import requests, os, time, threading, urllib.parse, json
UA={'User-Agent':'UniversArtifactBuilder/1.3 (educational visualization)'}; T0=time.time(); st={}
def save(name,url,method='get',timeout=230,minsize=5000,**kw):
    path='raw/'+name
    if os.path.exists(path) and os.path.getsize(path)>minsize: st[name]=('cache',os.path.getsize(path)); return True
    try:
        r=requests.request(method,url,headers=UA,timeout=(15,timeout),stream=True,**kw)
        if r.status_code!=200: st[name+' '+urllib.parse.urlparse(url).netloc]=('HTTP %d'%r.status_code, r.text[:140].replace('\n',' ')); return False
        n=0
        with open(path+'.part','wb') as f:
            for c in r.iter_content(1<<16):
                f.write(c); n+=len(c)
                if time.time()-T0>265: raise TimeoutError('délai global')
        if n<minsize: st[name+' '+urllib.parse.urlparse(url).netloc]=('trop petit',open(path+'.part',errors='replace').read()[:200].replace('\n',' ')); return False
        os.replace(path+'.part',path); st[name]=('ok',n,urllib.parse.urlparse(url).netloc); return True
    except Exception as e: st[name+' '+urllib.parse.urlparse(url).netloc]=('ERR',str(e)[:140]); return False
Q="SELECT ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaiadr3.gaia_source WHERE phot_g_mean_mag BETWEEN 8.4 AND 9.8 AND parallax_over_error > 6 AND parallax > 0.3"
def gaia():
    # 1) ARI Heidelberg  2) NOIRLab Data Lab  3) ESA (asynchrone)
    if save('gaia_bright.csv','https://gaia.ari.uni-heidelberg.de/tap/sync',method='post',minsize=2000000,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','MAXREC':'700000','QUERY':Q}): return
    if save('gaia_bright.csv','https://datalab.noirlab.edu/tap/sync',method='post',minsize=2000000,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':Q.replace('gaiadr3.gaia_source','gaia_dr3.gaia_source')}): return
    try:
        r=requests.post('https://gea.esac.esa.int/tap-server/tap/async',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','PHASE':'RUN','QUERY':Q},headers=UA,timeout=(15,60),allow_redirects=False)
        job=r.headers.get('Location'); st['gaia esa job']=(r.status_code,job)
        while job and time.time()-T0<230:
            ph=requests.get(job+'/phase',headers=UA,timeout=30).text.strip()
            if ph in ('COMPLETED','ERROR','ABORTED'): st['gaia esa phase']=ph; break
            time.sleep(5)
        if job and ph=='COMPLETED': save('gaia_bright.csv',job+'/results/result',minsize=2000000)
    except Exception as e: st['gaia esa']=('ERR',str(e)[:140])
def sbdb():
    save('sbdb_com.json','https://ssd-api.jpl.nasa.gov/sbdb_query.api?'+urllib.parse.urlencode({'fields':'pdes,name,e,q,i,om,w,tp,epoch,M1,class','sb-kind':'c','full-prec':'true','sb-cdata':json.dumps({'AND':['e|LT|0.9996']})}),timeout=120)
def exo():
    save('exo.csv','https://exoplanetarchive.ipac.caltech.edu/TAP/sync?'+urllib.parse.urlencode({'query':'select hostname,ra,dec,sy_dist,sy_pnum,sy_vmag,st_teff from pscomppars','format':'csv'}),timeout=150,minsize=50000)
def psr():
    for host in ('vizier.cds.unistra.fr','vizier.cfa.harvard.edu'):
        if save('psr.tsv',f'https://{host}/viz-bin/asu-tsv?-source=B/psr/psr&-out.max=unlimited&-out=PSRJ,Dist,P0,Age&-out.add=_RAJ,_DEJ',timeout=120,minsize=30000): return
th=[threading.Thread(target=f,daemon=True) for f in (gaia,sbdb,exo,psr)]
[t.start() for t in th]; [t.join(max(1,270-(time.time()-T0))) for t in th]
for k in sorted(st): print('%-28s %s'%(k,st[k]))
def head(name,n=2,skip='#'):
    p='raw/'+name
    if os.path.exists(p):
        L=[l.rstrip('\n') for l in open(p,errors='replace') if not l.startswith(skip) and l.strip()]
        print('---',name,len(L),'lignes |',' || '.join(l[:150] for l in L[:1]+L[3:3+n]))
for n in ('gaia_bright.csv','exo.csv','psr.tsv'): head(n)
p='raw/sbdb_com.json'
if os.path.exists(p):
    d=json.load(open(p)); print('--- comètes',d.get('count'),d.get('fields'),d['data'][0] if d.get('data') else d)
