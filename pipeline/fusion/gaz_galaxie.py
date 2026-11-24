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
# Gaz « thermique » (Marc, 19/11/2026 : physique du gaz plus complète ; refait le 24/11/2026). [Modèle, signalé comme tel]
# En plus du gaz de base : l'énergie interne de chaque particule est suivie (compression, chocs), le gaz rayonne et se
# refroidit, et les étoiles le réchauffent en explosant. La physique est dans gaz_physique.py (contrôlée par
# essai_gaz_physique.py, sans carte graphique) :
# - refroidissement : courbe d'équilibre par collisions de Cholla, normalisation n_e n_i, intégrée EXACTEMENT à chaque
#   sous-pas (Townsend 2009) ; plancher de 10^4 K ; pression effective gardée comme plancher (Schaye & Dalla Vecchia 2008) ;
# - forme de du/dt de Monaghan (gaz_gpu.sph, energie='monaghan') : avec la forme « moyenne », le gaz froid voisin du gaz
#   chaud passait sous zéro et le plancher créait de l'énergie (+6,6 % sur l'explosion de Sedov, mesuré le 24/11) ;
# - explosions : chaque particule d'étoiles libère l'énergie de ses supernovæ au fil de son âge (à effondrement de 3,4 à
#   40 Ma selon la masse des étoiles, Raiteri et al. 1996, répartition de Chabrier 2003 ; puis Ia en 1/t dès 40 Ma,
#   Maoz & Mannucci 2012), 10^51 erg chacune ; étoiles du départ comprises (leurs Ia), d'après leurs âges supposés
#   (ages_de_depart). L'énergie va dans une réserve par particule ; des voisines de gaz sont chauffées de 10^7,5 K au
#   hasard avec la probabilité de Dalla Vecchia & Schaye 2012, tirée sur la réserve : registre exact (libérée = déposée +
#   réserve). Les remplaçantes du 19/11 chauffaient au moment de la naissance, sans délai.
# - bilan d'énergie suivi : libérée, déposée, rayonnée, ajoutée par les planchers (e_liberee, e_deposee, e_rayonnee,
#   e_plancher, en erg).
# Pas calculé : gaz sous 10^4 K, vents et lumière des étoiles massives, champ magnétique, rayons cosmiques, noyau actif,
# métaux (Z solaire). Tout le gaz avance au même sous-pas (pas de limiteur de pas individuel nécessaire).
import gaz_physique as gp

GAMMA = gp.GAMMA
K_PAR_U = gp.K_PAR_U                                                  # kelvins par (km/s)² d'énergie interne : 48,38
T_PLANCHER = gp.T_PLANCHER
U_PLANCHER = T_PLANCHER / K_PAR_U
SOUS_PAS_MAX_THERMIQUE = 256
VOISINES_CHAUFFE = 16          # candidates : les 16 particules de gaz les plus proches de l'étoile qui chauffe
ERG_PAR_MU = gp.M_SOL * 1.0e10  # erg pour 1 M☉ (km/s)²


