#!/usr/bin/env python3
"""Le gaz d'une galaxie dans le calcul : pression, chocs, et naissance d'étoiles. [Modèle, signalé comme tel]

S'appuie sur gaz_gpu.py (hydrodynamique à particules lissées, contrôlée par essai_gaz.py). Les particules de gaz sont
celles de sorte 3 des galaxies de départ (modeles_v2.py) ; jusqu'ici elles n'étaient que des étoiles froides.

Choix physiques, tous des modèles simples et publiés, à dire à l'écran :
- gaz isotherme à 10 km/s de vitesse du son (gaz tiède à ~10 000 K, qui porte l'essentiel de la masse du gaz d'un disque) :
  le chauffage et le refroidissement ne sont pas calculés, on suppose qu'ils s'équilibrent à cette température ;
- pression effective au-dessus du seuil de naissance d'étoiles : P = P_seuil (rho / rho_seuil)^(4/3), avec une température
  de 8 000 K au seuil (Schaye & Dalla Vecchia 2008 ; EAGLE, Schaye et al. 2015). Elle tient lieu de la pression des
  explosions d'étoiles et de la turbulence qu'on ne résout pas : sans elle le gaz dense s'effondre en grumeaux. Avec
  l'exposant 4/3, la masse de Jeans ne dépend plus de la densité et reste résolue. [Remplace, le 18/11/2026, un plancher de
  Jeans qui dépendait de la longueur de lissage : conseil de docs/monter-une-simulation-pro.md.]
- pas de temps du gaz : le gaz avance par sous-pas, assez courts pour que le nombre de Courant (dt x vitesse de signal / h)
  reste sous COURANT, pendant que la gravité garde son pas long (dans les chocs de la rencontre il faut ~0,03 Ma) ;
- naissance d'étoiles : au-dessus de SEUIL_NH atomes d'hydrogène par cm³, une particule de gaz devient une particule
  d'étoiles (sorte 5, « née pendant le calcul ») avec la probabilité 1 - exp(-EFFICACITE dt / t_chute), où t_chute est le
  temps de chute libre du gaz, sqrt(3 pi / (32 G rho)) (loi de Schmidt 1959 ; Katz 1992 ; EFFICACITE ~1 % par temps de
  chute libre, Krumholz & Tan 2007). La masse est conservée : la particule change de nature, pas de masse.
- retour de masse : les étoiles rendent du gaz en vieillissant (retour_masse.py : 21 % de la masse d'une population à
  100 Ma, 31 % à 1 Ga, 40 % à 10 Ga). Ici, à chaque pas, une particule d'étoiles redevient une particule de gaz avec la
  probabilité (part rendue pendant le pas) / (part pas encore rendue) à son âge : en moyenne la bonne masse revient au gaz,
  et la masse totale ne change pas. Âges des étoiles du départ [Supposition] : disque mince né à rythme constant depuis
  10 Ga, disque épais entre 10 et 12 Ga, bulbe à 10 Ga ; étoiles nées pendant le calcul : leur date de naissance.
Ce qui manque encore : chauffage par les explosions d'étoiles (rétroaction), gaz chaud, enrichissement chimique.

Unités du calcul : kpc, km/s, M☉ ; temps en kpc/(km/s).
"""
import math

import numpy as np
import cupy as cp

import json
import os

import gaz_gpu

G = 4.30091e-6
CS = 10.0                 # km/s
COURANT = 0.3
SOUS_PAS_MAX = 64
C_SEUIL2 = 54.2             # (km/s)² : k T / (mu m_p) à 8 000 K, gaz neutre (mu = 1,22)
SEUIL_NH = 0.1            # cm^-3 (seuil de naissance d'étoiles, ordre de grandeur des simulations EAGLE : Schaye et al. 2015)
# 1 M☉/kpc³ = 1e-9 M☉/pc³ = 1e-9 x 40,46 protons/cm³ ; avec 76 % d'hydrogène : n_H = 3,075e-8 cm^-3 par M☉/kpc³
NH_PAR_MSOL_KPC3 = 0.76 * 40.46e-9
EFFICACITE = 0.01
H_MIN, H_MAX = 0.02, 2.0  # kpc
SORTE_GAZ, SORTE_NEE = 3, 5
AN_PAR_UNITE = 0.9778e9      # ans par unité de temps du calcul, kpc/(km/s)


