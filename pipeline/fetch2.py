import requests, os, time, threading, subprocess, urllib.parse
UA={'User-Agent':'UniversArtifactBuilder/1.1 (educational visualization)'}; T0=time.time(); st={}
def save(name,url,method='get',timeout=200,minsize=2000,**kw):
    path='raw/'+name
    if os.path.exists(path) and os.path.getsize(path)>minsize: st[name]=('cache',os.path.getsize(path)); return True
    try:
        r=requests.request(method,url,headers=UA,timeout=(15,timeout),stream=True,**kw)
        if r.status_code!=200: st[name]=('HTTP %d'%r.status_code, r.text[:140].replace('\n',' ')); return False
        n=0
        with open(path+'.part','wb') as f:
            for c in r.iter_content(1<<16):
                f.write(c); n+=len(c)
                if time.time()-T0>262: raise TimeoutError('délai global')
        if n<minsize: st[name]=('trop petit',open(path+'.part',errors='replace').read()[:200].replace('\n',' ')); return False
        os.replace(path+'.part',path); st[name]=('ok',n); return True
    except Exception as e: st[name]=('ERR',str(e)[:140]); return False
def viz(name,source,cols):
    for host in ('vizier.cds.unistra.fr','vizier.cfa.harvard.edu'):
        if save(name,f'https://{host}/viz-bin/asu-tsv?-source={urllib.parse.quote(source,safe="/")}&-out.max=unlimited&-out={urllib.parse.quote(cols,safe=",")}',timeout=220,minsize=200000): return
def tap(name,q,timeout=235):
    save(name,'https://datalab.noirlab.edu/tap/sync',method='post',timeout=timeout,minsize=20000,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q})
def schema():
    try:
        r=requests.post('https://datalab.noirlab.edu/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':"SELECT column_name FROM tap_schema.columns WHERE table_name='sdss_dr17.specobj'"},headers=UA,timeout=(15,60))
        cols=[c.strip().strip('"') for c in r.text.splitlines()[1:]]; st['sdss_schema']=(r.status_code,len(cols),[c for c in cols if c in ('ra','dec','z','zwarning','class','random_id','plug_ra','plug_dec','specobjid','sciprimary','sciencePrimary')])
        if 'z' in cols:
            ra='ra' if 'ra' in cols else 'plug_ra'; de='dec' if 'dec' in cols else 'plug_dec'
            w=["zwarning=0","z>0.003","z<6","class<>'STAR'"]+(['random_id<7'] if 'random_id' in cols else [])
            tap('dl_sdss.csv',f"SELECT {ra},{de},z,class FROM sdss_dr17.specobj WHERE "+' AND '.join(w))
    except Exception as e: st['sdss_schema']=('ERR',str(e)[:140])
jobs=[(schema,()),
 (tap,('dl_desi.csv',"SELECT mean_fiber_ra,mean_fiber_dec,z,spectype FROM desi_dr1.zpix WHERE random_id<0.45 AND zwarn=0 AND z>0.002 AND z<5.5 AND spectype<>'STAR' AND zcat_primary='t'")),
 (viz,('2dfgrs.tsv','VII/250/2dfgrs','RAJ2000,DEJ2000,z,q_z')),
 (viz,('6dfgs.tsv','VII/259/6dfgs','RAJ2000,DEJ2000,cz,q_cz')),
 (viz,('dr16q.tsv','VII/289/dr16q','RAJ2000,DEJ2000,z')),
 (save,('Moon.py','https://raw.githubusercontent.com/architest/pymeeus/master/pymeeus/Moon.py')),
 (save,('moonposition.js','https://raw.githubusercontent.com/commenthol/astronomia/master/src/moonposition.js'))]
for b in ('mer','ven','ear','emb','mar','jup','sat','ura','nep'):
    jobs.append((save,('VSOP87A.'+b,'https://cdsarc.cds.unistra.fr/ftp/VI/81/VSOP87A.'+b)))
pips=[subprocess.Popen(f'timeout 140 pip install {p} --break-system-packages -q 2>&1 | tail -1',shell=True,stdout=subprocess.PIPE,text=True) for p in ('jplephem','astropy-healpix','pymeeus')]
th=[threading.Thread(target=f,args=a,daemon=True) for f,a in jobs]
[t.start() for t in th]; [t.join(max(1,268-(time.time()-T0))) for t in th]
for k in sorted(st): print('%-16s %s'%(k,st[k]))
for p,n in zip(pips,('jplephem','astropy-healpix','pymeeus')): print('pip',n,'->',(p.stdout.read().strip()[:120] if p.poll() is not None else 'en cours'))
def head(name,n=2):
    p='raw/'+name
    if os.path.exists(p):
        L=[l.rstrip('\n') for l in open(p,errors='replace') if not l.startswith('#') and l.strip()]
        print('---',name,len(L),'lignes |',' || '.join(l[:110] for l in L[:1]+L[3:3+n]))
for n in ('dl_sdss.csv','dl_desi.csv','2dfgrs.tsv','6dfgs.tsv','dr16q.tsv'): head(n)
for n in ('VSOP87A.ear','Moon.py'):
    p='raw/'+n
    if os.path.exists(p): L=open(p,errors='replace').read().split('\n'); print('---',n,len(L)); [print('   ',l[:170]) for l in L[:3]]
