import json, statistics
from simbad import q
names=["M 31","M 33","NAME LMC","NAME SMC","NGC 5128","M 81","M 87","NGC 1399","NGC 4874","NGC 1275","M 51","M 101","NGC 253","M 104","M 83","IC 342","NAME Sgr dSph","NAME Fornax Dwarf Spheroidal","NAME Sculptor Dwarf Galaxy","NAME Draco Dwarf Galaxy","NAME UMi Galaxy","NAME Carina dSph","NAME Sextans Dwarf Galaxy","NAME Leo I","NAME Leo II","NGC 6822","IC 10","M 32","M 110","IC 1613","NAME WLM Galaxy","NGC 185","NGC 147","NAME Leo A","NGC 3109"]
lst=",".join("'"+n.replace("'","''")+"'" for n in names)
rows=q(f"SELECT id, dist, unit, method FROM mesDistance JOIN ident ON mesDistance.oidref=ident.oidref WHERE id IN ({lst})")
U={'kpc':1e-3,'Mpc':1.0,'pc':1e-6,' pc':1e-6}
by={}
for r in rows:
    try:
        d=float(r['dist'])*U[r['unit'].strip()]
    except Exception as e:
        continue
    by.setdefault(' '.join(r['id'].split()),[]).append(d)
out={}
for k,v in sorted(by.items()):
    out[k]=dict(n=len(v), median=statistics.median(v), lo=min(v), hi=max(v))
    print(f"{k:32s} n={len(v):3d} median={statistics.median(v):9.4f} Mpc  range {min(v):.4f}-{max(v):.4f}")
json.dump(out, open('simbad_dist.json','w'), indent=1)