class Gaz:
    """Gaz d'un ensemble de particules (une galaxie, ou plusieurs assez proches pour tenir en simple précision)."""

    def __init__(self, n_total, graine=20261118):
        self.h = cp.full(n_total, 0.2)            # longueur de lissage de chaque particule (seules celles de gaz servent)
        self.rho = cp.zeros(n_total)
        self.naissance = np.full(n_total, np.nan)  # date de naissance (Ga) des étoiles nées pendant le calcul
        self.rng = cp.random.default_rng(graine)
        self.cfl = 0.0; self.sous_pas = 0
        self._acc = None; self._taux = 0.0
        self.age0 = None; self.rendues = 0
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats', 'retour_masse.json'), encoding='utf-8') as f:
            r = json.load(f)
        self._la = cp.asarray(np.log(np.array(r['ages_ans']))); self._pr = cp.asarray(np.array(r['part_rendue']))
        self.nees = 0

    def _sph(self, p, v, mm, h):
        """Forces du gaz avec la pression effective : vitesse du son au carré = max(CS², C_SEUIL2 (rho / rho_seuil)^(1/3)).
        La densité dépend peu de la pression choisie : un premier passage la donne, le second calcule les forces."""
        r = gaz_gpu.sph(p, v, mm, h, cs=CS, h_min=H_MIN, h_max=H_MAX, passes=2)
        c2 = cp.maximum(CS * CS, C_SEUIL2 * cp.cbrt(r['rho'] * NH_PAR_MSOL_KPC3 / SEUIL_NH))
        if float(c2.max()) > CS * CS * 1.0001:
            r = gaz_gpu.sph(p, v, mm, r['h'], cs=cp.sqrt(c2), h_min=H_MIN, h_max=H_MAX, passes=1)
        return r

    def avancer(self, pos, vel, m, qui, dt):
        """Fait avancer les particules de gaz d'indices `qui` d'un pas dt (positions ET vitesses, sur place), par sous-pas
        saute-mouton sous la seule pression ; la gravité est appliquée par l'appelant, aux demi-pas longs, comme pour les
        autres particules. Rend le nombre de sous-pas faits."""
        n = int(qui.shape[0])
        if n < 100:
            pos[qui] += dt * vel[qui]; return 0
        p, v, mm = pos[qui], vel[qui], m[qui]
        if self._acc is None or self._acc.shape[0] != n:      # premier pas, ou des particules sont devenues des étoiles
            r = self._sph(p, v, mm, self.h[qui]); self._acc = r['acc']; self.h[qui] = r['h']; self.rho[qui] = r['rho']
            self._taux = float((r['vsig'] / r['h']).max())
        k = 1
        while k < SOUS_PAS_MAX and dt / k * self._taux > COURANT: k *= 2
        d = dt / k; h = self.h[qui]; pire = 0.0
        for _ in range(k):
            v += 0.5 * d * self._acc
            p += d * v
            r = self._sph(p, v, mm, h); h = r['h']
            self._acc = r['acc']
            v += 0.5 * d * self._acc
            pire = max(pire, float((r['vsig'] / r['h']).max()))
        pos[qui] = p; vel[qui] = v; self.h[qui] = h; self.rho[qui] = r['rho']
        self.cfl = d * pire; self._taux = pire; self.sous_pas = k
        return k

    def naissances(self, kind, qui, dt, t_ga, pos=None, m=None):
        """Tire au sort les particules de gaz qui deviennent des étoiles pendant ce pas. kind : tableau CuPy des sortes,
        modifié sur place. Rend le nombre de naissances."""
        if int(qui.shape[0]) == 0: return 0
        rho = self.rho[qui]
        dense = rho * NH_PAR_MSOL_KPC3 > SEUIL_NH
        t_chute = cp.sqrt(3.0 * math.pi / (32.0 * G * cp.maximum(rho, 1e-30)))
        proba = cp.where(dense, 1.0 - cp.exp(-EFFICACITE * dt / t_chute), 0.0)
        nee = self.rng.random(int(qui.shape[0])) < proba
        k = int(nee.sum())
        if k:
            idx = qui[nee]
            kind[idx] = SORTE_NEE
            self._acc = None      # la liste des particules de gaz a changé : les forces seront recalculées
            self.naissance[cp.asnumpy(idx)] = t_ga
            self.nees += k
        return k

    def ages_de_depart(self, kind):
        """Âge (Ga) à t = 0 des étoiles du départ, d'après leur sorte (tableau numpy). [Supposition, voir l'en-tête]"""
        rng = np.random.default_rng(20261119)
        n = len(kind); a = np.full(n, np.nan)
        a[kind == 1] = rng.uniform(0.05, 10.0, int((kind == 1).sum()))
        a[kind == 4] = rng.uniform(10.0, 12.0, int((kind == 4).sum()))
        a[kind == 2] = 10.0
        self.age0 = cp.asarray(a)

    def retour(self, kind, dt, t_ga):
        """Retour de masse : tire au sort les particules d'étoiles (sortes 1, 2, 4, 5) qui redeviennent du gaz pendant ce pas.
        kind : tableau CuPy modifié sur place. Rend le nombre de particules rendues au gaz."""
        if self.age0 is None: return 0
        etoile = (kind == 1) | (kind == 2) | (kind == 4) | (kind == SORTE_NEE)
        qui = cp.where(etoile)[0]
        if int(qui.shape[0]) == 0: return 0
        nee = cp.asarray(self.naissance)[qui]
        age = cp.where(cp.isnan(nee), self.age0[qui] + t_ga, t_ga - nee) * 1e9      # ans
        age = cp.maximum(age, 3.1e6); pas = dt * AN_PAR_UNITE
        r0 = cp.interp(cp.log(age), self._la, self._pr); r1 = cp.interp(cp.log(age + pas), self._la, self._pr)
        proba = cp.clip((r1 - r0) / (1.0 - r0), 0.0, 1.0)
        rend = self.rng.random(int(qui.shape[0])) < proba
        k = int(rend.sum())
        if k:
            idx = qui[rend]
            kind[idx] = SORTE_GAZ
            self.h[idx] = 0.2
            self.naissance[cp.asnumpy(idx)] = np.nan
            self.age0[idx] = cp.nan
            self._acc = None; self.rendues += k
        return k


