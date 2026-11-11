import requests, os, time, threading, queue, sys, json, urllib.parse
UA={'User-Agent':'UniversArtifactBuilder/1.7 (educational visualization)'}; os.makedirs('raw/esa3',exist_ok=True); LOCK=threading.Lock(); T0=time.time(); LIMIT=250; LOG={}
def log(k,v):
    with LOCK: LOG[k]=v
Q="SELECT TOP 3000000 ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaiadr3.gaia_source WHERE phot_g_mean_mag >= %.4f AND phot_g_mean_mag < %.4f AND parallax_over_error > 5 AND parallax > 0.2"
def job(a,b,depth=0):
    out='raw/esa3/g_%.4f_%.4f.csv'%(a,b)
    if os.path.exists(out) or time.time()-T0>LIMIT-45: return
    for attempt in range(2):
        try:
            r=requests.post('https://gea.esac.esa.int/tap-server/tap/async',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','PHASE':'RUN','MAXREC':'3000000','QUERY':Q%(a,b)},headers=UA,timeout=(20,120),allow_redirects=False)
            url=r.headers.get('Location'); ph=''
            if not url: time.sleep(6); continue
            while time.time()-T0<LIMIT-8:
                ph=requests.get(url+'/phase',headers=UA,timeout=60).text.strip()
                if ph in ('COMPLETED','ERROR','ABORTED'): break
                time.sleep(3)
            if ph!='COMPLETED': return
            d=requests.get(url+'/results/result',headers=UA,timeout=(20,200)).content; n=d.count(b'\n')-1
            if n>=50000 and n%50000==0 and depth<5: m=(a+b)/2; job(a,m,depth+1); job(m,b,depth+1); return
            open(out,'wb').write(d); return
        except Exception as e: time.sleep(4)
bins=[]; g=12.4
while g<12.8-1e-9:
    dens=1.01*358000*2.75**(g-9.8)*0.9; w=min(0.1,38000/dens); b=min(12.8,g+w); bins.append((g,b)); g=b
qu=queue.Queue(); [qu.put(x) for x in bins]
def worker():
    while True:
        try: a,b=qu.get_nowait()
        except Exception: return
        job(a,b)
def desi():
    out='raw/desi_big2.csv'
    if os.path.exists(out): return
    try:
        r=requests.post('https://datalab.noirlab.edu/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':"SELECT mean_fiber_ra,mean_fiber_dec,z,spectype FROM desi_dr1.zpix WHERE random_id>=13 AND random_id<27.5 AND zwarn=0 AND z>0.002 AND z<5.5 AND spectype<>'STAR' AND zcat_primary='t'"},headers=UA,timeout=(30,240),stream=True)
        if r.status_code!=200: log('desi',('HTTP',r.status_code)); return
        n=0
        with open(out+'.part','wb') as f:
            for c in r.iter_content(1<<18):
                f.write(c); n+=len(c)
                if time.time()-T0>LIMIT-5: raise TimeoutError('trop long')
        os.replace(out+'.part',out); log('desi',('OK',n))
    except Exception as e: log('desi',('ERR',str(e)[:100]))
def sbdb():
    out='raw/sbdb_ast_big.json'
    if os.path.exists(out): return
    try:
        u='https://ssd-api.jpl.nasa.gov/sbdb_query.api?'+urllib.parse.urlencode({'fields':'pdes,name,a,e,i,om,w,ma,H,epoch,class','sb-kind':'a','sb-cdata':json.dumps({'AND':['H|LT|14.6','a|LT|8']})})
        r=requests.get(u,headers=UA,timeout=(20,230)); open(out,'wb').write(r.content); log('sbdb',(r.status_code,len(r.content)))
    except Exception as e: log('sbdb',('ERR',str(e)[:100]))
