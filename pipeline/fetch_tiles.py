import requests, os, time, sys
UA={'User-Agent':'UniversArtifactBuilder/1.4 (educational visualization)'}
name, q = sys.argv[1], sys.argv[2]; out='raw/%s.csv'%name; t=time.time()
def log(*a): open('raw/tiles.log','a').write(name+' | '+' '.join(str(x) for x in a)+'\n')
try:
    r=requests.post('https://datalab.noirlab.edu/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q},headers=UA,timeout=(30,1500),stream=True)
    if r.status_code!=200: log('HTTP',r.status_code,r.text[:300].replace('\n',' ')); sys.exit()
    n=0
    with open(out+'.part','wb') as f:
        for c in r.iter_content(1<<18): f.write(c); n+=len(c)
    os.replace(out+'.part',out); log('OK',n,'octets en %.0f s'%(time.time()-t))
except Exception as e: log('ERR',str(e)[:200])
