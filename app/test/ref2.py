import json, math
from scipy.integrate import quad
c=299792.458
def run(H0,Om,OL,w):
    Or=4.1837e-5/(H0/100)**2; Ok=1-Om-OL-Or
    E=lambda a: math.sqrt(Or/a**4+Om/a**3+Ok/a**2+OL*a**(-3*(1+w)))
    ph=quad(lambda a: c/(H0*a*a*E(a)), 0, 1, limit=400, epsabs=1e-6)[0]
    eh=quad(lambda a: c/(H0*a*a*E(a)), 1, math.inf, limit=400)[0] if OL>0 and w<=-1 else None
    return dict(H0=H0,Om=Om,OL=OL,w=w,chi_ph=ph,chi_eh=eh)
out=[run(*p) for p in [(67.4,0.315,0.685,-1),(70,0.3,0.7,-1),(67.4,1.0,0.0,-1),(67.4,0.315,0.0,-1),(67.4,0.315,0.685,-0.8),(72,0.25,0.9,-1)]]
json.dump(out, open('ref2.json','w'), indent=1)
for o in out: print(o)
