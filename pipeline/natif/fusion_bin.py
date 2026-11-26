#!/usr/bin/env python3
"""Lot G natif : centres et traceurs du calcul complet de la fusion (fusion.json de pipeline/fusion/calcul.py) en binaire
pour natif/physique/groupe_local.h. Les images des étoiles (kf_NNN.bin) sont lues telles quelles.
Sortie : en-tête Float64 [version 1, n images, pas (Ga), nb galaxies 4, nb traceurs, quantum kpc, fusion_ga, dérive max,
nb étoiles mw, m31, m33, lmc], puis Float64 : centres n × 4 × 3 (repère du centre de masse, kpc), traceurs n × T × 3,
puis la liste des fichiers kf (nom sur 16 octets, nombre d'images en Float64).
Usage : python fusion_bin.py <dossier du calcul> <sortie.bin>"""
import json, math, os, struct, sys

KF_NAME_MAX_BYTES = 16
_MAX_FRAMES = 10_000_000
_MAX_TRACEURS = 1_000_000
_INT32_MAX = (1 << 31) - 1
_MAX_GAL_STARS = _INT32_MAX // 12
_MAX_TOTAL_STARS = _INT32_MAX // 3


def _is_real_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def pack_fusion(m):
    """Sérialise fusion.json au format binaire attendu par natif/physique/groupe_local.h."""
    t = m['t']
    n, T = len(t), len(m['traceurs'])
    if n < 2 or n > _MAX_FRAMES:
        raise ValueError(f"nombre d'images invalide dans fusion.json (attendu 2..{_MAX_FRAMES}), reçu {n}")
    if not (_is_real_number(t[0]) and _is_real_number(t[1])):
        raise ValueError(f"instants t[0..1] invalides dans fusion.json : {t[:2]!r}")
    dt = t[1] - t[0]
    if not (math.isfinite(dt) and dt > 0.0):
        raise ValueError(f"pas temporel dt doit être fini et strictement positif, reçu {dt!r}")
    if T < 1 or T > _MAX_TRACEURS:
        raise ValueError(f"nombre de traceurs invalide (attendu 1..{_MAX_TRACEURS}), reçu {T}")

    q = m['quantum_kpc']
    if not _is_real_number(q) or not (math.isfinite(q) and q > 0.0):
        raise ValueError(f"quantum_kpc doit être fini et strictement positif, reçu {q!r}")

    raw_fusion_ga = m['fusion_ga']
    if raw_fusion_ga is None:
        fusion_ga = math.nan
    else:
        if not _is_real_number(raw_fusion_ga) or math.isinf(raw_fusion_ga):
            raise ValueError(f"fusion_ga doit être fini, NaN ou None, reçu {raw_fusion_ga!r}")
        fusion_ga = float(raw_fusion_ga)

    derive_max = m['derive_max']
    if not _is_real_number(derive_max) or not math.isfinite(derive_max):
        raise ValueError(f"derive_max doit être fini, reçu {derive_max!r}")

    affichees = m['affichees']
    if len(affichees) != 4:
        raise ValueError(f"affichees doit contenir exactement 4 galaxies, reçu {len(affichees)}")
    total_stars = 0
    for idx, v in enumerate(affichees):
        if not _is_real_number(v) or not math.isfinite(v) or not float(v).is_integer() or v < 0 or v > _MAX_GAL_STARS:
            raise ValueError(f"affichees[{idx}] doit être un entier >= 0 (<= {_MAX_GAL_STARS}), reçu {v!r}")
        total_stars += int(v)
    if total_stars > _MAX_TOTAL_STARS:
        raise ValueError(f"somme des étoiles affichées dépasse {_MAX_TOTAL_STARS} : {total_stars}")

    fichiers = m['fichiers']
    if len(fichiers) > _MAX_FRAMES:
        raise ValueError(f"trop de fichiers kf ({len(fichiers)} > {_MAX_FRAMES})")

    hdr = [1, n, dt, 4, T, q, fusion_ga, derive_max] + list(affichees)
    parts = [
        struct.pack('<%dd' % len(hdr), *hdr),
        struct.pack('<%dd' % (n * 12), *[x for c in m['centres'] for g in c for x in g]),
        struct.pack('<%dd' % (n * T * 3), *[x for c in m['traceurs_pos'] for g in c for x in g]),
        struct.pack('<d', len(fichiers)),
    ]
    for f, k in fichiers:
        if not isinstance(f, str):
            raise ValueError(f"nom de fichier kf doit être une chaîne, reçu {f!r}")
        encoded = f.encode('utf-8')
        if not encoded:
            raise ValueError("nom de fichier kf vide interdit")
        if len(encoded) > KF_NAME_MAX_BYTES:
            raise ValueError(
                f"nom de fichier kf trop long pour le champ fixe de {KF_NAME_MAX_BYTES} octets : "
                f"{f!r} ({len(encoded)} octets UTF-8)"
            )
        if b'\0' in encoded:
            raise ValueError(f"nom de fichier kf invalide (octet nul) : {f!r}")
        if not _is_real_number(k) or not math.isfinite(k) or k < 0 or not float(k).is_integer() or k > n:
            raise ValueError(f"nombre d'images k invalide pour {f!r} (attendu entier dans 0..{n}), reçu {k!r}")
        parts.append(encoded.ljust(KF_NAME_MAX_BYTES, b'\0') + struct.pack('<d', k))
    return b''.join(parts)


def convert(src, dst):
    with open(os.path.join(src, 'fusion.json'), encoding='utf-8') as fh:
        m = json.load(fh)
    b = pack_fusion(m)
    with open(dst, 'wb') as fh:
        fh.write(b)
    return m, b


def main():
    src, dst = sys.argv[1], sys.argv[2]
    m, b = convert(src, dst)
    print('écrit', dst, len(b), 'octets ;', len(m['t']), 'images,', len(m['traceurs']), 'traceurs')


if __name__ == '__main__':
    main()
