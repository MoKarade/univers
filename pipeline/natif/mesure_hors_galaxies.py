#!/usr/bin/env python3
"""Part de la lumière des étoiles du film du Groupe local qui se trouve loin de toute galaxie (docs/etoiles-hors-galaxies.md).

Pour chaque galaxie du film et quelques dates : part de sa lumière (champ « lum » des étoiles visibles) à plus de 30 et
100 kpc du centre de sa galaxie d'origine, et à plus de 50 kpc de TOUS les centres (étoiles vraiment hors galaxie).
Usage : python mesure_hors_galaxies.py [dossier du film] [dossier des étoiles visibles]
"""
import os, sys
import numpy as np, importlib.util
spec=importlib.util.spec_from_file_location('fv2',os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fusion', 'film_v2.py')); fv=importlib.util.module_from_spec(spec); spec.loader.exec_module(fv)
f=fv.Film(sys.argv[1] if len(sys.argv) > 1 else 'C:/tmp/natif/groupe-local-2/film'); TR=sys.argv[2] if len(sys.argv) > 2 else 'C:/tmp/natif/donnees/etoiles-visibles'
names=f.galaxies
lum=[np.load(f'{TR}/etoiles_visibles_{g}.npz')['lum'].astype(np.float64) for g in names]
print('lum share', [round(l.sum()/sum(x.sum() for x in lum)*100,2) for l in lum])
for T in [0,1,3,5.6,6.8,9,10]:
    i=int(np.argmin(abs(f.t-T))); C=np.array([f.centre(g,i) for g in range(5)])
    row=[]
    for g in range(5):
        p=f.positions(g,i)+C[g]
        d=np.min(np.stack([np.linalg.norm(p-C[k],axis=1) for k in range(5)]),axis=0)
        own=np.linalg.norm(f.positions(g,i),axis=1)
        L=lum[g]
        row.append(f'{names[g][:6]} own>30:{100*L[own>30].sum()/L.sum():.2f}% >100:{100*L[own>100].sum()/L.sum():.2f}% loinDeTout>50:{100*L[d>50].sum()/L.sum():.2f}%')
    print(f't={f.t[i]:.2f}', ' || '.join(row), flush=True)
