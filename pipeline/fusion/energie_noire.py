#!/usr/bin/env python3
"""Énergie noire dans les calculs de gravité du Groupe local (demande de Marc, 13/11/2026 : « jamais négliger l'énergie noire »).

Avec une constante cosmologique (w = -1), l'énergie noire pousse chaque masse loin du centre de masse du système avec une
accélération proportionnelle à la distance (équation de Friedmann pour l'accélération appliquée à un système lié) :

    a_Λ = H0² Ω_Λ r

Ordre de grandeur [Probable, calcul fait ici] : à 770 kpc (Andromède), 2,4 (km/s)²/kpc, soit environ 15 % de l'attraction
de la Voie lactée et d'Andromède réunies (2e12 M☉) ; au Grand Nuage (50 kpc), 0,01 % de l'attraction de la Voie lactée.
Littérature : Peñarrubia et al. 2014 (MNRAS 443, 2204), Partridge, Lahav et Hoffman 2013 (MNRAS 436, L45) : l'énergie
noire change de 10 à 15 % la masse du Groupe local déduite du mouvement d'Andromède.

Cosmologie : celle de l'appli (natif/src/cosmologie.h, Planck 2018) : H0 = 67,4 km/s/Mpc, Ω_Λ = 0,685.
Le réglage w0/wa de l'appli ne change pas ces calculs faits à l'avance (w = -1 ici) : l'écran le dit.
Unités : kpc, km/s, temps kpc/(km/s).
"""
import numpy as np

H0_KMS_MPC = 67.4
OMEGA_LAMBDA = 0.685
H0_KMS_KPC = H0_KMS_MPC / 1000.0
K_LAMBDA = H0_KMS_KPC ** 2 * OMEGA_LAMBDA      # (km/s)² / kpc², ≈ 3,11e-3


def acceleration(pos, centre=None, xp=np):
    """Accélération de l'énergie noire sur des positions (N, 3) en kpc ; centre : centre de masse (origine par défaut)."""
    r = pos if centre is None else pos - centre
    return K_LAMBDA * r


def potentiel(pos, centre=None, xp=np):
    """Potentiel associé, φ_Λ = -½ K r² ((km/s)²), pour le contrôle de l'énergie."""
    r = pos if centre is None else pos - centre
    return -0.5 * K_LAMBDA * xp.sum(r * r, axis=-1)


if __name__ == '__main__':
    G = 4.30091e-6
    for nom, r, m in (('Andromède (770 kpc, MW + M31 = 2e12 M☉)', 770.0, 2e12), ('Grand Nuage (50 kpc, MW 1e12 M☉)', 50.0, 1e12)):
        a_l, a_g = K_LAMBDA * r, G * m / r ** 2
        print(f'{nom} : énergie noire {a_l:.3f}, gravité {a_g:.3f} (km/s)²/kpc, rapport {100 * a_l / a_g:.3f} %')
