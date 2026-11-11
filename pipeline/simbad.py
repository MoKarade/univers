import requests, sys, json, csv, io
TAP="https://simbad.harvard.edu/simbad/sim-tap/sync"
def q(adql):
    r=requests.post(TAP, data={"request":"doQuery","lang":"adql","format":"csv","query":adql}, timeout=60)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))
if __name__=="__main__":
    names=["M 31","M 33","LMC","SMC","NGC 5128","M 81","M 87","NGC 1399","NGC 4874","NGC 1275","ACO 3627","ACO 3558","M 51","M 101","NGC 253","M 104","M 83","IC 342","NAME Sgr A*","NAME Sgr dSph","NAME Fornax Dwarf Spheroidal","NAME Sculptor Dwarf Galaxy","NAME Draco Dwarf Galaxy","NAME UMi Galaxy","NAME Carina dSph","NAME Sextans Dwarf Galaxy","NAME Leo I","NAME Leo II","NGC 6822","IC 10","M 32","M 110","IC 1613","NAME WLM Galaxy","NGC 185","NGC 147","NAME Leo A","NGC 3109","NAME Phoenix Dwarf","NAME Bootes Void","ACO 2151","ACO 1367","ACO 1060","NAME Centaurus Cluster","NAME Hercules Cluster","ACO 2199","ACO 2065","NAME Canis Major Overdensity"]
    lst=",".join("'"+n.replace("'","''")+"'" for n in names)
    rows=q(f"SELECT id, main_id, otype, ra, dec, rvz_redshift, galdim_majaxis, galdim_minaxis, galdim_angle FROM basic JOIN ident ON oidref=oid WHERE id IN ({lst})")
    for r in rows: print(r)
    json.dump(rows, open('simbad_gal.json','w'), indent=1)
