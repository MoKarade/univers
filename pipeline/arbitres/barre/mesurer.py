#!/usr/bin/env python3
"""Mesures de la barre et de l'épaisseur sur les instantanés GADGET-4, les mêmes que pipeline/fusion/stabilite_tir.py
(fonction releve, copiée telle quelle), plus :
- force A2 de la barre sur 0,5–4 kpc (un seul anneau) et son angle ;
- vitesse de rotation de la barre entre deux instantanés espacés de 10 Ma (km/s/kpc) ;
- longueur de la barre : rayon où A2 (anneaux de 0,5 kpc) retombe sous la moitié de son maximum, au-delà du maximum,
  ou bien où la phase s'écarte de plus de 10° de celle de la barre (le plus petit des deux) ;
- épaisseur (médiane de |z|) des vieilles étoiles (sortes 1 et 4) et des jeunes (sorte 3, disque froid), anneau 4–9 kpc,
  dans le plan propre du disque (perpendiculaire au moment cinétique des étoiles à moins de 10 kpc) ET dans le plan xy.
Types GADGET → sortes : 1 → 0 (matière noire), 2 → 1, 3 → 3, 4 → 4 (voir npz_vers_gadget.py).
Le même calcul est aussi appliqué à notre tir GPU (fichier .json de stabilite_tir.py) pour la vitesse de la barre.
Usage : python3 mesurer.py <dossier output> <sortie.json>
"""
import glob
import json
import os
import sys

import h5py
import numpy as np

T_UNIT = 0.9778      # Ga par unité de temps
KMS_KPC = 1.0227121650456      # (km/s/kpc) -> rad/Ga
ANNEAUX = [(0.5, 2), (2, 4), (4, 6), (6, 9), (9, 13)]
KIND_DE_TYPE = {1: 0, 2: 1, 3: 3, 4: 4}


def releve(pos, vel, m, kind, t, e_rel, cm):
    """Copie de pipeline/fusion/stabilite_tir.py:releve (mesures sur les étoiles du disque, sortes 1 et 4)."""
    etoiles = (kind == 1) | (kind == 4)
    p = pos[etoiles]; v = vel[etoiles]; w = m[etoiles]
    c = np.average(p, axis=0, weights=w)
    for _ in range(8):
        sel = np.linalg.norm(p - c, axis=1) < 5
        c = np.average(p[sel], axis=0, weights=w[sel])
    p = p - c
    v = v - np.average(v[np.linalg.norm(p, axis=1) < 5], axis=0)
    R = np.hypot(p[:, 0], p[:, 1]); phi = np.arctan2(p[:, 1], p[:, 0])
    vR = (p[:, 0] * v[:, 0] + p[:, 1] * v[:, 1]) / np.maximum(R, 1e-9)
    vphi = (p[:, 0] * v[:, 1] - p[:, 1] * v[:, 0]) / np.maximum(R, 1e-9)
    out = dict(t=round(t, 4), energie=e_rel, centre_de_masse_kpc=cm, anneaux=[])
    for a, b in ANNEAUX:
        s = (R >= a) & (R < b)
        if s.sum() < 100:
            out['anneaux'].append(None); continue
        z2 = np.sum(w[s] * np.exp(2j * phi[s])) / np.sum(w[s])
        out['anneaux'].append(dict(r=[a, b], a2=round(float(abs(z2)), 4), angle_deg=round(float(np.degrees(np.angle(z2)) / 2), 1), n=int(s.sum()),
                                   epaisseur_kpc=round(float(np.median(np.abs(p[s, 2]))), 3), sigma_r=round(float(np.std(vR[s])), 1),
                                   v_rotation=round(float(np.mean(vphi[s])), 1)))
    return out


def lire(fichier):
    with h5py.File(fichier, 'r') as f:
        t = float(f['Header'].attrs['Time']) * T_UNIT
        pos, vel, m, kind, pot = [], [], [], [], []
        for typ, k in KIND_DE_TYPE.items():
            g = f.get(f'PartType{typ}')
            if g is None:
                continue
            pos.append(g['Coordinates'][:].astype(np.float64)); vel.append(g['Velocities'][:].astype(np.float64))
            m.append(g['Masses'][:].astype(np.float64) * 1e10); kind.append(np.full(len(g['Masses']), k, dtype=np.int8))
            if 'Potential' in g:
                pot.append(g['Potential'][:].astype(np.float64) * 1e10)
    return t, np.concatenate(pos), np.concatenate(vel), np.concatenate(m), np.concatenate(kind), (np.concatenate(pot) if pot else None)


