import requests, os, time, sys
UA={'User-Agent':'UniversArtifactBuilder/1.3 (educational visualization)'}
Q="SELECT ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaiadr3.gaia_source WHERE phot_g_mean_mag BETWEEN 8.4 AND 9.8 AND parallax_over_error > 6 AND parallax > 0.3"
def log(*a):
    open('raw/gaia.log','a').write(' '.join(str(x) for x in a)+'\n')
def grab(url, out, **kw):
    t=time.time()
    try:
        r=requests.request(kw.pop('method','get'),url,headers=UA,timeout=(20,900),stream=True,**kw)
        if r.status_code!=200: log('HTTP',r.status_code,url,r.text[:200].replace('\n',' ')); return False
        n=0
        with open(out+'.part','wb') as f:
            for c in r.iter_content(1<<16): f.write(c); n+=len(c)
        log('reçu',n,'octets en %.0f s'%(time.time()-t),url)
        if n<2000000: log('trop petit:',open(out+'.part',errors='replace').read()[:300].replace('\n',' ')); return False
        os.replace(out+'.part',out); return True
    except Exception as e: log('ERR',url,str(e)[:200]); return False
which=sys.argv[1]; out='raw/gaia_%s.csv'%which
if which=='ari': ok=grab('https://gaia.ari.uni-heidelberg.de/tap/sync',out,method='post',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','MAXREC':'700000','QUERY':Q})
elif which=='noirlab': ok=grab('https://datalab.noirlab.edu/tap/sync',out,method='post',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':Q.replace('gaiadr3.gaia_source','gaia_dr3.gaia_source')})
elif which=='vizier': ok=grab('https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync',out,method='post',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','MAXREC':'700000','QUERY':'SELECT RA_ICRS,DE_ICRS,Plx,pmRA,pmDE,RV,Gmag,"BP-RP" FROM "I/355/gaiadr3" WHERE Gmag BETWEEN 8.4 AND 9.8 AND RPlx > 6 AND Plx > 0.3'})
else:
    ok=False
    try:
        r=requests.post('https://gea.esac.esa.int/tap-server/tap/async',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','PHASE':'RUN','QUERY':Q},headers=UA,timeout=(20,120),allow_redirects=False)
        job=r.headers.get('Location'); log('esa job',r.status_code,job)
        ph=''
        while job:
            ph=requests.get(job+'/phase',headers=UA,timeout=60).text.strip()
            if ph in ('COMPLETED','ERROR','ABORTED'): break
            time.sleep(6)
        log('esa phase',ph)
        if ph=='COMPLETED': ok=grab(job+'/results/result',out)
    except Exception as e: log('ERR esa',str(e)[:200])
log('FIN',which,ok)
