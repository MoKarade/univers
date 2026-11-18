#!/usr/bin/env python3
"""Gaz sur la carte graphique : hydrodynamique à particules lissées (SPH), pour le calcul du Groupe local.

Pourquoi : sans gaz, pas de nouvelles étoiles, les bras s'effacent et la couche jeune du disque ne reste pas mince
(docs/deuxieme-film.md, écart 7). Marc, 18/11/2026 : « plus réaliste niveau physique », « va encore plus loin ».

Méthode (formulation classique, Monaghan 1992, ARA&A 30, 543 ; Springel 2005, MNRAS 364, 1105 pour les choix) :
- chaque particule de gaz a une longueur de lissage h telle que sa sphère de rayon 2h contienne environ 58 voisines
  (h = ETA (m / rho)^(1/3), ETA = 1,2), trouvée par itération ;
- densité : rho_i = somme_j m_j W(r_ij, h_i), noyau en spline cubique (Monaghan & Lattanzio 1985) ;
- accélération : a_i = - somme_j m_j (P_i / rho_i² + P_j / rho_j² + Pi_ij) grad W_ij, avec le noyau moyen
  W_ij = (W(h_i) + W(h_j)) / 2 : chaque paire agit de façon égale et opposée (quantité de mouvement conservée) ;
- viscosité artificielle Pi_ij de Monaghan (alpha = 1, beta = 2) avec l'interrupteur de Balsara (1995), qui la coupe
  dans les écoulements en cisaillement pur (un disque qui tourne) ;
- énergie interne : du_i/dt = 1/2 somme_j m_j (P_i / rho_i² + P_j / rho_j² + Pi_ij) v_ij . grad W_ij.
Les voisines sont trouvées en descendant le même arbre binaire que la gravité (gravite_gpu.py, Karras 2012), dont
chaque nœud porte sa boîte et la plus grande longueur de lissage de ses particules.

Unités : celles du calcul (kpc, km/s, M☉) ; pression = (gamma - 1) rho u, ou rho cs² en isotherme.
Simple précision sur la carte, positions comptées depuis le centre du nuage : à utiliser galaxie par galaxie (à
800 kpc du centre, la simple précision ne distingue plus 60 pc).

Contrôles : pipeline/fusion/essai_gaz.py (gradient connu, tube à choc isotherme, effondrement d'Evrard).
"""
import numpy as np
import cupy as cp

from gravite_gpu import _build, _morton, _grid, BLOCK

ETA = 1.2
ALPHA, BETA = 1.0, 2.0

