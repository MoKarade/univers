#!/usr/bin/env python3
"""Le gaz d'une galaxie dans le calcul : pression, chocs, et naissance d'étoiles. [Modèle, signalé comme tel]

S'appuie sur gaz_gpu.py (hydrodynamique à particules lissées, contrôlée par essai_gaz.py). Les particules de gaz sont
celles de sorte 3 des galaxies de départ (modeles_v2.py) ; jusqu'ici elles n'étaient que des étoiles froides.

Choix physiques, tous des modèles simples et publiés, à dire à l'écran :
- gaz isotherme à 10 km/s de vitesse du son (gaz tiède à ~10 000 K, qui porte l'essentiel de la masse du gaz d'un disque) :
  le chauffage et le refroidissement ne sont pas calculés, on suppose qu'ils s'équilibrent à cette température ;
- plancher de pression de Jeans : la pression ne descend jamais sous celle qui garde la longueur de Jeans égale à
  N_JEANS longueurs de lissage (c² >= G rho (N_JEANS h)² / pi ; Bate & Burkert 1997, Robertson & Kravtsov 2008), pour
  que le gaz ne se fragmente pas en grumeaux plus petits que ce que le calcul peut résoudre ;
- naissance d'étoiles : au-dessus de SEUIL_NH atomes d'hydrogène par cm³, une particule de gaz devient une particule
  d'étoiles (sorte 5, « née pendant le calcul ») avec la probabilité 1 - exp(-EFFICACITE dt / t_chute), où t_chute est le
  temps de chute libre du gaz, sqrt(3 pi / (32 G rho)) (loi de Schmidt 1959 ; Katz 1992 ; EFFICACITE ~1 % par temps de
  chute libre, Krumholz & Tan 2007). La masse est conservée : la particule change de nature, pas de masse.
Ce qui manque encore : chauffage par les explosions d'étoiles (rétroaction), gaz chaud, enrichissement chimique.

Unités du calcul : kpc, km/s, M☉ ; temps en kpc/(km/s).
"""
import math

import numpy as np
import cupy as cp

import gaz_gpu

G = 4.30091e-6
CS = 10.0                 # km/s
N_JEANS = 4.0
SEUIL_NH = 0.1            # cm^-3 (seuil de naissance d'étoiles, ordre de grandeur des simulations EAGLE : Schaye et al. 2015)
# 1 M☉/kpc³ = 1e-9 M☉/pc³ = 1e-9 x 40,46 protons/cm³ ; avec 76 % d'hydrogène : n_H = 3,075e-8 cm^-3 par M☉/kpc³
NH_PAR_MSOL_KPC3 = 0.76 * 40.46e-9
EFFICACITE = 0.01
H_MIN, H_MAX = 0.02, 2.0  # kpc
SORTE_GAZ, SORTE_NEE = 3, 5


class Gaz:
    """Gaz d'un ensemble de particules (une galaxie, ou plusieurs assez proches pour tenir en simple précision)."""

    def __init__(self, n_total, graine=20261118):
        self.h = cp.full(n_total, 0.2)            # longueur de lissage de chaque particule (seules celles de gaz servent)
        self.rho = cp.zeros(n_total)
        self.naissance = np.full(n_total, np.nan)  # date de naissance (Ga) des étoiles nées pendant le calcul
        self.rng = cp.random.default_rng(graine)
        self.cfl = 0.0
        self.nees = 0

    def acceleration(self, pos, vel, m, qui, dt):
        """Accélération de pression et de viscosité des particules d'indices `qui` (tableau CuPy). Met à jour h, rho et
        le nombre de Courant le plus grand (dt vsig / h : doit rester sous ~0,3)."""
        if int(qui.shape[0]) < 100: return None
        p, v, mm = pos[qui], vel[qui], m[qui]
        r = gaz_gpu.sph(p, v, mm, self.h[qui], cs=CS, h_min=H_MIN, h_max=H_MAX, passes=2)
        rho, h = r['rho'], r['h']
        # plancher de Jeans : refait le calcul des forces avec la vitesse du son relevée là où il le faut
        c2 = cp.maximum(CS * CS, G * rho * (N_JEANS * h) ** 2 / math.pi)
        if float(c2.max()) > CS * CS * 1.0001:
            r = gaz_gpu.sph(p, v, mm, h, cs=cp.sqrt(c2), h_min=H_MIN, h_max=H_MAX, passes=1)
        self.h[qui] = r['h']; self.rho[qui] = r['rho']
        self.cfl = float((dt * r['vsig'] / r['h']).max())
        return r['acc']

    def naissances(self, kind, qui, dt, t_ga):
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
            self.naissance[cp.asnumpy(idx)] = t_ga
            self.nees += k
        return k
