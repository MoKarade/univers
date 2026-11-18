#!/usr/bin/env python3
"""Gravité entre toutes les particules, calculée sur la carte graphique (jalon A1, docs/plan-natif.md).

Remplace pyfalcon (processeur) dans calcul.py quand on lance `calcul.py ... --gpu`. Même rôle : accélération et
potentiel de chaque particule, toutes s'attirant.

Méthode : arbre de Barnes et Hut (1986, Nature 324, 446) sous forme d'arbre binaire construit en parallèle à partir
de codes de Morton triés (Karras 2012, « Maximizing Parallelism in the Construction of BVHs, Octrees, and k-d
Trees », HPG 2012). Un groupe lointain de particules est remplacé par sa masse totale placée à son centre de masse
(et, si QUAD, par son moment quadripolaire) quand il est vu sous un petit angle : distance > taille / theta + écart
entre centre de masse et centre de la boîte (critère de Barnes 1994, qui évite les erreurs quand le centre de masse
est au bord de la boîte). Sinon le groupe est ouvert.

Adoucissement de Plummer, propre à chaque particule : eps_ij² = (eps_i² + eps_j²) / 2 ; pour un groupe, la moyenne
de eps² pondérée par la masse. [Différence avec falcON, qui utilise un autre noyau : contrôlée par l'énergie.]

Aucun outil à installer en administrateur : les noyaux CUDA sont compilés à la volée par CuPy (paquet pip
`cupy-cuda12x[ctk]`). Simple précision pour les forces, comme falcON ; positions et vitesses restent en double.
"""
import numpy as np
import cupy as cp

