#!/usr/bin/env python3
"""Contrôle de lumiere_hors_gaia.retrait_lisse (sans données téléchargées) : python test_lumiere_hors_gaia.py"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lumiere_hors_gaia as lhg

def essai():
    rng = np.random.default_rng(1)
    nz, ny, nx = 40, 60, 60
    modele = np.zeros((nz, ny, nx))
    # modèle creux : un traceur dans une case sur trois (comme 4 M de traceurs dans 8 M de cases)
    plein = rng.uniform(size=modele.shape) < 0.33
    modele[plein] = rng.uniform(1.0, 3.0, plein.sum())
    gaia = np.zeros_like(modele)
    gaia[15:25, 20:40, 20:40] = rng.uniform(0.0, 0.6, (10, 20, 20))      # la bulle Gaia, moins lumineuse que le modèle en moyenne
    retrait, reste = lhg.retrait_lisse(modele, gaia)
    # 1. jamais plus que le modèle, jamais négatif
    assert (retrait >= -1e-12).all() and (retrait <= modele + 1e-12).all()
    # 2. conservation : retiré + reste = lumière Gaia
    assert abs(retrait.sum() + reste - gaia.sum()) < 1e-9 * gaia.sum()
    # 3. l'ancien retrait par case perdait la lumière des cases vides ; le nouveau la retire presque toute
    ancien = np.minimum(modele, gaia).sum()
    assert ancien < 0.5 * gaia.sum(), ancien / gaia.sum()
    assert reste < 1e-3 * gaia.sum(), reste / gaia.sum()
    # 4. part gardée entre 0 et 1, et 1 loin de la bulle
    part = lhg.part_gardee(modele, retrait)
    assert (part >= 0).all() and (part <= 1).all() and np.allclose(part[:, :, :5], 1.0)
    # 5. modèle trop faible partout : la mesure est gardée, le reste le dit
    r2, reste2 = lhg.retrait_lisse(modele * 0.01, gaia)
    assert abs(r2.sum() - (modele * 0.01).sum()) < 1e-6 * gaia.sum() or reste2 > 0.5 * gaia.sum()
    print(f'PASSE : ancien retrait {ancien / gaia.sum():.1%} de Gaia, nouveau {retrait.sum() / gaia.sum():.2%}')

if __name__ == '__main__':
    essai()