_SRC = r'''
#define PI 3.14159265358979f

__device__ __forceinline__ float W(float r, float h) {
    float q = r / h, s = 1.f / (PI * h * h * h);
    if (q < 1.f) return s * (1.f - 1.5f * q * q + 0.75f * q * q * q);
    if (q < 2.f) { float t = 2.f - q; return s * 0.25f * t * t * t; }
    return 0.f;
}
/* dW/dr */
__device__ __forceinline__ float dW(float r, float h) {
    float q = r / h, s = 1.f / (PI * h * h * h * h);
    if (q < 1.f) return s * (-3.f * q + 2.25f * q * q);
    if (q < 2.f) { float t = 2.f - q; return -s * 0.75f * t * t; }
    return 0.f;
}
/* distance au carré d'un point à une boîte */
__device__ __forceinline__ float d2box(const float* b, float x, float y, float z) {
    float dx = fmaxf(fmaxf(b[0] - x, x - b[3]), 0.f), dy = fmaxf(fmaxf(b[1] - y, y - b[4]), 0.f), dz = fmaxf(fmaxf(b[2] - z, z - b[5]), 0.f);
    return dx * dx + dy * dy + dz * dz;
}

/* Remontée : boîte de chaque nœud et plus grande longueur de lissage de ses particules. */
extern "C" __global__ void boites(int n, const float* pos, const float* h, const int* left, const int* right,
                                  const int* parent, int* flag, float* box, float* hmax) {
    int k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= n) return;
    int node = n - 1 + k;
    for (int a = 0; a < 3; a++) { box[6*node+a] = pos[3*k+a]; box[6*node+3+a] = pos[3*k+a]; }
    hmax[node] = h[k];
    __threadfence();
    int cur = parent[node];
    while (cur >= 0) {
        if (atomicAdd(&flag[cur], 1) == 0) return;
        __threadfence();
        int L = left[cur], R = right[cur];
        for (int a = 0; a < 3; a++) { box[6*cur+a] = fminf(box[6*L+a], box[6*R+a]); box[6*cur+3+a] = fmaxf(box[6*L+3+a], box[6*R+3+a]); }
        hmax[cur] = fmaxf(hmax[L], hmax[R]);
        __threadfence();
        cur = parent[cur];
    }
}

/* Densité, nombre de voisines, divergence et rotationnel de la vitesse (pour l'interrupteur de Balsara). */
extern "C" __global__ void densite(int n, const float* pos, const float* vel, const float* mass, const float* h,
                                   const int* left, const int* right, const float* box,
                                   float* rho, int* nvois, float* divv, float* rotv) {
    int k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= n) return;
    float px = pos[3*k], py = pos[3*k+1], pz = pos[3*k+2], hi = h[k], r2max = 4.f * hi * hi;
    float vx = vel[3*k], vy = vel[3*k+1], vz = vel[3*k+2];
    float s = 0.f, dv = 0.f, cx = 0.f, cy = 0.f, cz = 0.f; int nv = 0;
    int stack[128]; int sp = 0; stack[sp++] = 0;
    while (sp > 0) {
        int node = stack[--sp];
        if (d2box(box + 6*node, px, py, pz) >= r2max) continue;
        if (node >= n - 1) {
            int j = node - (n - 1);
            float dx = px - pos[3*j], dy = py - pos[3*j+1], dz = pz - pos[3*j+2];
            float r2 = dx*dx + dy*dy + dz*dz;
            if (r2 >= r2max) continue;
            float r = sqrtf(r2), m = mass[j];
            s += m * W(r, hi); nv++;
            if (r > 0.f) {
                float g = m * dW(r, hi) / r;      /* grad_i W = g * (dx, dy, dz) / m */
                float ux = vel[3*j] - vx, uy = vel[3*j+1] - vy, uz = vel[3*j+2] - vz;      /* v_j - v_i */
                dv += g * (ux * dx + uy * dy + uz * dz);
                cx += g * (uy * dz - uz * dy); cy += g * (uz * dx - ux * dz); cz += g * (ux * dy - uy * dx);
            }
        } else if (sp < 126) { stack[sp++] = left[node]; stack[sp++] = right[node]; }
    }
    rho[k] = s; nvois[k] = nv;
    divv[k] = dv / s; rotv[k] = sqrtf(cx*cx + cy*cy + cz*cz) / s;
}

/* Accélération de pression et de viscosité, et taux de chauffage. pr = P / rho². cs : vitesse du son. bal : interrupteur de Balsara. */
extern "C" __global__ void forces(int n, const float* pos, const float* vel, const float* mass, const float* h,
                                  const float* rho, const float* pr, const float* cs, const float* bal,
                                  const int* left, const int* right, const float* box, const float* hmax,
                                  float alpha, float beta, float* acc, float* dudt, float* vsig) {
    int k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= n) return;
    float px = pos[3*k], py = pos[3*k+1], pz = pos[3*k+2], hi = h[k];
    float vx = vel[3*k], vy = vel[3*k+1], vz = vel[3*k+2];
    float ax = 0.f, ay = 0.f, az = 0.f, du = 0.f, vs = cs[k];
    int stack[128]; int sp = 0; stack[sp++] = 0;
    while (sp > 0) {
        int node = stack[--sp];
        float hh = fmaxf(hi, hmax[node]);
        if (d2box(box + 6*node, px, py, pz) >= 4.f * hh * hh) continue;
        if (node >= n - 1) {
            int j = node - (n - 1);
            if (j == k) continue;
            float dx = px - pos[3*j], dy = py - pos[3*j+1], dz = pz - pos[3*j+2];
            float r2 = dx*dx + dy*dy + dz*dz, hj = h[j];
            float hm = fmaxf(hi, hj);
            if (r2 >= 4.f * hm * hm || r2 <= 0.f) continue;
            float r = sqrtf(r2);
            float g = 0.5f * (dW(r, hi) + dW(r, hj)) / r;      /* grad_i W_ij = g * (dx, dy, dz) */
            float ux = vx - vel[3*j], uy = vy - vel[3*j+1], uz = vz - vel[3*j+2];
            float vr = ux * dx + uy * dy + uz * dz;
            float visc = 0.f;
            if (vr < 0.f) {
                float hbar = 0.5f * (hi + hj), mu = hbar * vr / (r2 + 0.01f * hbar * hbar);
                float cbar = 0.5f * (cs[k] + cs[j]), rbar = 0.5f * (rho[k] + rho[j]);
                visc = (-alpha * cbar * mu + beta * mu * mu) / rbar * 0.5f * (bal[k] + bal[j]);
                vs = fmaxf(vs, cbar - 3.f * vr / r);
            }
            float f = mass[j] * (pr[k] + pr[j] + visc) * g;
            ax -= f * dx; ay -= f * dy; az -= f * dz;
            du += 0.5f * f * vr;
        } else if (sp < 126) { stack[sp++] = left[node]; stack[sp++] = right[node]; }
    }
    acc[3*k] = ax; acc[3*k+1] = ay; acc[3*k+2] = az; dudt[k] = du; vsig[k] = vs;
}
'''

_mod = cp.RawModule(code=_SRC, options=('--std=c++14',))
_boites, _densite, _forces = (_mod.get_function(k) for k in ('boites', 'densite', 'forces'))