_SRC = r'''
typedef unsigned long long u64;

__device__ __forceinline__ int delta(const u64* code, int n, int i, int j) {
    if (j < 0 || j >= n) return -1;
    u64 a = code[i], b = code[j];
    if (a == b) return 64 + __clz(i ^ j);
    return __clzll(a ^ b);
}

/* Karras 2012 : chaque noeud interne i (0..n-2) trouve seul ses deux enfants. Feuille k = noeud n-1+k. */
extern "C" __global__ void build(const u64* code, int n, int* left, int* right, int* parent) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n - 1) return;
    int d = (delta(code, n, i, i + 1) - delta(code, n, i, i - 1)) >= 0 ? 1 : -1;
    int dmin = delta(code, n, i, i - d);
    int lmax = 2;
    while (delta(code, n, i, i + lmax * d) > dmin) lmax *= 2;
    int l = 0;
    for (int t = lmax / 2; t >= 1; t /= 2)
        if (delta(code, n, i, i + (l + t) * d) > dmin) l += t;
    int j = i + l * d;
    int dnode = delta(code, n, i, j);
    int s = 0, t = l;
    do {
        t = (t + 1) >> 1;
        if (delta(code, n, i, i + (s + t) * d) > dnode) s += t;
    } while (t > 1);
    int g = i + s * d + (d < 0 ? d : 0);
    int lo = i < j ? i : j, hi = i < j ? j : i;
    int L = (lo == g) ? (n - 1 + g) : g;
    int R = (hi == g + 1) ? (n - 1 + g + 1) : (g + 1);
    left[i] = L; right[i] = R;
    parent[L] = i; parent[R] = i;
}

/* Remontée : chaque feuille monte ; le second arrivé sur un noeud en calcule la masse, le centre, la boîte.
   com : x, y, z, masse. box : min xyz, max xyz. aux : rayon d'ouverture au carré, eps² moyen.
   quad : 6 termes du moment quadripolaire sans trace retirée (somme m dx dx), autour du centre de masse. */
extern "C" __global__ void upward(int n, const float* pos, const float* mass, const float* eps2,
                                  const int* left, const int* right, const int* parent, int* flag,
                                  float* com_w, float* box_w, float* aux_w, float* quad_w, float inv_theta) {
    int k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= n) return;
    int node = n - 1 + k;
    com_w[4*node] = pos[3*k]; com_w[4*node+1] = pos[3*k+1]; com_w[4*node+2] = pos[3*k+2]; com_w[4*node+3] = mass[k];
    for (int a = 0; a < 3; a++) { box_w[6*node+a] = pos[3*k+a]; box_w[6*node+3+a] = pos[3*k+a]; }
    aux_w[2*node] = 0.f; aux_w[2*node+1] = eps2[k];
    for (int a = 0; a < 6; a++) quad_w[6*node+a] = 0.f;
    __threadfence();
    int cur = parent[node];
    while (cur >= 0) {
        if (atomicAdd(&flag[cur], 1) == 0) return;      /* premier arrivé : l'autre enfant n'est pas prêt */
        __threadfence();
        int L = left[cur], R = right[cur];
        /* Les données des deux enfants ont été écrites par d'autres fils d'exécution : on les relit en mémoire par des
           pointeurs « volatile », pour que le compilateur ne réutilise jamais une valeur lue avant la barrière
           (__threadfence). [Revue de code du 18/11/2026, point N2.] */
        const volatile float* com = com_w; const volatile float* box = box_w; const volatile float* aux = aux_w; const volatile float* quad = quad_w;
        double mL = com[4*L+3], mR = com[4*R+3], m = mL + mR;
        double c[3];
        for (int a = 0; a < 3; a++) c[a] = (mL * (double)com[4*L+a] + mR * (double)com[4*R+a]) / m;
        float ext = 0.f, off2 = 0.f;
        for (int a = 0; a < 3; a++) {
            float lo = fminf(box[6*L+a], box[6*R+a]), hi = fmaxf(box[6*L+3+a], box[6*R+3+a]);
            box_w[6*cur+a] = lo; box_w[6*cur+3+a] = hi;
            ext = fmaxf(ext, hi - lo);
            float o = (float)c[a] - 0.5f * (lo + hi); off2 += o * o;
        }
        float ro = ext * inv_theta + sqrtf(off2);
        /* quadripôle : théorème des axes parallèles */
        double dl[3], dr[3];
        for (int a = 0; a < 3; a++) { dl[a] = (double)com[4*L+a] - c[a]; dr[a] = (double)com[4*R+a] - c[a]; }
        const int ia[6] = {0, 1, 2, 0, 0, 1}, ib[6] = {0, 1, 2, 1, 2, 2};
        for (int q = 0; q < 6; q++)
            quad_w[6*cur+q] = (float)((double)quad[6*L+q] + (double)quad[6*R+q] + mL * dl[ia[q]] * dl[ib[q]] + mR * dr[ia[q]] * dr[ib[q]]);
        for (int a = 0; a < 3; a++) com_w[4*cur+a] = (float)c[a];
        com_w[4*cur+3] = (float)m;
        aux_w[2*cur] = ro * ro;
        aux_w[2*cur+1] = (float)((mL * (double)aux[2*L+1] + mR * (double)aux[2*R+1]) / m);
        __threadfence();
        cur = parent[cur];
    }
}

/* Descente : accélération et potentiel de chaque particule (dans l'ordre trié). G n'est pas appliqué ici. */
extern "C" __global__ void walk(int n, const float* pos, const float* eps2, const int* left, const int* right,
                                const float* com, const float* aux, const float* quad, int use_quad,
                                float* acc, float* phi, int* plein) {
    int k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= n) return;
    float px = pos[3*k], py = pos[3*k+1], pz = pos[3*k+2], e2 = eps2[k];
    float ax = 0.f, ay = 0.f, az = 0.f, ph = 0.f;
    int self = n - 1 + k;
    int stack[160]; int sp = 0;
    stack[sp++] = 0;
    while (sp > 0) {
        int node = stack[--sp];
        float dx = com[4*node] - px, dy = com[4*node+1] - py, dz = com[4*node+2] - pz;
        float r2 = dx*dx + dy*dy + dz*dz;
        bool leaf = node >= n - 1;
        if (leaf || r2 > aux[2*node]) {
            if (node == self) continue;
            float m = com[4*node+3];
            float s2 = r2 + 0.5f * (e2 + aux[2*node+1]);
            float inv = rsqrtf(s2), inv2 = inv * inv, inv3 = inv * inv2;
            ax += m * inv3 * dx; ay += m * inv3 * dy; az += m * inv3 * dz; ph -= m * inv;
            if (use_quad && !leaf) {
                const float* Q = quad + 6*node;      /* xx yy zz xy xz yz */
                float tr = Q[0] + Q[1] + Q[2];
                float qx = Q[0]*dx + Q[3]*dy + Q[4]*dz, qy = Q[3]*dx + Q[1]*dy + Q[5]*dz, qz = Q[4]*dx + Q[5]*dy + Q[2]*dz;
                float dqd = qx*dx + qy*dy + qz*dz;
                float inv5 = inv3 * inv2, inv7 = inv5 * inv2;
                /* phi = -(3 dQd/s^5 - tr/s^3)/2 ; a = -grad_p phi, avec d = centre - particule */
                ph -= 0.5f * (3.f * dqd * inv5 - tr * inv3);
                float c1 = 7.5f * dqd * inv7 - 1.5f * tr * inv5;
                ax += c1 * dx - 3.f * inv5 * qx; ay += c1 * dy - 3.f * inv5 * qy; az += c1 * dz - 3.f * inv5 * qz;
            }
        } else {
            if (sp < 158) { stack[sp++] = left[node]; stack[sp++] = right[node]; }
            else atomicAdd(plein, 1);      /* pile pleine : ce nœud est abandonné ; compté, et gravity() s'arrête (point N3) */
        }
    }
    acc[3*k] = ax; acc[3*k+1] = ay; acc[3*k+2] = az; phi[k] = ph;
}

/* Somme directe (contrôle) : cibles pos_t, sources pos. */
extern "C" __global__ void direct(int nt, int n, const float* pos_t, const float* eps2_t, const int* self,
                                  const float* pos, const float* mass, const float* eps2, float* acc, float* phi) {
    int k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= nt) return;
    double ax = 0, ay = 0, az = 0, ph = 0;
    float px = pos_t[3*k], py = pos_t[3*k+1], pz = pos_t[3*k+2], e2 = eps2_t[k];
    for (int j = 0; j < n; j++) {
        if (j == self[k]) continue;
        float dx = pos[3*j] - px, dy = pos[3*j+1] - py, dz = pos[3*j+2] - pz;
        float s2 = dx*dx + dy*dy + dz*dz + 0.5f * (e2 + eps2[j]);
        float inv = rsqrtf(s2), inv3 = inv * inv * inv, m = mass[j];
        ax += m * inv3 * dx; ay += m * inv3 * dy; az += m * inv3 * dz; ph -= m * inv;
    }
    acc[3*k] = (float)ax; acc[3*k+1] = (float)ay; acc[3*k+2] = (float)az; phi[k] = (float)ph;
}
'''

