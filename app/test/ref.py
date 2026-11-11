import json, math, numpy as np
from astropy.time import Time
from astropy.coordinates import get_body_barycentric, solar_system_ephemeris, get_body, GCRS, CartesianRepresentation
from astropy.cosmology import FlatLambdaCDM, LambdaCDM, wCDM
import astropy.units as u
EPS = math.radians(84381.448/3600)
def eq2ecl(v):
    x,y,z=v; c,s=math.cos(EPS),math.sin(EPS); return [x, c*y+s*z, -s*y+c*z]
out={'planets':[], 'cosmo':[]}
dates=['1850-03-01T00:00:00','1969-07-20T20:17:00','2000-01-01T12:00:00','2026-11-09T22:00:00','2045-06-15T06:00:00']
with solar_system_ephemeris.set('builtin'):
    for d in dates:
        t=Time(d, scale='tdb')
        sun=get_body_barycentric('sun', t).xyz.to_value(u.au)
        rec={'date':d,'jd':t.jd,'bodies':{}}
        for b in ['mercury','venus','earth','moon','mars','jupiter','saturn','uranus','neptune','earth-moon-barycenter']:
            p=get_body_barycentric(b, t).xyz.to_value(u.au)-sun
            rec['bodies'][b]=eq2ecl(p)
        out['planets'].append(rec)
# cosmologie : mêmes hypothèses que l'appli (rayonnement = photons + 3,046 neutrinos sans masse)
def cos(H0,Om,OL,w=-1):
    kw=dict(H0=H0, Om0=Om, Tcmb0=2.7255, Neff=3.046, m_nu=0*u.eV)
    if w==-1: return LambdaCDM(Ode0=OL, **kw)
    return wCDM(Ode0=OL, w0=w, **kw)
for (H0,Om,OL,w) in [(67.4,0.315,0.685,-1),(70,0.3,0.7,-1),(67.4,1.0,0.0,-1),(67.4,0.315,0.0,-1),(67.4,0.315,0.685,-0.8),(72,0.25,0.9,-1)]:
    c=cos(H0,Om,OL,w)
    rec=dict(H0=H0,Om=Om,OL=OL,w=w, age=float(c.age(0).to_value(u.Gyr)), Or=float(c.Ogamma0+c.Onu0), Ok=float(c.Ok0),
             chi_z1100=float(c.comoving_distance(1100).to_value(u.Mpc)), chi_z1=float(c.comoving_distance(1).to_value(u.Mpc)),
             lookback_z1=float(c.lookback_time(1).to_value(u.Gyr)), lookback_z5=float(c.lookback_time(5).to_value(u.Gyr)),
             H_z1=float(c.H(1).value))
    # horizon des particules : intégrale de c dz/H jusqu'à z très grand
    rec['chi_ph']=float(c.comoving_distance(1e9).to_value(u.Mpc))
    out['cosmo'].append(rec)
json.dump(out, open('ref.json','w'), indent=1)
print('ok', len(out['planets']), len(out['cosmo']))
for r in out['cosmo']: print(r)
