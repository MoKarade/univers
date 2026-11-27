"""Force de la barre (mode 2) par anneau, étoiles d'une galaxie. Usage : barre_rayon.py <fichier.npz> [gid]"""
import sys, numpy as np
z = np.load(sys.argv[1]); g = int(sys.argv[2]) if len(sys.argv) > 2 else 0
pos, vel, m, kind = z['pos'], z['vel'], z['m'], z['kind']
gid = z['gid'] if 'gid' in z.files else np.zeros(len(m), int)
s = (gid == g) & np.isin(kind, [1, 2, 4, 5])
p, w, v = pos[s].astype(float), m[s].astype(float), vel[s].astype(float)
print(sys.argv[1], 'étoiles', s.sum(), 'sortes', {int(k): int(((kind == k) & (gid == g)).sum()) for k in np.unique(kind)})
c = np.median(p, axis=0)
for _ in range(6):
    d = np.linalg.norm(p - c, axis=1); c = np.average(p[d < 3], axis=0, weights=w[d < 3])
q = p - c; v = v - np.average(v[d < 3], axis=0, weights=w[d < 3])
L = (w[:, None] * np.cross(q, v))[np.linalg.norm(q, axis=1) < 15].sum(0); n = L / np.linalg.norm(L)
a = np.cross(n, [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(n, a)
x, y, zz = q @ a, q @ b, q @ n; R = np.hypot(x, y); ph = np.arctan2(y, x)
for r0, r1 in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 7), (7, 10), (2, 4)]:
    k = (R >= r0) & (R < r1); A = (w[k] * np.exp(2j * ph[k])).sum() / w[k].sum()
    print(f'  R {r0}-{r1} kpc : A2 = {abs(A):.3f}, angle {np.degrees(np.angle(A)) / 2:+4.0f}°, épaisseur {np.sqrt(np.average(zz[k] ** 2, weights=w[k])):.2f} kpc, masse {w[k].sum():.3g}')