class GazThermique(Gaz):
    """Gaz avec énergie interne suivie, refroidissement exact et explosions d'étoiles retardées. Même usage que Gaz.
    État en plus à sauvegarder : u (énergie interne), reserve (erg, par particule)."""

    def __init__(self, n_total, graine=20261124):
        super().__init__(n_total, graine)
        self.u = cp.full(n_total, U_PLANCHER)
        self.reserve = cp.zeros(n_total)
        self._du = None
        self.refroid = gp.Refroidissement('ne_ni')
        self.explo = gp.Explosions()
        self.rng_np = np.random.default_rng(graine)
        self.chauffees = 0
        self.e_liberee = self.e_deposee = self.e_rayonnee = self.e_plancher = 0.0

    def _plancher(self, u, rho, mm=None):
        """Énergie interne minimale : 10^4 K, et la pression effective au-dessus du seuil de naissance d'étoiles. Avec mm,
        l'énergie ajoutée par le plancher est comptée dans e_plancher."""
        u_eos = C_SEUIL2 * cp.cbrt(cp.maximum(rho, 0.0) * NH_PAR_MSOL_KPC3 / SEUIL_NH) / (GAMMA - 1.0)
        v = cp.maximum(u, cp.maximum(U_PLANCHER, cp.where(rho * NH_PAR_MSOL_KPC3 > SEUIL_NH, u_eos, 0.0)))
        if mm is not None:
            self.e_plancher += float((mm * (v - u)).sum()) * ERG_PAR_MU
        return v

    def _sph(self, p, v, mm, h, u):
        return gaz_gpu.sph(p, v, mm, h, u=u, gamma=GAMMA, h_min=H_MIN, h_max=H_MAX, passes=2, energie='monaghan')

    def avancer(self, pos, vel, m, qui, dt):
        n = int(qui.shape[0])
        if n < 100:
            pos[qui] += dt * vel[qui]; return 0
        p, v, mm = pos[qui], vel[qui], m[qui]
        u = self._plancher(self.u[qui], self.rho[qui], mm)
        if self._acc is None or self._acc.shape[0] != n:
            r = self._sph(p, v, mm, self.h[qui], u); self._acc, self._du = r['acc'], r['dudt']
            self.h[qui] = r['h']; self.rho[qui] = r['rho']; self._taux = float((r['vsig'] / r['h']).max())
        k = 1
        while k < SOUS_PAS_MAX_THERMIQUE and dt / k * self._taux > COURANT: k *= 2
        d = dt / k; h = self.h[qui]; rho = self.rho[qui]; pire = 0.0
        for _ in range(k):
            v += 0.5 * d * self._acc; u = self._plancher(u + 0.5 * d * self._du, rho, mm)
            p += d * v
            # forces à la fin du sous-pas avec vitesse et énergie PRÉDITES (comme essai_gaz.py) : la viscosité dépend de la
            # vitesse ; l'évaluer à mi-pas fait une erreur d'énergie du premier ordre dans les chocs des explosions
            r = self._sph(p, v + 0.5 * d * self._acc, mm, h, cp.maximum(u + 0.5 * d * self._du, U_PLANCHER)); h, rho = r['h'], r['rho']
            self._acc, self._du = r['acc'], r['dudt']
            v += 0.5 * d * self._acc; u = self._plancher(u + 0.5 * d * self._du, rho, mm)
            u2 = self.refroid.refroidir(u, rho, d, xp=cp)
            self.e_rayonnee += float((mm * (u - u2)).sum()) * ERG_PAR_MU
            u = self._plancher(u2, rho, mm)
            pire = max(pire, float((r['vsig'] / r['h']).max()))
        pos[qui] = p; vel[qui] = v; self.h[qui] = h; self.rho[qui] = rho; self.u[qui] = u
        self.cfl = d * pire; self._taux = pire; self.sous_pas = k
        return k

    def _ages(self, kind, t_ga):
        """Indices des particules d'étoiles (sortes 1, 2, 4, 5) et leur âge en ans (NaN si inconnu)."""
        etoile = (kind == 1) | (kind == 2) | (kind == 4) | (kind == SORTE_NEE)
        qui = cp.where(etoile)[0]
        nee = cp.asarray(self.naissance)[qui]
        age0 = self.age0[qui] if self.age0 is not None else cp.full(int(qui.shape[0]), cp.nan)
        return qui, cp.where(cp.isnan(nee), age0 + t_ga, t_ga - nee) * 1e9

    def naissances(self, kind, qui, dt, t_ga, pos=None, m=None):
        """Naissances (comme Gaz), puis explosions des étoiles selon leur âge."""
        k = super().naissances(kind, qui, dt, t_ga)
        if pos is not None and m is not None:
            self.exploser(kind, pos, m, dt, t_ga)
        return k

    def exploser(self, kind, pos, m, dt, t_ga):
        """Énergie des supernovæ du pas dans la réserve de chaque particule d'étoiles, puis chauffes de 10^7,5 K."""
        self._rendre_reserves(kind, m)
        et, age = self._ages(kind, t_ga)      # âge à la fin du pas ; énergie libérée entre âge - pas et âge
        connu = ~cp.isnan(age)
        et, age = et[connu], age[connu]
        if int(et.shape[0]) == 0: return 0
        pas_ans = dt * AN_PAR_UNITE
        dE = m[et] * self.explo.energie_liberee(cp.maximum(age - pas_ans, 0.0), pas_ans, xp=cp)
        self.reserve[et] += dE; self.e_liberee += float(dE.sum())
        gaz = cp.where(kind == SORTE_GAZ)[0]
        if int(gaz.shape[0]) < VOISINES_CHAUFFE: return 0
        q = gp.energie_quantum(float(cp.median(m[gaz])))
        n = gp.nombre_de_chauffes(self.reserve[et], q, self.rng, xp=cp)
        act = cp.where(n > 0)[0]
        if int(act.shape[0]) == 0: return 0
        actives = et[act]; n_act = cp.asnumpy(n[act])
        pg = pos[gaz]; vois = []
        for a in range(0, int(actives.shape[0]), 32):      # les plus proches voisines de gaz, par paquets
            pa = pos[actives[a:a + 32]]
            d2 = sum((pa[:, None, c] - pg[None, :, c]) ** 2 for c in range(3))
            vois.append(cp.argpartition(d2, VOISINES_CHAUFFE, axis=1)[:, :VOISINES_CHAUFFE])
        vois = cp.concatenate(vois)
        cand = cp.unique(vois.ravel())                      # le dépôt se fait sur ce petit sous-ensemble, sur le processeur
        loc = cp.asnumpy(cp.searchsorted(cand, vois))
        mg = cp.asnumpy(m[gaz[cand]]); ug = cp.asnumpy(self.u[gaz[cand]]); res = cp.asnumpy(self.reserve[actives])
        c, depose = gp.deposer(res, n_act, loc, mg, ug, self.rng_np)
        self.u[gaz[cand]] = cp.asarray(ug); self.reserve[actives] = cp.asarray(res)
        self.e_deposee += depose; self.chauffees += c
        self._acc = None
        return c

    def _rendre_reserves(self, kind, m):
        """Une particule d'étoiles redevenue gaz (retour de masse) garde sa réserve : on la lui rend en chaleur (positive ou
        négative, puis plancher compté dans e_plancher). Le registre reste exact."""
        r = cp.where((kind == SORTE_GAZ) & (self.reserve != 0))[0]
        if int(r.shape[0]) == 0: return
        avant = self.u[r] + self.reserve[r] / (m[r] * ERG_PAR_MU)
        self.e_deposee += float(self.reserve[r].sum()); self.reserve[r] = 0.0
        self.u[r] = cp.maximum(avant, U_PLANCHER)
        self.e_plancher += float((m[r] * (self.u[r] - avant)).sum()) * ERG_PAR_MU

    def retour(self, kind, dt, t_ga):
        """Retour de masse (comme Gaz) ; le gaz rendu par les étoiles part tiède (10^4 K)."""
        avant = kind == SORTE_GAZ
        k = super().retour(kind, dt, t_ga)
        if k: self.u[(kind == SORTE_GAZ) & ~avant] = U_PLANCHER
        return k
