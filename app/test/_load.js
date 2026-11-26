'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { performance: nodePerf } = require('perf_hooks');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const APP_DIR = path.join(REPO_ROOT, 'app');
const GEN_DIR = path.join(APP_DIR, 'gen');
const SRC_DIR = path.join(APP_DIR, 'src');

/** Liste triée (ordre app/build.py) des fichiers JS dans app/src/. */
function listSrcFiles() {
  return fs
    .readdirSync(SRC_DIR)
    .filter(f => f.endsWith('.js'))
    .sort();
}

/** Concatène les fichiers JS de app/src/ (tous par défaut, ou une sélection). */
function readSrcConcat(files) {
  const list = files || listSrcFiles();
  return list
    .map(f => fs.readFileSync(path.isAbsolute(f) ? f : path.join(SRC_DIR, f), 'utf8'))
    .join('\n');
}

function resolveFile(baseDir, prefix, f) {
  if (path.isAbsolute(f)) return f;
  return f.startsWith(prefix) ? path.join(APP_DIR, f) : path.join(baseDir, f);
}

/** Promouvoir const/let en colonne 0 en var (1:1 sur les numéros de ligne) pour exposer sur le contexte VM. */
function hoistTopLevel(code) {
  return code.replace(/^(const|let)(?=\s)/gm, 'var');
}

/**
 * Charge les fichiers app/gen/*.js et app/src/*.js demandés dans un contexte VM isolé.
 * Utilise vm.constants.DONT_CONTEXTIFY (Node >= 20.18 / 22) pour conserver la vitesse JIT native V8
 * (sans le proxy C++ ContextifyContext qui ralentit les boucles numériques d'un facteur ~15-18x).
 */
function loadUnivers({ gen = [], src = [], globals = {} } = {}) {
  const dataIdx = gen.findIndex(f => path.basename(f) === 'data.js');
  if (dataIdx > 0) {
    throw new Error('loadUnivers: data.js doit être en première position dans gen[]');
  }
  const fast = !!(vm.constants && vm.constants.DONT_CONTEXTIFY);
  const ctx = fast ? vm.createContext(vm.constants.DONT_CONTEXTIFY) : vm.createContext({});
  Object.assign(
    ctx,
    {
      DATA: {},
      console,
      atob: s => Buffer.from(s, 'base64').toString('binary'),
      btoa: s => Buffer.from(s, 'binary').toString('base64'),
      performance: globalThis.performance || nodePerf,
      setTimeout,
      clearTimeout,
      URL,
      TextDecoder,
      TextEncoder,
    },
    fast ? {} : { Float64Array, Float32Array },
    globals
  );

  for (const f of gen) {
    const abs = resolveFile(GEN_DIR, 'gen/', f);
    const code = hoistTopLevel(fs.readFileSync(abs, 'utf8'));
    vm.runInContext(code, ctx, { filename: abs });
  }
  for (const f of src) {
    const abs = resolveFile(SRC_DIR, 'src/', f);
    const code = "'use strict';\n" + hoistTopLevel(fs.readFileSync(abs, 'utf8'));
    vm.runInContext(code, ctx, { filename: abs, lineOffset: -1 });
  }
  return ctx;
}

module.exports = { loadUnivers, listSrcFiles, readSrcConcat, REPO_ROOT };
