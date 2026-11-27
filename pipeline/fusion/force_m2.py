"""Part à deux lobes (m = 2) de l'attraction dans le plan d'une galaxie, par composante. Usage : force_m2.py <fichier.npz> [gid]"""
import sys, numpy as np
z = np.load(sys.argv[1]); g = int(sys.argv[2]) if len(sys.argv) > 2 else 0
pos, m, kind = z['pos'], z['m'], z['kind']; gid = z['gid'] if 'gid' in z.files else np.zeros(len(m), int)
st = (gid == g) & np.isin(kind, [1, 4]); p = pos[st].astype(float); c = np.median(p, axis=0)
for _ in range(6):
    d = np.linalg.norm(p - c, axis=1); c = p[d < 3].mean(0)
G = 4.30091e-6
comps = {'étoiles': (gid == g) & np.isin(kind, [1, 2, 4, 5]), 'gaz': (gid == g) & (kind == 3), 'halo': (gid == g) & (kind == 0)}
P = {n: (pos[s] - c).astype(np.float32) for n, s in comps.items()}; M = {n: (m[s] * G).astype(np.float32) for n, s in comps.items()}
def acc(x, n):
    d = P[n] - np.asarray(x, np.float32); r2 = (d * d).sum(1) + np.float32(0.01)
    return (M[n][:, None] * d / (r2 ** 1.5)[:, None]).sum(0).astype(float)
az = np.radians(np.arange(0, 360, 15.0))
print(sys.argv[1]); print('   R    F_r moyen | part m=2 de F_r (% du total) : étoiles  gaz   halo   tout (angle du max d’attraction) | F_phi m=2 tout')
for R in (3.0, 4.0, 6.0, 8.15, 10.0, 12.0):
    Fr = {n: [] for n in P}; Fp = []
    for a in az:
        x = np.array([R * np.cos(a), R * np.sin(a), 0.0]); er = x / R; ep = np.array([-er[1], er[0], 0.0]); tp = 0.0
        for n in P:
            f = acc(x, n); Fr[n].append(f @ er); tp += f @ ep
        Fp.append(tp)
    tot = sum(np.array(v) for v in Fr.values()); F0 = tot.mean()
    amp = lambda v: 2 * abs((np.array(v) * np.exp(-2j * az)).mean())
    c2 = (tot * np.exp(-2j * az)).mean()
    print(f'{R:5.2f} {F0:9.1f} | ' + '  '.join(f'{100 * amp(Fr[n]) / abs(F0):5.2f}' for n in P) + f'  {100 * amp(tot) / abs(F0):5.2f} ({np.degrees(np.angle(-c2)) / 2 % 180:5.1f}°) | {100 * amp(Fp) / abs(F0):5.2f}')