class Arbre:
    """Arbre des particules de gaz, triées le long de la courbe de Morton ; positions comptées depuis le centre."""

    def __init__(self, pos, vel, m):
        n = self.n = int(pos.shape[0])
        self.centre = cp.median(pos, axis=0)
        half = 1.5 * float(cp.percentile(cp.abs(pos - self.centre).max(axis=1), 99.5)) + 1e-30
        lo = self.centre - half
        code = _morton(pos[:, 0], pos[:, 1], pos[:, 2], float(lo[0]), float(lo[1]), float(lo[2]), 1.0 / (2.0 * half))
        self.order = cp.argsort(code)
        code = cp.ascontiguousarray(code[self.order])
        self.p = cp.ascontiguousarray((pos[self.order] - self.centre).astype(cp.float32))
        self.v = cp.ascontiguousarray((vel[self.order] - cp.mean(vel, axis=0)).astype(cp.float32))
        self.m = cp.ascontiguousarray(m[self.order].astype(cp.float32))
        self.left = cp.empty(n - 1, cp.int32); self.right = cp.empty(n - 1, cp.int32)
        self.parent = cp.full(2 * n - 1, -1, cp.int32)
        _build(_grid(n - 1), (BLOCK,), (code, np.int32(n), self.left, self.right, self.parent))
        self.box = cp.empty(6 * (2 * n - 1), cp.float32); self.hmax = cp.empty(2 * n - 1, cp.float32)

    def boites(self, h):
        flag = cp.zeros(self.n - 1, cp.int32)
        _boites(_grid(self.n), (BLOCK,), (np.int32(self.n), self.p, h, self.left, self.right, self.parent, flag, self.box, self.hmax))


def sph(pos, vel, m, h, u=None, cs=None, gamma=5.0 / 3.0, h_min=0.0, h_max=np.inf, passes=3):
    """Un pas d'hydrodynamique. pos, vel (n,3), m, h (n,) : tableaux CuPy en double ; h : longueurs de lissage du pas d'avant
    (une première estimation suffit). u : énergie interne par unité de masse (gaz adiabatique) OU cs : vitesse du son
    (gaz isotherme, nombre ou tableau). Rend un dictionnaire : acc (n,3), dudt, rho, h (mis à jour), nvois, vsig (vitesse de
    signal, pour le pas de temps), dans l'ordre d'entrée."""
    n = int(pos.shape[0])
    A = Arbre(pos, vel, m)
    o = A.order
    hs = cp.ascontiguousarray(h[o].astype(cp.float32))
    rho = cp.empty(n, cp.float32); nv = cp.empty(n, cp.int32); dv = cp.empty(n, cp.float32); rv = cp.empty(n, cp.float32)
    for it in range(passes):
        A.boites(hs)
        _densite(_grid(n), (BLOCK,), (np.int32(n), A.p, A.v, A.m, hs, A.left, A.right, A.box, rho, nv, dv, rv))
        if it < passes - 1:
            # h = ETA (m / rho)^(1/3) ; moyenne avec l'ancien pour ne pas osciller, bornes données par l'appelant
            cible = ETA * (A.m / rho) ** (1.0 / 3.0)
            hs = cp.ascontiguousarray(cp.clip(0.5 * (hs + cible), h_min, h_max).astype(cp.float32))
    if cs is None:
        us = cp.ascontiguousarray(cp.maximum(u[o], 0.0).astype(cp.float32))      # une énergie interne ne peut pas être négative
        P = (gamma - 1.0) * rho * us
        son = cp.sqrt(gamma * (gamma - 1.0) * us)
    else:
        son = cp.full(n, cs, cp.float32) if np.isscalar(cs) else cp.ascontiguousarray(cs[o].astype(cp.float32))
        P = rho * son * son
    son = cp.ascontiguousarray(son.astype(cp.float32))
    pr = cp.ascontiguousarray((P / (rho * rho)).astype(cp.float32))
    bal = cp.ascontiguousarray((cp.abs(dv) / (cp.abs(dv) + rv + 1e-4 * son / hs)).astype(cp.float32))
    A.boites(hs)
    acc = cp.empty(3 * n, cp.float32); du = cp.empty(n, cp.float32); vs = cp.empty(n, cp.float32)
    _forces(_grid(n), (BLOCK,), (np.int32(n), A.p, A.v, A.m, hs, rho, pr, son, bal, A.left, A.right, A.box, A.hmax,
                                 np.float32(ALPHA), np.float32(BETA), acc, du, vs))
    out = {}
    for nom, t, forme in (('acc', acc.reshape(n, 3), (n, 3)), ('dudt', du, (n,)), ('rho', rho, (n,)), ('h', hs, (n,)), ('vsig', vs, (n,)), ('divv', dv, (n,))):
        x = cp.empty(forme, cp.float64); x[o] = t; out[nom] = x
    x = cp.empty(n, cp.int32); x[o] = nv; out['nvois'] = x
    return out
