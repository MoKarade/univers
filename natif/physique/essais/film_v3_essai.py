# Petit film version 3 pour essai_film_v3 : 400 traceurs P et 150 étoiles Gaia (famille G) sur des orbites connues autour de deux galaxies, écrit par
# l'écrivain du fil du calcul (pipeline/fusion/film_v3.py), avec ce que son lecteur Python en tire (reference.txt, reference_g.txt, nature.txt).
# Usage : python3 film_v3_essai.py <dossier vide>. Le résultat est rangé dans film_v3_essai/ (environ 300 ko).
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'pipeline', 'fusion'))      # film_v3.py (branche film-3)
import film_v3 as F
out = sys.argv[1]
K = 1.0227121650456
rng = np.random.default_rng(1)
N0, N1, NG = 300, 100, 150            # traceurs autour de la galaxie 0 et de la galaxie 1, puis étoiles Gaia (famille G, Voie lactée)
N = N0 + N1 + NG
gal = np.r_[np.zeros(N0, int), np.ones(N1, int), np.zeros(NG, int)]
R = np.r_[rng.uniform(0.3, 15, N0), rng.uniform(0.3, 8, N1), rng.uniform(5, 11, NG)]
vc = 220.0
om = vc / R * K                        # rad/Ga
ph = rng.uniform(0, 2 * np.pi, N); zA = rng.uniform(-0.3, 0.3, N); nu = 2 * om
def centre(t):                          # galaxie 1 : mouvement lent et courbe, en kpc ; galaxie 0 fixe à 0 ... + petit bruit
    c = np.zeros((2, 3)); v = np.zeros((2, 3))
    c[1] = [700 - 100 * t, 300 * np.sin(0.8 * t), 50 * t * t]; v[1] = np.array([-100, 240 * np.cos(0.8 * t), 100 * t]) / K
    return c, v
def etat(t):
    a = ph + om * t
    p = np.c_[R * np.cos(a), R * np.sin(a), zA * np.sin(nu * t)]
    v = np.c_[-R * om * np.sin(a), R * om * np.cos(a), zA * nu * np.cos(nu * t)] / K
    c, cv = centre(t)
    return p + c[gal], v + cv[gal]
NP = N0 + N1
ordre = np.argsort(-om[:NP])
C, M, L = np.sort(ordre[:30]), np.sort(ordre[30:70]), np.sort(ordre[70:120])
P = np.arange(NP)
GR = np.arange(NP, N)
NN = 3                                  # galaxies naines : 3 points de la galaxie 0, juste avant le Soleil
blocs = [dict(famille=0, type=1, galaxie=0, premier=0, nombre=N0 - 1 - NN), dict(famille=0, type=F.TYPE_NAINE, galaxie=0, premier=N0 - 1 - NN, nombre=NN),
         dict(famille=0, type=3, galaxie=0, premier=N0 - 1, nombre=1),
         dict(famille=0, type=1, galaxie=1, premier=N0, nombre=N1)]
rangs = {F.FAM_P: P, F.FAM_C: C, F.FAM_M: M, F.FAM_L: L, F.FAM_G: GR}
orig = {f: gal[np.asarray(r, int)] for f, r in rangs.items()}
for nom, cl in (('centraux.bin', C), ('moyens.bin', M), ('lents.bin', L)): cl.astype('<u4').tofile(os.path.join(out, nom))
blocs += [dict(famille=f, type=0, galaxie=None, premier=0, nombre=len(r)) for f, r in ((F.FAM_C, C), (F.FAM_M, M), (F.FAM_L, L))]
blocs += [dict(famille=F.FAM_G, type=F.TYPE_GAIA, galaxie=0, premier=0, nombre=NG)]
import zlib
appli = rng.integers(0, 256, 5000, dtype=np.uint8).tobytes()      # un faux gaia.bin de l'appli, pour la taille et le CRC32
open(os.path.join(out, 'gaia_appli.bin'), 'wb').write(appli)
rng.permutation(10000)[:NG].astype('<u4').tofile(os.path.join(out, 'gaia.bin'))
E = F.Ecrivain(out, ['Voie lactée', 'Andromède'], rangs, orig, blocs, infos=dict(naines=dict(nombre=NN, noms=['Sagittaire', 'Nuage "essai" \\ 2', 'Dragon 😀'], source='essai'), gaia=dict(taille=len(appli), crc32=zlib.crc32(appli)), decalage_a_t0={'Andromède': dict(position=[1, 2, 3], vitesse=[4, 5, 6])}))
NM = 12
m = np.zeros(NM, F.DT_MATIERE); m['nature'] = (np.arange(NM) % 3 != 0); m['sorte'] = np.where(m['nature'], 1, F.SORTE_GAZ); m['galaxie'] = np.arange(NM) % 2; m['masse'] = 1e5
F.ecrire_fichier(os.path.join(out, 'matiere.bin'), m)
E.nature = m['nature'].copy()
def sortes(k):
    s = m['sorte'].copy()
    s[(np.arange(NM) * 7 + k) % 11 == 0] = F.SORTE_GAZ; s[(np.arange(NM) * 5 + k) % 13 == 0] = 1
    return s
