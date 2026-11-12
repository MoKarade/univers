#!/usr/bin/env python3
"""Contrôles des calculs de gaia_convertir.py et voie_lactee.py qui n'ont pas besoin des données (rapides, partout).

Les points tirés au hasard ne servent qu'à éprouver le découpage de l'arbre : ils ne sont jamais affichés.
Usage : python test_gaia_unitaire.py
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')      # accents lisibles dans la console Windows
import math, os, sys
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import gaia_convertir as gc
import voie_lactee as vl

ECHECS = []


def verifie(ok, quoi):
    print(('PASSE  ' if ok else 'ÉCHEC  ') + quoi)
    if not ok: ECHECS.append(quoi)


def morton_et_feuilles():
    rng = np.random.default_rng(0)
    q = rng.integers(0, 1 << 21, (200_000, 3))
    cles = np.sort(gc.morton(q))
    # le bit de poids fort de x est le bit 60, celui de z le bit 62
    verifie(int(gc.morton(np.array([[1 << 20, 0, 0]]))[0]) == 1 << 60 and int(gc.morton(np.array([[0, 0, 1 << 20]]))[0]) == 1 << 62,
            'ordre de Morton : bits entrelacés x, y, z')
    fs = gc.feuilles(cles)
    contigu = fs[0][0] == 0 and fs[-1][1] == len(cles) and all(a[1] == b[0] for a, b in zip(fs, fs[1:]))
    verifie(contigu, f'feuilles contiguës ({len(fs)} feuilles)')
    verifie(max(h - l for l, h in fs) <= gc.FEUILLE, 'aucune feuille au-delà de la limite')
    # chaque feuille est un cube de l'arbre : toutes ses clés partagent le même préfixe
    ok = True
    for l, h in fs:
        diff = int(cles[l]) ^ int(cles[h - 1])
        niveau = (63 - diff.bit_length()) // 3 if diff else 21
        ok &= (diff >> (3 * (21 - niveau))) == 0 if niveau < 21 else True
    verifie(ok, 'chaque feuille tient dans un seul cube de l’arbre')


def temperatures():
    bandes = os.environ.get('GAIA_BANDES', 'C:/tmp/natif/gaia/bandes/GaiaEDR3_passbands_zeropoints_version2')
    if not os.path.exists(os.path.join(bandes, 'passband.dat')):
        print('SAUTÉ  table des températures (bandes de Gaia absentes ; GAIA_BANDES)')
        return
    T = gc.temperatures(os.path.join(bandes, 'passband.dat'), os.path.join(bandes, 'zeropt.dat'))
    verifie(np.all(np.diff(T[:254]) <= 0), 'température décroissante quand BP-RP rougit')
    pas = int((0.82 - gc.BPRP0) / gc.BPRP_PAS)
    verifie(5300 < T[pas] < 6300, f'BP-RP 0,82 (Soleil, Casagrande et VandenBerg 2018) -> {T[pas]:.0f} K')


def bras():
    # sur chaque bras, au coude (beta_kink), le profil vaut 1 au rayon R_kink
    for nom, bmin, bmax, bk, rk, *_ in vl.BRAS:
        th = math.radians(180.0 - bk)
        v = vl.bras(np.array([rk * math.cos(th)]), np.array([rk * math.sin(th)]))[0]
        verifie(abs(v - 1) < 1e-9, f'bras {nom} : au coude ({bk}°, {rk} kpc)')
    # hors de l'étendue mesurée : rien (Local : beta de -8 à 34°)
    th = math.radians(180.0 - 120.0)
    verifie(vl.bras(np.array([8.26 * math.cos(th)]), np.array([8.26 * math.sin(th)]))[0] < 1e-6, 'bras Local absent hors de l’azimut mesuré')


def disque():
    m, e = vl.disque(np.array(vl.R0), np.array(0.0))
    L = 10 ** (-0.4 * (vl.M_V_TOTAL - vl.M_SUN_V))
    verifie(abs(L / 3.4e10 - 1) < 0.05, f'luminosité totale {L:.3e} L_sol (M_V = {vl.M_V_TOTAL:.2f})')
    verifie(abs(e / (m + e) - 0.036) < 0.02, f'part du disque épais au Soleil {e / (m + e):.3f} (BHG 2016 : 4 % ± 2)')
    h = 0.1344 + 0.0148 * (vl.R0 - 4.4)      # Drimmel et Spergel 2001, éq. 14
    rap = vl.poussiere_drimmel(np.array([vl.R0]), np.array([h]))[0] / vl.poussiere_drimmel(np.array([vl.R0]), np.array([0.0]))[0]
    verifie(abs(rap - 1 / math.cosh(1.0) ** 2) < 1e-12, 'poussière : sech²(z / h_d) avec l’évasement au rayon du Soleil')


if __name__ == '__main__':
    morton_et_feuilles(); temperatures(); bras(); disque()
    if ECHECS: sys.exit(f'{len(ECHECS)} échec(s)')
    print('tout passe')
