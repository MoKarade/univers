#!/usr/bin/env python3
"""Nuage d'électrons de la molécule d'eau et contrôle sur l'hydrogène, calculés par chimie quantique (R14).

Logiciel : PySCF (Sun et al. 2018, WIREs Comput. Mol. Sci. 8, e1340 ; 2020, J. Chem. Phys. 153, 024109), libre (Apache 2.0).
1. Hydrogène, contrôle de la méthode : Hartree-Fock non restreint, base aug-cc-pV5Z. Pour un seul électron, la méthode est
   exacte à la base près ; on compare l'énergie (exacte : −0,5 hartree) et ⟨r²⟩ de l'état fondamental (exact : 3 a₀²).
2. Eau, géométrie expérimentale de la page (O–H 0,9572 Å, angle 104,52°) : Hartree-Fock, base aug-cc-pVTZ.
   - densité électronique sur une grille, puis 16 000 points tirés selon cette densité (positions en Å, repère de la page :
     O à l'origine, H dans le plan xy, bissectrice selon +y) ;
   - énergies des orbitales occupées (théorème de Koopmans : énergie d'ionisation ≈ −ε), à comparer aux mesures.
Écrit app/gen/water_qm.js. Usage : python eau_pyscf.py
"""
import os, json, math, base64
import numpy as np
from pyscf import gto, scf
from pyscf.dft import numint

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, '..', '..', 'app', 'gen', 'water_qm.js')
HA_TO_EV = 27.211386245988            # CODATA 2022
NPTS, Q = 16000, 0.001                # points tirés ; pas des entiers 16 bits : 0,001 Å


def hydrogene():
    m = gto.M(atom='H 0 0 0', basis='aug-cc-pv5z', spin=1, verbose=0)
    mf = scf.UHF(m).run()
    D = mf.make_rdm1()[0] + mf.make_rdm1()[1]
    r2 = float(np.einsum('ij,ji', D, m.intor('int1e_r2'))) / (0.529177210544 / 0.529177210544) ** 2      # bohr² = a₀²
    return dict(E=float(mf.e_tot), E_exact=-0.5, r2=r2, r2_exact=3.0, base='aug-cc-pV5Z')


def eau():
    HB, HA = 0.9572, math.radians(104.52 / 2)
    m = gto.M(atom=[['O', (0, 0, 0)], ['H', (math.sin(HA) * HB, math.cos(HA) * HB, 0)], ['H', (-math.sin(HA) * HB, math.cos(HA) * HB, 0)]],
              basis='aug-cc-pvtz', unit='Angstrom', verbose=0)
    mf = scf.RHF(m).run()
    occ = mf.mo_energy[mf.mo_occ > 0] * HA_TO_EV
    # densité sur une grille de 0,05 Å, de −2,5 à +2,5 Å (en x et z) et de −2,3 à +2,7 Å (en y)
    h = 0.05; xs = np.arange(-2.5, 2.5 + 1e-9, h); ys = np.arange(-2.3, 2.7 + 1e-9, h); zs = xs
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij'); C = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    D = mf.make_rdm1(); rho = np.empty(len(C))
    for k in range(0, len(C), 50000):
        c = C[k:k + 50000] / 0.529177210544        # PySCF attend des bohrs
        rho[k:k + 50000] = numint.eval_rho(m, numint.eval_ao(m, c), D)
    nel = float(rho.sum() * (h / 0.529177210544) ** 3)
    rng = np.random.default_rng(20261111)
    p = np.clip(rho, 0, None); p /= p.sum()
    idx = rng.choice(len(C), size=NPTS, p=p)
    pts = C[idx] + (rng.random((NPTS, 3)) - 0.5) * h
    q = np.clip(np.round(pts / Q), -32767, 32767).astype('<i2')
    return dict(eps_eV=[round(float(e), 3) for e in occ], electrons_grille=round(nel, 3), E=float(mf.e_tot), base='aug-cc-pVTZ',
                pts=base64.b64encode(q.tobytes()).decode(), n=NPTS, q_A=Q)


def main():
    H = hydrogene(); W = eau()
    print(f"Hydrogène : E = {H['E']:.6f} hartree (exact −0,5 : écart {100 * (H['E'] / -0.5 - 1):+.3f} %) ; ⟨r²⟩ = {H['r2']:.4f} a₀² (exact 3 : écart {100 * (H['r2'] / 3 - 1):+.3f} %)")
    print(f"Eau : E = {W['E']:.6f} hartree ; électrons sur la grille : {W['electrons_grille']} (10 attendus) ; −ε (eV) : {[-e for e in W['eps_eV']]}")
    out = dict(H=H, eau={k: v for k, v in W.items()}, methode='Hartree-Fock (PySCF)', src='PySCF : Sun et al. 2018, 2020 ; bases de Dunning (aug-cc-pVTZ, aug-cc-pV5Z)')
    open(DST, 'w', encoding='utf-8', newline='\n').write('/* généré par pipeline/quantique/eau_pyscf.py */\nObject.assign(DATA, ' + json.dumps({'WATER_QM': out}, ensure_ascii=False, separators=(',', ':')) + ');\n')


if __name__ == '__main__':
    main()