for k in range(0, 51):                  # 0 à 100 Ma, tous les 2 Ma
    t = k * 0.002; p, v = etat(t); c, cv = centre(t)
    E.date(t, lambda r: p[np.asarray(r)], lambda r: v[np.asarray(r)], c, cv, energie=1e-6 * k, sortes_matiere=sortes(k))
E.sauver()
# Référence : lecteur Python du fil du calcul + Hermite (traceur et centre), et la vérité analytique
f = F.Film(out)
cls = np.zeros(NP, int); cls[C] = 1; cls[M] = 3; cls[L] = 4
bits = {0: 1, 1: 3, 3: 9, 4: 17}
ts = np.array([0.0, 0.0071, 0.0200, 0.0333, 0.0811, 0.1])
nat = {}
for t in ts:
    k = int(np.floor(t / 0.002 + 1e-9)); nat[t] = (sortes(k) != F.SORTE_GAZ).astype(int) 
with open(os.path.join(out, 'nature.txt'), 'w') as h:
    for t in ts: h.write('%.10g ' % t + ' '.join(map(str, nat[t])) + '\n')
ref = []
for t in ts:
    tdt = np.array([d['t'] for d in f.dates])
    def enc(b):
        ks = [k for k, d in enumerate(f.dates) if d['familles'] & b]
        tk = tdt[ks]; j = np.searchsorted(tk, t, 'right') - 1; j = min(max(j, 0), len(ks) - 2)
        return ks[j], ks[j + 1]
    kc = min(max(np.searchsorted(tdt, t, 'right') - 1, 0), len(tdt) - 2)
    uc = (t - tdt[kc]) / (tdt[kc + 1] - tdt[kc])
    cen = np.array([F.hermite(np.array(f.dates[kc]['centres'][g]), np.array(f.dates[kc]['vitesses'][g]),
                              np.array(f.dates[kc + 1]['centres'][g]), np.array(f.dates[kc + 1]['vitesses'][g]), tdt[kc + 1] - tdt[kc], uc) for g in range(2)])
    truth, _ = etat(t)
    for i in range(NP):
        a, b = enc(bits[cls[i]])
        def lit(k):
            if f.dates[k]['familles'] & 1: pp, vv = f.image(k, 'p'); return pp[i], vv[i]
            lettre = {1: 'c', 3: 'm', 4: 'l'}[cls[i]]; arr = {1: C, 3: M, 4: L}[cls[i]]; j = np.searchsorted(arr, i)
            pp, vv = f.image(k, lettre); return pp[j], vv[j]
        pa, va = lit(a); pb, vb = lit(b)
        u = (t - tdt[a]) / (tdt[b] - tdt[a])
        x = F.hermite(pa, va, pb, vb, tdt[b] - tdt[a], u) + cen[gal[i]]
        ref.append([t, i, *x, *truth[i]])
np.savetxt(os.path.join(out, 'reference.txt'), np.array(ref), fmt='%.9g')
# Famille G : ses dates (bit 2), centre de la Voie lactée (nul), même Hermite
refg = []
kg = [k for k, d in enumerate(f.dates) if d['familles'] & 4]; tg = tdt[kg]
for t in ts:
    j = min(max(np.searchsorted(tg, t, 'right') - 1, 0), len(kg) - 2); a, b = kg[j], kg[j + 1]
    pa, va = f.image(a, 'g'); pb, vb = f.image(b, 'g'); u = (t - tdt[a]) / (tdt[b] - tdt[a])
    x = F.hermite(pa, va, pb, vb, tdt[b] - tdt[a], u); truth, _ = etat(t)
    for s_ in range(NG): refg.append([t, s_, *x[s_], *truth[NP + s_]])
np.savetxt(os.path.join(out, 'reference_g.txt'), np.array(refg), fmt='%.9g')
open(os.path.join(out, 'naines_attendues.txt'), 'w', encoding='utf-8', newline='\n').write(''.join(n + '\n' for n in f.meta['naines']['noms']))
print('film', len(f.dates), 'dates ; référence', len(ref), 'lignes')
