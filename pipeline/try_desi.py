import requests, time, os
t=time.time(); out='raw/desi_big.csv'
try:
    r=requests.post('https://datalab.noirlab.edu/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':"SELECT mean_fiber_ra,mean_fiber_dec,z,spectype FROM desi_dr1.zpix WHERE random_id>=0.45 AND random_id<13 AND zwarn=0 AND z>0.002 AND z<5.5 AND spectype<>'STAR' AND zcat_primary='t'"},headers={'User-Agent':'UniversArtifactBuilder/1.5'},timeout=(30,230),stream=True)
    if r.status_code!=200: print('DESI HTTP',r.status_code,r.text[:100].replace('\n',' '))
    else:
        n=0
        with open(out+'.part','wb') as f:
            for c in r.iter_content(1<<18):
                f.write(c); n+=len(c)
                if time.time()-t>225: raise TimeoutError('trop long, %d octets reçus'%n)
        os.replace(out+'.part',out); print('DESI OK',n,'octets en %.0f s'%(time.time()-t))
except Exception as e: print('DESI ERR',str(e)[:150])
