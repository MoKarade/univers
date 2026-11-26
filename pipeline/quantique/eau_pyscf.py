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
import base64, json, math, sys
from pathlib import Path
import numpy as np
from pyscf import gto, scf
from pyscf.dft import numint

_PIPE_DIR = str(Path(__file__).resolve().parents[1])
if _PIPE_DIR not in sys.path:
    sys.path.insert(0, _PIPE_DIR)
from _paths import APP_GEN  # noqa: E402

DST = APP_GEN / 'water_qm.js'
HA_TO_EV = 27.211386245988            # CODATA 2022
NPTS, Q = 16000, 0.001                # points tirés ; pas des entiers 16 bits : 0,001 Å


def hydrogene():
    m = gto.M(atom='H 0 0 0', basis='aug-cc-pv5z', spin=1, verbose=0)
    mf = scf.UHF(m).run()
    D = mf.make_rdm1()[0] + mf.make_rdm1()[1]
    r2 = float(np.einsum('ij,ji', D, m.intor('int1e_r2')))      # en bohr², soit a₀²
    # forme : densité radiale P(r) = 4π r² ρ(r), calculée le long de trois axes et moyennée, contre la formule exacte 4 r² e^(−2r)
    r = np.linspace(0.05, 8.0, 160); P = np.zeros_like(r)
    for ax in np.eye(3):
        c = r[:, None] * ax[None, :]; P += 4 * np.pi * r * r * numint.eval_rho(m, numint.eval_ao(m, c), D) / 3
    Pex = 4 * r * r * np.exp(-2 * r)
    ecart = float(np.max(np.abs(P - Pex)) / Pex.max())
    return dict(E=float(mf.e_tot), E_exact=-0.5, r2=r2, r2_exact=3.0, base='aug-cc-pV5Z', r=[round(float(x), 4) for x in r], P=[round(float(x), 6) for x in P], ecart_forme=ecart)


def eau():
    HB, HA = 0.9572, math.radians(104.52 / 2)
    m = gto.M(atom=[['O', (0, 0, 0)], ['H', (math.sin(HA) * HB, math.cos(HA) * HB, 0)], ['H', (-math.sin(HA) * HB, math.cos(HA) * HB, 0)]],
              basis='aug-cc-pvtz', unit='Angstrom', verbose=0)
    mf = scf.RHF(m).run()
    occ = mf.mo_energy[mf.mo_occ > 0] * HA_TO_EV
    # densité sur deux grilles : fine (0,0045 Å) dans un cube de ±0,225 Å autour de l'oxygène, pour la couche interne 1s, très resserrée ;
    # 0,05 Å ailleurs, de −2,5 à +2,5 Å (x et z) et de −2,3 à +2,7 Å (y), sans le cube fin
    D = mf.make_rdm1()
    def grille(h, xs, ys, zs, sauf=None):
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij'); C = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        if sauf is not None: C = C[np.max(np.abs(C), axis=1) > sauf + 1e-9]      # cases grossières entièrement hors du cube fin
        rho = np.empty(len(C))
        for k in range(0, len(C), 50000):
            rho[k:k + 50000] = numint.eval_rho(m, numint.eval_ao(m, C[k:k + 50000] / 0.529177210544), D)      # PySCF attend des bohrs
        return C, np.clip(rho, 0, None) * (h / 0.529177210544) ** 3, h
    hf = 0.0045; f = np.arange(-0.225 + hf / 2, 0.225, hf)      # cube fin ±0,225 Å, aligné sur les bords des cases grossières de 0,05 Å
    G1 = grille(hf, f, f, f); hc = 0.05
    G2 = grille(hc, np.arange(-2.5, 2.5 + 1e-9, hc), np.arange(-2.3, 2.7 + 1e-9, hc), np.arange(-2.5, 2.5 + 1e-9, hc), sauf=0.2)
    C = np.concatenate([G1[0], G2[0]]); w = np.concatenate([G1[1], G2[1]]); hh = np.concatenate([np.full(len(G1[0]), hf), np.full(len(G2[0]), hc)])
    nel = float(w.sum())
    rng = np.random.default_rng(20261111)
    idx = rng.choice(len(C), size=NPTS, p=w / w.sum())
    pts = C[idx] + (rng.random((NPTS, 3)) - 0.5) * hh[idx, None]
    q = np.clip(np.round(pts / Q), -32767, 32767).astype('<i2')
    return dict(eps_eV=[round(float(e), 3) for e in occ], electrons_grille=round(nel, 3), E=float(mf.e_tot), base='aug-cc-pVTZ',
                pts=base64.b64encode(q.tobytes()).decode(), n=NPTS, q_A=Q)


def main():
    H = hydrogene(); W = eau()
    print(f"Hydrogène : forme P(r) à {100 * H['ecart_forme']:.3f} % de la formule exacte ; E = {H['E']:.6f} hartree (exact −0,5 : écart {100 * (H['E'] / -0.5 - 1):+.3f} %) ; ⟨r²⟩ = {H['r2']:.4f} a₀² (exact 3 : écart {100 * (H['r2'] / 3 - 1):+.3f} %)")
    print(f"Eau : E = {W['E']:.6f} hartree ; électrons sur la grille : {W['electrons_grille']} (10 attendus) ; −ε (eV) : {[-e for e in W['eps_eV']]}")
    out = dict(H=H, eau={k: v for k, v in W.items()}, methode='Hartree-Fock (PySCF)', src='PySCF : Sun et al. 2018, 2020 ; bases de Dunning (aug-cc-pVTZ, aug-cc-pV5Z)')
    with open(DST, 'w', encoding='utf-8', newline='\n') as f:
        f.write('/* généré par pipeline/quantique/eau_pyscf.py */\nObject.assign(DATA, ' + json.dumps({'WATER_QM': out}, ensure_ascii=False, separators=(',', ':')) + ');\n')


if __name__ == '__main__':
    main()
