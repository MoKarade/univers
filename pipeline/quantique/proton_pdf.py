#!/usr/bin/env python3
"""Contenu du proton d'après un jeu public de distributions de partons (R15).

Source : CT18NNLO, membre central (Hou et al. 2021, Phys. Rev. D 103, 014013), distribué par LHAPDF
(https://lhapdfsets.web.cern.ch/current/CT18NNLO.tar.gz). Le fichier .dat (format LHAPDF6) donne x·f(x, Q) sur une grille.
Pour chaque finesse λ (longueur sondée), Q = ħc/λ ; on intègre :
- les parts d'impulsion ∫ x f dx des quarks de valence (u − ū, d − d̄), des paires quark-antiquark de la mer, des gluons ;
- le compte net ∫ (u − ū) dx et ∫ (d − d̄) dx, qui doit valoir 2 et 1.
Écrit app/gen/proton_pdf.js. Usage : python proton_pdf.py <chemin de CT18NNLO_0000.dat>
"""
import sys, os, json, math
import numpy as np

HBARC = 1.97326980e-16          # GeV·m (CODATA)
HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, '..', '..', 'app', 'gen', 'proton_pdf.js')


def lire(path):
    txt = open(path).read().split('---')
    blocks = []
    for b in txt[1:]:
        lines = [l for l in b.strip().split('\n') if l.strip()]
        if len(lines) < 4: continue
        xs = np.array(lines[0].split(), float); qs = np.array(lines[1].split(), float); fl = [int(v) for v in lines[2].split()]
        vals = np.array([l.split() for l in lines[3:]], float).reshape(len(xs), len(qs), len(fl))
        blocks.append((xs, qs, fl, vals))
    return blocks


def xf_at(blocks, Q):
    """x·f(x, Q) sur la grille x du sous-bloc qui contient Q (interpolation linéaire en log Q)."""
    for xs, qs, fl, v in blocks:
        if qs[0] <= Q <= qs[-1]:
            j = min(np.searchsorted(qs, Q), len(qs) - 1); j = max(j, 1)
            w = (math.log(Q) - math.log(qs[j - 1])) / (math.log(qs[j]) - math.log(qs[j - 1]))
            return xs, {f: (1 - w) * v[:, j - 1, k] + w * v[:, j, k] for k, f in enumerate(fl)}
    raise ValueError(f'Q = {Q} hors de la grille')


def integrales(xs, xf):
    lx = np.log(xs); fine = np.linspace(lx[0], lx[-1], 40000); x = np.exp(fine)
    F = {k: np.interp(fine, lx, v) for k, v in xf.items()}      # x·f, interpolé en log x
    g = lambda arr: float(np.trapz(arr * x, fine))               # ∫ x·f dx = ∫ (x·f)·x d(ln x)
    n = lambda arr: float(np.trapz(arr, fine))                    # ∫ f dx = ∫ (x·f) d(ln x)
    uv, dv = F[2] - F[-2], F[1] - F[-1]
    sea = 2 * F[-2] + 2 * F[-1] + sum(F.get(k, 0) + F.get(-k, 0) for k in (3, 4, 5))
    return dict(uv=g(uv), dv=g(dv), sea=g(sea), g=g(F[21])), dict(u=n(uv), d=n(dv))


def main():
    blocks = lire(sys.argv[1])
    Qmin = max(blocks[0][1][0], 1.3); Qmax = min(blocks[-1][1][-1], 1e4)
    Qs = np.geomspace(Qmin, Qmax, 24)
    rows = []
    for Q in Qs:
        xs, xf = xf_at(blocks, Q)
        m, n = integrales(xs, xf)
        rows.append(dict(Q=round(float(Q), 4), lam=float('%.4g' % (HBARC / Q)), mom={k: round(v, 5) for k, v in m.items()}, n={k: round(v, 4) for k, v in n.items()}))
        print(f"Q = {Q:9.2f} GeV  λ = {HBARC / Q:.2e} m  valence u {m['uv']:.3f}  d {m['dv']:.3f}  mer {m['sea']:.3f}  gluons {m['g']:.3f}  somme {sum(m.values()):.4f}  |  u {n['u']:.3f}  d {n['d']:.3f}")
    out = dict(rows=rows, src='CT18NNLO, membre central (Hou et al. 2021, Phys. Rev. D 103, 014013), via LHAPDF', licence='aucune licence écrite pour les grilles (LHAPDF et CT18) ; l'article CT18 est sous CC BY 4.0 ; usage libre avec citation de Hou et al. 2021 et de LHAPDF6 (Buckley et al. 2015)')
    open(DST, 'w', encoding='utf-8', newline='\n').write('/* généré par pipeline/quantique/proton_pdf.py */\nObject.assign(DATA, ' + json.dumps({'PROTON_PDF': out}, ensure_ascii=False, separators=(',', ':')) + ');\n')


if __name__ == '__main__':
    main()
