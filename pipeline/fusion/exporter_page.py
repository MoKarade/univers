#!/usr/bin/env python3
"""R10 (lot G) : extrait du calcul complet de la fusion (fusion.json de calcul.py) ce que la page rejoue pour le Groupe local.

Écrit fusion_centres.json (fichier joint à la page) :
- t : dates des images (Ga depuis aujourd'hui) ;
- c : centres de la Voie lactée, d'Andromède, du Triangle et du Grand Nuage, MOINS le centre de la Voie lactée
      (repère galactocentrique de la page, kpc), Float32 en base64, n × 4 × 3 ;
- sun : traceur Soleil moins le centre de la Voie lactée, n × 3 ; tr : les 38 autres traceurs (naines), n × 38 × 3 ;
- lgv : numéro de chaque naine dans DATA.LGV (même ordre que conditions.json, Triangle exclu, car il a ses particules) ;
- fusion_ga, derive_max, vitesse_m31 : résumé du calcul.
Usage : python exporter_page.py <dossier du résultat> <sortie.json>
"""
import base64, json, os, struct, sys


def main():
    src, dst = sys.argv[1], sys.argv[2]
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(src, 'fusion.json'), encoding='utf-8') as fh:
        m = json.load(fh)
    with open(os.path.join(here, 'conditions.json'), encoding='utf-8') as fh:
        ci = json.load(fh)
    dw = [d for d in ci['dwarfs'] if 'Triangle' not in d['name']]
    assert [d['name'] for d in dw] == m['traceurs'][1:], 'ordre des traceurs différent de conditions.json'
    f32 = lambda xs: base64.b64encode(struct.pack('<%df' % len(xs), *xs)).decode()
    C, T = m['centres'], m['traceurs_pos']
    c, sun, tr = [], [], []
    for k in range(len(m['t'])):
        mw = C[k][0]
        for g in C[k]: c += [g[i] - mw[i] for i in range(3)]
        sun += [T[k][0][i] - mw[i] for i in range(3)]
        for p in T[k][1:]: tr += [p[i] - mw[i] for i in range(3)]
    out = dict(t=m['t'], gal=m['galaxies'], c=f32(c), sun=f32(sun), tr=f32(tr), lgv=[d['i'] for d in dw], fusion_ga=m['fusion_ga'],
               derive_max=m['derive_max'], vitesse_m31=m['vitesse_m31'], image_ma=m['image_ma'],
               source='Calcul complet de la fusion (R9 : 300 000 particules, falcON, tâche GitHub 43119915874, 12 novembre 2026)')
    with open(dst, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print('écrit', dst, os.path.getsize(dst), 'octets')


if __name__ == '__main__':
    main()
