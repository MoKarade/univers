#!/usr/bin/env python3
"""R10 (lot G) : images clés du calcul complet de la fusion, préparées pour la page.

Lit kf_NNN.bin et fusion.json (sortie de calcul.py : étoiles affichées en entiers 16 bits, pas 0,025 kpc, relatives au
centre de masse total) et écrit, par paquets de 25 images, des fichiers texte (base64) où chaque étoile est relative au
centre de la Voie lactée de la même image (repère galactocentrique de la page), en entiers 16 bits (pas 0,025 kpc).
Écrit aussi fusion_images.json : nombre d'images, étoiles par galaxie, pas de temps, paquets.
Usage : python exporter_images.py <dossier du résultat> <dossier de sortie>
"""
import base64, json, os, struct, sys

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
m = json.load(open(os.path.join(src, 'fusion.json'), encoding='utf-8'))
Q, NS = m['quantum_kpc'], sum(m['affichees'])
frames = []
for f, n in m['fichiers']:
    b = open(os.path.join(src, f), 'rb').read()
    assert len(b) == n * NS * 6, f
    for i in range(n): frames.append(b[i * NS * 6:(i + 1) * NS * 6])
assert len(frames) == len(m['t'])
PER, packs = 25, []
for p0 in range(0, len(frames), PER):
    out = bytearray()
    for k in range(p0, min(p0 + PER, len(frames))):
        a = struct.unpack('<%dh' % (NS * 3), frames[k]); mw = m['centres'][k][0]
        q = [round(mw[0] / Q), round(mw[1] / Q), round(mw[2] / Q)]
        out += struct.pack('<%dh' % (NS * 3), *[max(-32767, min(32767, a[j] - q[j % 3])) for j in range(NS * 3)])
    name = f'fusion_images_{p0 // PER:02d}.txt'
    open(os.path.join(dst, name), 'w').write(base64.b64encode(bytes(out)).decode())
    packs.append({'fichier': name, 'premiere': p0, 'images': min(PER, len(frames) - p0)})
meta = dict(t=m['t'], par_galaxie=dict(zip(m['galaxies'], m['affichees'])), quantum_kpc=Q, etoiles=NS, paquets=packs,
            source='Calcul complet de la fusion (R9), tâche GitHub 43119915874 ; étoiles relatives au centre de la Voie lactée')
json.dump(meta, open(os.path.join(dst, 'fusion_images.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(len(packs), 'paquets,', len(frames), 'images,', NS, 'étoiles')