_mod = cp.RawModule(code=_SRC, options=('--std=c++14',))
_build, _upward, _walk, _direct = (_mod.get_function(k) for k in ('build', 'upward', 'walk', 'direct'))

_morton = cp.ElementwiseKernel(
    'float64 x, float64 y, float64 z, float64 x0, float64 y0, float64 z0, float64 inv', 'uint64 code',
    '''
    unsigned long long v[3];
    double c[3] = {(x - x0) * inv, (y - y0) * inv, (z - z0) * inv};
    for (int a = 0; a < 3; a++) {
        double t = c[a] * 2097152.0; if (t < 0) t = 0; if (t > 2097151.0) t = 2097151.0;
        unsigned long long u = (unsigned long long)t;
        u &= 0x1fffffULL;
        u = (u | u << 32) & 0x1f00000000ffffULL;
        u = (u | u << 16) & 0x1f0000ff0000ffULL;
        u = (u | u << 8) & 0x100f00f00f00f00fULL;
        u = (u | u << 4) & 0x10c30c30c30c30c3ULL;
        u = (u | u << 2) & 0x1249249249249249ULL;
        v[a] = u;
    }
    code = v[0] | (v[1] << 1) | (v[2] << 2);
    ''', 'morton63')

BLOCK = 256


def _grid(n):
    return ((n + BLOCK - 1) // BLOCK,)


def gravity(pos, m, eps, theta=0.5, quad=True):
    """pos (n,3) float64, m (n,), eps (n,) : tableaux CuPy. Rend (acc (n,3) float64, phi (n,) float64), sans G :
    multiplier m par G avant l'appel, comme pour pyfalcon.gravity."""
    n = int(pos.shape[0])
    # Boîte des codes de Morton : centrée sur la médiane, large de 3 fois le rayon qui contient 99,5 % des
    # particules. Quelques particules de halo partent à des millions de kpc : une boîte qui les contiendrait
    # toutes écraserait les galaxies dans une poignée de cases (arbre dégénéré, mesuré 16 fois plus lent) et
    # ruinerait la simple précision. Les particules hors boîte sont rangées dans les cases du bord ; leurs
    # vraies positions restent utilisées pour les forces.
    centre = cp.median(pos, axis=0)
    half = 1.5 * float(cp.percentile(cp.abs(pos - centre).max(axis=1), 99.5)) + 1e-30
    lo = centre - half; size = 2.0 * half
    code = _morton(pos[:, 0], pos[:, 1], pos[:, 2], float(lo[0]), float(lo[1]), float(lo[2]), 1.0 / size)
    order = cp.argsort(code)
    code = cp.ascontiguousarray(code[order])
    p32 = cp.ascontiguousarray((pos[order] - centre).astype(cp.float32))
    m32 = cp.ascontiguousarray(m[order].astype(cp.float32))
    e2 = cp.ascontiguousarray((eps[order] ** 2).astype(cp.float32))
    nn = 2 * n - 1
    left = cp.empty(n - 1, cp.int32); right = cp.empty(n - 1, cp.int32)
    parent = cp.full(nn, -1, cp.int32); flag = cp.zeros(n - 1, cp.int32)
    com = cp.empty(4 * nn, cp.float32); box = cp.empty(6 * nn, cp.float32); aux = cp.empty(2 * nn, cp.float32)
    qd = cp.empty(6 * nn, cp.float32)
    _build(_grid(n - 1), (BLOCK,), (code, np.int32(n), left, right, parent))
    _upward(_grid(n), (BLOCK,), (np.int32(n), p32, m32, e2, left, right, parent, flag, com, box, aux, qd, np.float32(1.0 / theta)))
    acc = cp.empty(3 * n, cp.float32); phi = cp.empty(n, cp.float32)
    plein = cp.zeros(1, cp.int32)
    _walk(_grid(n), (BLOCK,), (np.int32(n), p32, e2, left, right, com, aux, qd, np.int32(1 if quad else 0), acc, phi, plein))
    if int(plein[0]): raise RuntimeError(f"gravité : pile pleine {int(plein[0])} fois dans la descente de l'arbre, des forces seraient fausses")
    out_a = cp.empty((n, 3), cp.float64); out_p = cp.empty(n, cp.float64)
    out_a[order] = acc.reshape(n, 3); out_p[order] = phi
    return out_a, out_p


def gravity_direct(pos, m, eps, idx):
    """Somme directe pour les particules d'indices idx (contrôle de l'arbre)."""
    n = int(pos.shape[0]); idx = cp.asarray(idx, cp.int32); nt = int(idx.shape[0])
    centre = cp.median(pos, axis=0)
    p32 = cp.ascontiguousarray((pos - centre).astype(cp.float32)); m32 = cp.ascontiguousarray(m.astype(cp.float32))
    e2 = cp.ascontiguousarray((eps ** 2).astype(cp.float32))
    pt = cp.ascontiguousarray(p32[idx]); et = cp.ascontiguousarray(e2[idx])
    acc = cp.empty(3 * nt, cp.float32); phi = cp.empty(nt, cp.float32)
    _direct(_grid(nt), (BLOCK,), (np.int32(nt), np.int32(n), pt, et, idx, p32, m32, e2, acc, phi))
    return acc.reshape(nt, 3).astype(cp.float64), phi.astype(cp.float64)
