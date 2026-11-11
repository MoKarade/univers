import requests, os, time, sys
UA={'User-Agent':'UniversArtifactBuilder/1.4 (educational visualization)'}
def log(*a): open('raw/tiles.log','a').write(' '.join(str(x) for x in a)+'\n')
G="SELECT ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaia_dr3.gaia_source WHERE parallax_over_error > 5 AND parallax > 0.2 AND phot_g_mean_mag >= %s AND phot_g_mean_mag < %s"
jobs=[('gaia_t1',G%(9.52,10.9)),('gaia_t2',G%(10.9,11.65)),('desi_big',"SELECT mean_fiber_ra,mean_fiber_dec,z,spectype FROM desi_dr1.zpix WHERE random_id>=0.45 AND random_id<14 AND zwarn=0 AND z>0.002 AND z<5.5 AND spectype<>'STAR' AND zcat_primary='t'")]
for name,q in jobs:
    out='raw/%s.csv'%name
    if os.path.exists(out): continue
    for attempt in range(4):
        t=time.time()
        try:
            r=requests.post('https://datalab.noirlab.edu/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q},headers=UA,timeout=(30,1500),stream=True)
            if r.status_code!=200: log(name,'essai',attempt,'HTTP',r.status_code,r.text[:120].replace('\n',' ')); time.sleep(20); continue
            n=0
            with open(out+'.part','wb') as f:
                for c in r.iter_content(1<<18): f.write(c); n+=len(c)
            if n<1000000: log(name,'trop petit',n,open(out+'.part',errors='replace').read()[:200].replace('\n',' ')); time.sleep(20); continue
            os.replace(out+'.part',out); log(name,'OK',n,'octets en %.0f s'%(time.time()-t)); break
        except Exception as e: log(name,'ERR',str(e)[:160]); time.sleep(20)
log('FIN')
