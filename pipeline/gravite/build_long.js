#!/usr/bin/env node
/* Lot G (G2) : table des orbites du système solaire sur des millions d'années, pour la page.

   Entrée : les fichiers .el de long.js (vers le passé et vers l'avenir, même point de départ).
   Sortie : un fichier binaire (chargé à part de la page, au-delà de ±3 000 ans) :
     en-tête Float64 [version, jd0, pas en jours (1 000 ans), nPasse, nFutur, nCorps, pasLent]
     puis Float32 λ (longitude moyenne, radians) tous les 1 000 ans, du plus ancien au plus récent, nCorps par date ;
     puis Float32 a, e, i, Ω, ϖ tous les pasLent × 1 000 ans (orbites qui changent lentement).
   Corps : les 9 premiers de NB_BODIES (8 planètes, barycentre Terre-Lune compris, et Pluton).
   Usage : node build_long.js <passe.el> <futur.el> <sortie.bin> [milliers d'années gardés de chaque côté] */
const fs = require('fs'), [fp, ff, out, keep] = process.argv.slice(2), NB = 13, NK = 9, SLOW = 10, DAYS = 365252;
const rd = f => { const b = fs.readFileSync(f); return new Float32Array(b.buffer, b.byteOffset, b.length / 4); };
const P = rd(fp), Fu = rd(ff), K = keep ? +keep : Infinity, nP = Math.min(P.length / (NB * 6) - 1, K), nF = Math.min(Fu.length / (NB * 6) - 1, K), n = nP + nF + 1;
/* ligne k (0 = le plus ancien) : passé inversé, puis l'avenir (la date de départ n'est écrite qu'une fois) */
const row = k => k <= nP ? P.subarray((nP - k) * NB * 6, (nP - k + 1) * NB * 6) : Fu.subarray((k - nP) * NB * 6, (k - nP + 1) * NB * 6);
const lam = new Float32Array(n * NK), nS = Math.floor((n - 1) / SLOW) + 1, slow = new Float32Array(nS * NK * 5);
for (let k = 0; k < n; k++) { const r = row(k); for (let b = 0; b < NK; b++) lam[k * NK + b] = r[b * 6 + 5]; }
for (let s = 0; s < nS; s++) { const r = row(s * SLOW); for (let b = 0; b < NK; b++) for (let q = 0; q < 5; q++) slow[(s * NK + b) * 5 + q] = r[b * 6 + q]; }
const hdr = new Float64Array([1, 2461354.5, DAYS, nP, nF, NK, SLOW]);
fs.writeFileSync(out, Buffer.concat([Buffer.from(hdr.buffer), Buffer.from(lam.buffer), Buffer.from(slow.buffer)]));
console.log('écrit', out, (fs.statSync(out).size / 1e6).toFixed(2), 'Mo ;', nP, 'milliers d’années vers le passé,', nF, 'vers l’avenir');
