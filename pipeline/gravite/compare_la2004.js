#!/usr/bin/env node
/* Lot G (G2) : excentricité de la Terre (barycentre Terre-Lune) de l'intégration longue (long.js) contre la solution publiée
   La2004 (Laskar et al. 2004, A&A 428, 261 ; fichiers INSOLN/INSOLP.LA2004.BTL.ASC de l'IMCCE, un point par millier d'années).
   Usage : node compare_la2004.js <long.json> <INSOL*.ASC> → écart médian et corrélation par tranche d'un million d'années. */
const fs = require('fs'), [jf, lf] = process.argv.slice(2), d = JSON.parse(fs.readFileSync(jf, 'utf8')), k = d.names.indexOf('emb');
const L = fs.readFileSync(lf, 'utf8').trim().split('\n').map(l => l.trim().split(/\s+/).map(x => parseFloat(x.replace('D', 'E'))));
const e = d.e.map(r => r[k]), n = Math.min(e.length, L.length), out = [];
for (let a = 0; a < n; a += 1000) {
  const b = Math.min(n, a + 1000), x = e.slice(a, b), y = L.slice(a, b).map(r => r[1]), m = v => v.reduce((s, q) => s + q, 0) / v.length, mx = m(x), my = m(y);
  const cov = x.reduce((s, q, i) => s + (q - mx) * (y[i] - my), 0), r = cov / Math.sqrt(x.reduce((s, q) => s + (q - mx) ** 2, 0) * y.reduce((s, q) => s + (q - my) ** 2, 0));
  const ad = x.map((q, i) => Math.abs(q - y[i])).sort((p, q) => p - q);
  out.push({ Ma: a / 1000, ecart_median: +ad[ad.length >> 1].toFixed(5), correlation: +r.toFixed(4) });
}
console.log(JSON.stringify(out));