def centre_et_plan(pos, vel, m, kind):
    """Centre des étoiles (même méthode que releve) et rotation qui met leur moment cinétique (< 10 kpc) sur +z."""
    s = (kind == 1) | (kind == 4)
    p, v, w = pos[s], vel[s], m[s]
    c = np.average(p, axis=0, weights=w)
    for _ in range(8):
        sel = np.linalg.norm(p - c, axis=1) < 5
        c = np.average(p[sel], axis=0, weights=w[sel])
    vc = np.average(v[np.linalg.norm(p - c, axis=1) < 5], axis=0)
    q = p - c; u = v - vc; sel = np.linalg.norm(q, axis=1) < 10
    L = np.sum(w[sel, None] * np.cross(q[sel], u[sel]), axis=0); n = L / np.linalg.norm(L)
    ez = n; ex = np.cross([0, 1, 0], ez); ex = ex / np.linalg.norm(ex) if np.linalg.norm(ex) > 1e-8 else np.array([1.0, 0, 0])
    ey = np.cross(ez, ex)
    return c, vc, np.vstack([ex, ey, ez]), float(np.degrees(np.arccos(np.clip(n[2], -1, 1))))


def barre(pos, m, kind, c, rot=None):
    """A2 et angle sur 0,5–4 kpc, et longueur de la barre, dans le plan xy (ou le plan propre si rot est donné)."""
    s = (kind == 1) | (kind == 4)
    p = pos[s] - c; w = m[s]
    if rot is not None:
        p = p @ rot.T
    R = np.hypot(p[:, 0], p[:, 1]); ph = np.arctan2(p[:, 1], p[:, 0])
    s4 = (R >= 0.5) & (R < 4)
    z = np.sum(w[s4] * np.exp(2j * ph[s4])) / np.sum(w[s4])
    a2, ang = abs(z), np.angle(z) / 2
    bords = np.arange(0.0, 12.01, 0.5); prof = []
    for a, b in zip(bords[:-1], bords[1:]):
        k = (R >= a) & (R < b)
        zz = np.sum(w[k] * np.exp(2j * ph[k])) / max(np.sum(w[k]), 1e-30)
        prof.append((0.5 * (a + b), abs(zz), np.angle(zz) / 2))
    i_max = int(np.argmax([x[1] for x in prof[:10]]))      # maximum dans les 5 kpc centraux
    longueur = prof[-1][0]
    for r, amp, phase in prof[i_max:]:
        dphi = abs((phase - ang + np.pi / 2) % np.pi - np.pi / 2)
        if amp < 0.5 * prof[i_max][1] or np.degrees(dphi) > 10:
            longueur = r; break
    return float(a2), float(ang), float(longueur), [(round(r, 2), round(float(a), 4)) for r, a, _ in prof]


def epaisseurs(pos, m, kind, c, rot):
    out = {}
    for nom, sorte in (('vieilles', (1, 4)), ('jeunes', (3,))):
        s = np.isin(kind, sorte); p = pos[s] - c
        for plan, q in (('plan_propre', p @ rot.T), ('plan_xy', p)):
            R = np.hypot(q[:, 0], q[:, 1]); k = (R >= 4) & (R < 9)
            out[f'{nom}_{plan}_kpc'] = round(float(np.median(np.abs(q[k, 2]))), 3)
    return out


def vitesse_barre(t1, a1, t2, a2):
    """Vitesse de rotation (km/s/kpc) entre deux angles de barre (définis à π près), écart supposé < π/2."""
    d = (a2 - a1 + np.pi / 2) % np.pi - np.pi / 2
    return d / (t2 - t1) / KMS_KPC


def energie(vel, m, pot):
    return None if pot is None else 0.5 * float(np.sum(m * np.sum(vel ** 2, axis=1))) + 0.5 * float(np.sum(m * pot))


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    fichiers = sorted(glob.glob(os.path.join(dossier, 'snapshot_*.hdf5')))
    res = dict(source=os.path.abspath(dossier), releves=[])
    e0 = None; prec = None
    for f in fichiers:
        t, pos, vel, m, kind, pot = lire(f)
        e = energie(vel, m, pot); e0 = e0 if e0 is not None else e
        r = releve(pos, vel, m, kind, t, (e / e0 - 1) if e is not None and e0 else None, None)
        c, vc, rot, incl = centre_et_plan(pos, vel, m, kind)
        a2, ang, lon, prof = barre(pos, m, kind, c)
        a2p, angp, lonp, _ = barre(pos, m, kind, c, rot)
        r.update(a2_barre=round(a2, 4), angle_barre_deg=round(np.degrees(ang), 2), longueur_barre_kpc=lon,
                 a2_barre_plan_propre=round(a2p, 4), longueur_barre_plan_propre_kpc=lonp, inclinaison_plan_deg=round(incl, 2),
                 profil_a2=prof, **epaisseurs(pos, m, kind, c, rot))
        if prec is not None and 0 < t - prec[0] < 0.0151:      # paire espacée de 10 Ma
            r['vitesse_barre_kms_kpc'] = round(float(vitesse_barre(prec[0], prec[1], t, angp)), 1)
        prec = (t, angp)
        res['releves'].append(r)
        print(f"t={t:6.3f} Ga A2={a2:.3f} L={lon:.1f} kpc Ωb={r.get('vitesse_barre_kms_kpc', '')} "
              f"h_vieilles={r['vieilles_plan_propre_kpc']} h_jeunes={r['jeunes_plan_propre_kpc']} E={r['energie']}", flush=True)
        json.dump(res, open(sortie + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False); os.replace(sortie + '.tmp', sortie)


if __name__ == '__main__':
    main()
