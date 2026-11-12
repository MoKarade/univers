#!/usr/bin/env node
/* Lot G : passages de Mercure et de Vénus devant le Soleil de 1600 à 2300, calculés avec le code même de la page
   (app/src/23_events.js, positions VSOP87), écrits dans app/gen/transits.js. Le contrôle contre la NASA est dans
   app/test/evenements.test.js. Usage : node pipeline/gravite/build_transits.js */
const fs = require('fs'), vm = require('vm'), path = require('path'), app = path.join(__dirname, '..', '..', 'app');
const rd = f => fs.readFileSync(path.join(app, f), 'utf8'); global.atob = s => Buffer.from(s, 'base64').toString('binary');
vm.runInThisContext((rd('gen/data.js') + rd('gen/data2.js') + rd('gen/ephem.js') + rd('src/20_physics.js') + rd('src/23_events.js') + "function b64ToBytes(s) { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }").replace(/^const /gm, 'var '));
const jd = y => Date.UTC(y, 0, 1) / 864e5 + 2440587.5, out = { src: 'Calculé par la page (VSOP87, 23_events.js) ; contrôlé contre le catalogue de la NASA (F. Espenak) de 2026 à 2200' };
for (const k of ['mercury', 'venus']) { out[k] = evTransits(k, jd(1600), jd(2301)).map(t => [+t.jd.toFixed(5), +t.sep.toFixed(1), +t.rSun.toFixed(1)]); console.log(k, out[k].length); }
fs.writeFileSync(path.join(app, 'gen', 'transits.js'), 'Object.assign(DATA, { TRANSITS: ' + JSON.stringify(out) + ' });\n');