# ----------------------------------------------------------------------------------------------------------------------
# Gaz « thermique » (Marc, 19/11/2026 : physique du gaz plus complète). [Modèle, signalé comme tel]
# En plus du gaz de base : l'énergie interne de chaque particule est suivie (compression, chocs), le gaz rayonne et se
# refroidit, et les étoiles qui naissent le réchauffent en explosant.
# - refroidissement : courbe à composition solaire, équilibre d'ionisation par collisions, ajustement par morceaux de
#   Schneider & Robertson 2018 (ApJ 860, 135, éq. A4, relu dans l'article le 19/11/2026) :
#     log L = -1,3 (logT - 5,25)² - 21,25 de 10^4 à 10^5,9 K ; 0,7 (logT - 7,1)² - 22,8 jusqu'à 10^7,4 K ; 0,45 logT - 26,065 au-delà
#   (L en erg cm³/s ; perte par volume n² L avec n = rho / (mu m_p), mu = 0,6 [définition de n : à relire dans Schneider &
#   Robertson 2017, annexe C]). Pas de refroidissement sous 10^4 K : plancher de température, comme dans cet article.
# - pression effective au-dessus du seuil de naissance d'étoiles : gardée, comme plancher (Schaye & Dalla Vecchia 2008).
# - explosions d'étoiles : chaque particule d'étoiles qui naît libère 10^51 erg par 100 M☉ formées (une supernova pour
#   100 M☉ : ordre de grandeur pour la répartition des masses de Kroupa [Supposition]) ; l'énergie est donnée d'un coup à la
#   particule de gaz la plus proche, chauffée de 10^7,5 K, avec la probabilité qui conserve l'énergie en moyenne (0,77 à
#   masses égales) : chauffage « thermique stochastique » de Dalla Vecchia & Schaye 2012 (MNRAS 426, 140), celui d'EAGLE.
#   Chauffé si fort, le gaz met longtemps à rayonner et a le temps de pousser son entourage ; chauffé un peu partout, il
#   rayonnerait tout aussitôt (c'est le défaut connu des explosions mal résolues). Ici l'explosion suit la naissance sans
#   délai [simplification : EAGLE attend 30 Ma].
GAMMA = 5.0 / 3.0
MU = 0.6
K_PAR_U = (GAMMA - 1.0) * MU * 1.6726e-24 * 1.0e10 / 1.3807e-16      # kelvins par (km/s)² d'énergie interne : 48,46
N_PAR_RHO = 1.989e33 / 3.0857e21 ** 3 / (MU * 1.6726e-24)            # particules par cm³ pour 1 M☉/kpc³ : 6,746e-8
REFROID = 3.0857e16 * 1.0e-10 / (MU * 1.6726e-24)                    # (km/s)² par unité de temps du calcul, pour n L = 1 erg cm³/s x cm^-3
T_PLANCHER = 1.0e4
U_PLANCHER = T_PLANCHER / K_PAR_U
DT_EXPLOSION = 10 ** 7.5                                             # kelvins
E_SN_PAR_MASSE = 1.0e51 / (100.0 * 1.989e33) * 1.0e-10               # (km/s)² par unité de masse d'étoiles formée : 5,03e5
SOUS_PAS_MAX_THERMIQUE = 256


def lambda_refroidissement(T):
    """Courbe de refroidissement (erg cm³/s), tableau CuPy de températures en kelvins. Nulle sous 10^4 K."""
    lt = cp.log10(cp.maximum(T, 1.0))
    L = cp.where(lt < 5.9, -1.3 * (lt - 5.25) ** 2 - 21.25, cp.where(lt < 7.4, 0.7 * (lt - 7.1) ** 2 - 22.8, 0.45 * lt - 26.065))
    return cp.where(lt < 4.0, 0.0, 10.0 ** L)


