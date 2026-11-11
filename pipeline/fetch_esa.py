# Gaia DR3 par l'archive de l'ESA (tâches asynchrones). Si la réponse est tronquée à 50 000 lignes, on découpe par tranches de magnitude.
import requests, os, time, threading, io, sys
UA={'User-Agent':'UniversArtifactBuilder/1.4 (educational visualization)'}; os.makedirs('raw/esa',exist_ok=True); LOCK=threading.Lock()
def log(*a):
    with LOCK: open('raw/esa.log','a').write(' '.join(str(x) for x in a)+'\n')
Q="SELECT TOP 3000000 ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp FROM gaiadr3.gaia_source WHERE phot_g_mean_mag >= %.4f AND phot_g_mean_mag < %.4f AND parallax_over_error > 5 AND parallax > 0.2"
def job(a,b,depth=0):
    out='raw/esa/g_%.4f_%.4f.csv'%(a,b)
    if os.path.exists(out): return
    for attempt in range(3):
        try:
            r=requests.post('https://gea.esac.esa.int/tap-server/tap/async',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','PHASE':'RUN','MAXREC':'3000000','QUERY':Q%(a,b)},headers=UA,timeout=(20,120),allow_redirects=False)
            url=r.headers.get('Location'); ph=''
            if not url: log('pas de tâche',a,b,r.status_code,r.text[:100].replace('\n',' ')); time.sleep(8); continue
            t=time.time()
            while time.time()-t<600:
                ph=requests.get(url+'/phase',headers=UA,timeout=60).text.strip()
                if ph in ('COMPLETED','ERROR','ABORTED'): break
                time.sleep(3)
            if ph!='COMPLETED': log('phase',ph,a,b); time.sleep(5); continue
            d=requests.get(url+'/results/result',headers=UA,timeout=(20,900)).content; n=d.count(b'\n')-1
            if n>=50000 and n%50000==0 and depth<5:
                log('tronqué',n,a,b,'-> découpe'); m=(a+b)/2; job(a,m,depth+1); job(m,b,depth+1); return
            open(out,'wb').write(d); log('OK',a,b,n,'lignes'); return
        except Exception as e: log('ERR',a,b,str(e)[:120]); time.sleep(6)
# tranches : largeur adaptée à la densité attendue (environ 40 000 étoiles par tranche)
bins=[]; g=9.52
while g<11.65-1e-9:
    dens=1.01*358000*2.75**(g-9.8)*0.9; w=min(0.1,40000/dens); b=min(11.65,g+w); bins.append((g,b)); g=b
log('tranches',len(bins))
import queue; qu=queue.Queue(); [qu.put(x) for x in bins]
def worker():
    while True:
        try: a,b=qu.get_nowait()
        except Exception: return
        job(a,b)
th=[threading.Thread(target=worker,daemon=True) for _ in range(8)]; [t.start() for t in th]; [t.join() for t in th]; log('FIN')