JD0=2461355.5; HZ={}
def hz(name,cmd,cen,kind):
    for attempt in range(3):
        try:
            p={'format':'text','COMMAND':"'%s'"%cmd,'OBJ_DATA':'NO','MAKE_EPHEM':'YES','CENTER':"'%s'"%cen,'REF_PLANE':'ECLIPTIC','CSV_FORMAT':'YES','OUT_UNITS':"'KM-D'"}
            if kind=='moon':
                p1=dict(p); p1.update({'EPHEM_TYPE':'ELEMENTS','TLIST':"'%.1f'"%JD0}); row=requests.get('https://ssd.jpl.nasa.gov/api/horizons.api',params=p1,headers=UA,timeout=90).text.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n')[0].split(',')
                e={'ec':float(row[2]),'qr':float(row[3]),'inc':float(row[4]),'om':float(row[5]),'w':float(row[6]),'n':float(row[8]),'ma':float(row[9]),'a':float(row[11]),'pr':float(row[13])}
                p2=dict(p); p2.update({'EPHEM_TYPE':'VECTORS','TLIST':"'%.1f,%.1f,%.1f'"%(JD0+5,JD0+30,JD0+365),'VEC_TABLE':'1'})
                vs=[[float(x) for x in l.split(',')[2:5]] for l in requests.get('https://ssd.jpl.nasa.gov/api/horizons.api',params=p2,headers=UA,timeout=90).text.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n') if l.strip()]
                with LOCK: HZ[name]={'kind':'moon','cen':cen,'el':e,'chk':vs}
            else:
                p2=dict(p); p2.update({'EPHEM_TYPE':'VECTORS','TLIST':"'%.1f'"%JD0,'VEC_TABLE':'2','OUT_UNITS':"'AU-D'"})
                row=requests.get('https://ssd.jpl.nasa.gov/api/horizons.api',params=p2,headers=UA,timeout=90).text.split('$$SOE')[1].split('$$EOE')[0].strip().split('\n')[0].split(',')
                with LOCK: HZ[name]={'kind':'craft','p':[float(x) for x in row[2:5]],'v':[float(x) for x in row[5:8]]}
            return
        except Exception as ex:
            time.sleep(5)
    with LOCK: HZ[name]={'err':True}
def horizons():
    L=[('Amalthée','505','500@599','moon'),('Himalia','506','500@599','moon'),('Hypérion','607','500@699','moon'),('Phœbé','609','500@699','moon'),('Puck','715','500@799','moon'),('Néréide','802','500@899','moon'),('Protée','808','500@899','moon'),('Charon','901','500@999','moon'),
       ('Voyager 1','-31','500@10','craft'),('Voyager 2','-32','500@10','craft'),('Pioneer 10','-23','500@10','craft'),('Pioneer 11','-24','500@10','craft'),('New Horizons','-98','500@10','craft')]
    for x in L: hz(*x)
    json.dump({'jd0':JD0,'items':HZ,'order':[x[0] for x in L]},open('raw/horizons2.json','w'),ensure_ascii=False)
def stel():
    for name,url in (('constellationship.fab','https://raw.githubusercontent.com/Stellarium/stellarium/v0.22.2/skycultures/western/constellationship.fab'),('modern_index.json','https://raw.githubusercontent.com/Stellarium/stellarium-skycultures/master/western/index.json'),('modern_index2.json','https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern/index.json')):
        try:
            r=requests.get(url,headers=UA,timeout=40); log(name,(r.status_code,len(r.content)))
            if r.status_code==200 and len(r.content)>2000: open('raw/'+name,'wb').write(r.content)
        except Exception as e: log(name,('ERR',str(e)[:80]))
th=[threading.Thread(target=worker,daemon=True) for _ in range(12)]+[threading.Thread(target=f,daemon=True) for f in (desi,sbdb,horizons,stel)]
[t.start() for t in th]; [t.join(max(1,LIMIT-(time.time()-T0))) for t in th]
print(LOG); print('tranches Gaia :',len(os.listdir('raw/esa3')),'/',len(bins)); print('Horizons :',{k:('ok' if 'err' not in v else 'échec') for k,v in HZ.items()})