class GazThermique(Gaz):
    """Gaz avec énergie interne suivie, refroidissement et explosions d'étoiles. Même usage que Gaz."""

    def __init__(self, n_total, graine=20261119):
        super().__init__(n_total, graine)
        self.u = cp.full(n_total, U_PLANCHER)
        self._du = None
        self.chauffees = 0

    def _plancher(self, u, rho):
        """Énergie interne minimale : 10^4 K, et la pression effective au-dessus du seuil de naissance d'étoiles."""
        u_eos = C_SEUIL2 * cp.cbrt(cp.maximum(rho, 0.0) * NH_PAR_MSOL_KPC3 / SEUIL_NH) / (GAMMA - 1.0)
        return cp.maximum(u, cp.maximum(U_PLANCHER, cp.where(rho * NH_PAR_MSOL_KPC3 > SEUIL_NH, u_eos, 0.0)))

    def _refroidir(self, u, rho, dt):
        """Refroidissement à densité constante pendant dt, par petits pas (au plus 20 % de l'énergie par pas)."""
        n = rho * N_PAR_RHO; reste = cp.full(u.shape, dt)
        for _ in range(24):
            taux = n * lambda_refroidissement(u * K_PAR_U) * REFROID      # (km/s)² par unité de temps
            pas = cp.minimum(reste, 0.2 * u / cp.maximum(taux, 1e-30))
            u = cp.maximum(u - taux * pas, U_PLANCHER); reste = reste - pas
            if float(reste.max()) <= 0: break
        return u

    def _sph(self, p, v, mm, h, u):
        return gaz_gpu.sph(p, v, mm, h, u=u, gamma=GAMMA, h_min=H_MIN, h_max=H_MAX, passes=2)

    def avancer(self, pos, vel, m, qui, dt):
        n = int(qui.shape[0])
        if n < 100:
            pos[qui] += dt * vel[qui]; return 0
        p, v, mm = pos[qui], vel[qui], m[qui]
        u = self._plancher(self.u[qui], self.rho[qui])
        if self._acc is None or self._acc.shape[0] != n:
            r = self._sph(p, v, mm, self.h[qui], u); self._acc, self._du = r['acc'], r['dudt']
            self.h[qui] = r['h']; self.rho[qui] = r['rho']; self._taux = float((r['vsig'] / r['h']).max())
        k = 1
        while k < SOUS_PAS_MAX_THERMIQUE and dt / k * self._taux > COURANT: k *= 2
        d = dt / k; h = self.h[qui]; rho = self.rho[qui]; pire = 0.0
        for _ in range(k):
            v += 0.5 * d * self._acc; u = self._plancher(u + 0.5 * d * self._du, rho)
            p += d * v
            r = self._sph(p, v, mm, h, u); h, rho = r['h'], r['rho']
            self._acc, self._du = r['acc'], r['dudt']
            v += 0.5 * d * self._acc; u = self._plancher(u + 0.5 * d * self._du, rho)
            u = self._plancher(self._refroidir(u, rho, d), rho)
            pire = max(pire, float((r['vsig'] / r['h']).max()))
        pos[qui] = p; vel[qui] = v; self.h[qui] = h; self.rho[qui] = rho; self.u[qui] = u
        self.cfl = d * pire; self._taux = pire; self.sous_pas = k
        return k

    def naissances(self, kind, qui, dt, t_ga, pos=None, m=None):
        """Naissances (comme Gaz), puis explosions : chaque nouvelle étoile chauffe la particule de gaz la plus proche."""
        avant = kind[qui] == SORTE_GAZ
        k = super().naissances(kind, qui, dt, t_ga)
        if not k or pos is None: return k
        nees = qui[avant & (kind[qui] == SORTE_NEE)]
        gaz = qui[kind[qui] == SORTE_GAZ]
        if int(gaz.shape[0]) == 0: return k
        pg = pos[gaz]
        for a in range(0, int(nees.shape[0]), 256):      # voisine la plus proche, par paquets (peu de naissances par pas)
            pn = pos[nees[a:a + 256]]
            d2 = ((pn[:, None, :] - pg[None, :, :]) ** 2).sum(2)
            j = gaz[cp.argmin(d2, axis=1)]
            proba = E_SN_PAR_MASSE * m[nees[a:a + 256]] / ((DT_EXPLOSION / K_PAR_U) * m[j])
            oui = self.rng.random(int(j.shape[0])) < proba
            self.u[j[oui]] += DT_EXPLOSION / K_PAR_U
            self.chauffees += int(oui.sum())
        self._acc = None
        return k

    def retour(self, kind, dt, t_ga):
        avant = kind == SORTE_GAZ
        k = super().retour(kind, dt, t_ga)
        if k: self.u[(kind == SORTE_GAZ) & ~avant] = U_PLANCHER      # gaz rendu par les étoiles : tiède
        return k
