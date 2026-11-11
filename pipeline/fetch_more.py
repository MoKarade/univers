import requests, os, time, threading, queue, sys, urllib.parse
UA={'User-Agent':'UniversArtifactBuilder/1.5 (educational visualization)'}; os.makedirs('raw/esa2',exist_ok=True); os.makedirs('raw/sky',exist_ok=True); LOCK=threading.Lock(); T0=time.time(); LIMIT=float(sys.argv[1]) if len(sys.argv)>1 else 255
def log(*a):
    with LOCK: open('raw/more.log','a').write(' '.join(str(x) for x in a)+'\n')
Q="SELECT TOP 3000000 ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaiadr3.gaia_source WHERE phot_g_mean_mag >= %.4f AND phot_g_mean_mag < %.4f AND parallax_over_error > 5 AND parallax > 0.2"
def job(a,b,depth=0):
    out='raw/esa2/g_%.4f_%.4f.csv'%(a,b)
    if os.path.exists(out) or time.time()-T0>LIMIT-50: return
    for attempt in range(2):
        try:
            r=requests.post('https://gea.esac.esa.int/tap-server/tap/async',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','PHASE':'RUN','MAXREC':'3000000','QUERY':Q%(a,b)},headers=UA,timeout=(20,120),allow_redirects=False)
            url=r.headers.get('Location'); ph=''
            if not url: log('pas de tâche',a,b,r.status_code); time.sleep(6); continue
            while time.time()-T0<LIMIT-8:
                ph=requests.get(url+'/phase',headers=UA,timeout=60).text.strip()
                if ph in ('COMPLETED','ERROR','ABORTED'): break
                time.sleep(3)
            if ph!='COMPLETED': log('phase',ph,a,b); return
            d=requests.get(url+'/results/result',headers=UA,timeout=(20,200)).content; n=d.count(b'\n')-1
            if n>=50000 and n%50000==0 and depth<5: m=(a+b)/2; job(a,m,depth+1); job(m,b,depth+1); return
            open(out,'wb').write(d); return
        except Exception as e: log('ERR',a,b,str(e)[:100]); time.sleep(4)
bins=[]; g=11.65
while g<12.4-1e-9:
    dens=1.01*358000*2.75**(g-9.8)*0.9; w=min(0.1,38000/dens); b=min(12.4,g+w); bins.append((g,b)); g=b
qu=queue.Queue(); [qu.put(x) for x in bins]
def worker():
    while True:
        try: a,b=qu.get_nowait()
        except Exception: return
        job(a,b)
def sky(k):
    out='raw/sky/gal_%d.csv'%k
    if os.path.exists(out): return
    sql="SELECT ra,dec,z FROM SpecObj WHERE class='GALAXY' AND zWarning=0 AND z>0.003 AND z<1.3 AND fiberID%%8=%d"%k
    for base in ('https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch','https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch'):
        try:
            r=requests.get(base,params={'cmd':sql,'format':'csv'},headers=UA,timeout=(20,200))
            if r.status_code==200 and r.content.count(b'\n')>1000: open(out,'wb').write(r.content); log('sky',k,r.content.count(b'\n'),'lignes'); return
            log('sky',k,'HTTP',r.status_code,r.text[:120].replace('\n',' '))
        except Exception as e: log('sky ERR',k,str(e)[:100])
def viz(name,src,extra=''):
    for host in ('vizier.cfa.harvard.edu','vizier.cds.unistra.fr'):
        try:
            r=requests.get(f'https://{host}/viz-bin/asu-tsv?-source={src}&-out.max=unlimited&-out.all&-out.add=_RAJ,_DEJ{extra}',headers=UA,timeout=(15,90))
            if r.status_code==200 and len(r.content)>3000: open('raw/'+name,'wb').write(r.content); log('viz',name,len(r.content),host); return
            log('viz',name,'HTTP',r.status_code,len(r.content),host)
        except Exception as e: log('viz ERR',name,str(e)[:100])
def simbad():
    names=['Cyg X-1','V404 Cyg','V616 Mon','GRO J1655-40','GRS 1915+105','NAME Gaia BH1','NAME Gaia BH2','NAME Gaia BH3','M 87','M 31','M 104','NGC 4258','TON 618','NAME Sgr A*','M 33 X-7','LMC X-1','LMC X-3','NGC 1277','M 81','NAME Cen A','3C 273','M 32','Holmberg 15A','NGC 4889']
    try:
        q="SELECT id, ra, dec, plx_value, rvz_redshift, rvz_radvel FROM basic JOIN ident ON oidref=oid WHERE id IN (%s)"%','.join("'%s'"%n.replace("'","''") for n in names)
        r=requests.post('https://simbad.harvard.edu/simbad/sim-tap/sync',data={'request':'doQuery','lang':'adql','format':'csv','query':q},headers=UA,timeout=60); open('raw/bh_simbad.csv','w').write(r.text); log('simbad',r.text.count('\n')-1,'objets')
    except Exception as e: log('simbad ERR',str(e)[:100])
th=[threading.Thread(target=worker,daemon=True) for _ in range(12)]+[threading.Thread(target=sky,args=(k,),daemon=True) for k in range(8)]+[threading.Thread(target=viz,args=('blackcat.tsv','J/A+A/587/A61'),daemon=True),threading.Thread(target=viz,args=('smbh.tsv','J/ApJ/831/134'),daemon=True),threading.Thread(target=simbad,daemon=True)]
[t.start() for t in th]; [t.join(max(1,LIMIT-(time.time()-T0))) for t in th]; log('FIN partielle : tranches Gaia',len(os.listdir('raw/esa2')),'/',len(bins))
