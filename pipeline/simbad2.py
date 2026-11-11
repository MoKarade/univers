import json
from simbad import q
names=["M 42","M 1","NGC 3372","NGC 5139","M 16","M 45","NAME Hyades","M 13","NAME Crab Nebula","NAME Orion Nebula","* eta Car","NAME Laniakea Supercluster","NAME Virgo Cluster","NAME Coma Cluster","NAME Perseus Cluster","NAME Shapley Supercluster","NAME Great Attractor","NAME Fornax Cluster","NAME Norma Cluster","NAME Sloan Great Wall","NAME Local Void"]
lst=",".join("'"+n.replace("'","''")+"'" for n in names)
rows=q(f"SELECT id, main_id, otype, ra, dec, rvz_redshift, plx_value FROM basic JOIN ident ON oidref=oid WHERE id IN ({lst})")
for r in rows: print(r)
json.dump(rows, open('simbad_extra.json','w'), indent=1)
rows=q(f"SELECT id, dist, unit, method, bibcode FROM mesDistance JOIN ident ON mesDistance.oidref=ident.oidref WHERE id IN ({lst})")
for r in rows: print(r)
