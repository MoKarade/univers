/* ============================================================================
   APPLICATION
   ============================================================================ */
(async function () {
  const $ = id => document.getElementById(id);
  const fail = msg => { $('loader').querySelector('h2').textContent = 'Affichage impossible'; $('lmsg').textContent = msg; $('lbar').hidden = true; };
  if (typeof THREE === 'undefined') return fail('La bibliothèque 3D n’a pas pu être chargée. Vérifiez la connexion, puis rechargez la page.');
  const canvas = $('gl'), reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ease = k => k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;

  /* ---- niveau de détail selon l'appareil ---- */
  const coarse = matchMedia('(pointer: coarse)').matches, small = Math.min(innerWidth, innerHeight) < 700;
  const mem = navigator.deviceMemory || 4, cores = navigator.hardwareConcurrency || 4;
  let tier = (coarse || small) ? ((mem <= 3 || cores <= 4) ? 0 : 1) : 2;
  if (typeof window.__TIER === 'number') tier = window.__TIER;
  const Q = [
    { gal: 52000, glow: 2600, web: 60000, modes: 44, far: 24000, patch: 8000, oort: 6000, belt: 2400, halo: 3500, lg: 0.45, dpr: 1.5, bloom: true, keep: 0.5, bodies: 0.45, starChunks: 16, dynN: 12000, dyn31: 3000, dynSteps: 4, gaia: 0.3 },
    { gal: 95000, glow: 4200, web: 115000, modes: 60, far: 45000, patch: 14000, oort: 10000, belt: 4000, halo: 6000, lg: 0.7, dpr: 2, bloom: true, keep: 0.75, bodies: 0.7, starChunks: 10, dynN: 26000, dyn31: 6000, dynSteps: 6, gaia: 0.6 },
    { gal: 175000, glow: 5000, web: 230000, modes: 76, far: 80000, patch: 24000, oort: 18000, belt: 7000, halo: 10000, lg: 1, dpr: 2, bloom: true, keep: 1, bodies: 1, starChunks: 6, dynN: 90000, dyn31: 30000, dynSteps: 5, gaia: 1 },
  ][tier];

  /* ---- génération ---- */
  const setProg = (f, msg) => { $('lbar').firstElementChild.style.width = Math.round(f * 100) + '%'; if (msg) $('lmsg').textContent = msg; };
  const pause = () => new Promise(r => setTimeout(r, 0));
  const M = DATA.M_GAL2ECL;
  (DATA.LGX_FIX || []).forEach(f => { const x = DATA.LG_X[f[0]]; if (x) { x[5] = f[1]; x[1] = f[2]; x[2] = x[3] = x[4] = null; } });      // trois fiches portaient les données d'une autre galaxie : nom et vitesse corrigés, le reste retiré
  const sunGal0 = DATA.SGRA_GAL.map(x => -x * GAL.R0);          // Soleil dans le repère galactique centré sur Sagittarius A* (kpc)
  const gcRelKpc0 = mulM(M, sunGal0.map(x => -x));
  const G = {};
  setProg(0.06, 'Mise en orbite des planètes'); await pause();
  G.oort = genOort(Q.oort, 13);
  setProg(0.16, 'Allumage de la Voie lactée'); await pause();
  G.gal = genGalaxy(Q.gal, Q.glow, 21); G.lg = genLocalGroup(Q.lg, 22, gcRelKpc0); G.m31 = genDiskGalaxy(23, Math.round(9000 * Q.lg), 24);
  const MAG = { c: [], r: [0, 0, 0], r0: [0, 0, 0] };      // Nuages de Magellan : ils suivent l'orbite calculée du Grand Nuage
  for (const key of ['LMC', 'SMC']) { const p = mulM(DATA.M_GAL2ECL, DATA[key].pos); let b = null, bd = 8; for (const c of G.lg.centers) { const d = Math.hypot(c.c[0] - p[0], c.c[1] - p[1], c.c[2] - p[2]); if (d < bd) { bd = d; b = c; } }
    if (b) { b.m0 = b.c.slice(); MAG.c.push(b); for (let i = 0; i < G.lg.N; i++) if (Math.abs(G.lg.cen[i * 3] - b.m0[0]) + Math.abs(G.lg.cen[i * 3 + 1] - b.m0[1]) + Math.abs(G.lg.cen[i * 3 + 2] - b.m0[2]) < 1e-3) G.lg.grp[i] = 2; } }
  setProg(0.5, 'Placement des étoiles, des galaxies et des quasars mesurés'); await pause();


  setProg(0.95, 'Réglage des instruments'); await pause();
  let Rr;
  try { Rr = createRenderer(canvas, Q, G); } catch (e) { console.error(e); return fail('Ce navigateur ne peut pas afficher la 3D (WebGL indisponible).'); }

  /* ---- état ---- */
  const NOW_MS = Date.now(), JD_NOW = 2440587.5 + NOW_MS / 86400000, T_NOW = (JD_NOW - JD_J2000) / 36525;
  const fid = buildCosmo(PLANCK), D_FID = fid.Dtoday;
  /** Distance comobile actuelle en fonction du décalage vers le rouge, pour la cosmologie choisie : table utilisée pour placer chaque galaxie observée. */
  let lcOn = false;      /* S7 : la constante S n’existe pas encore au premier appel */
  function surveyLut(C) { return surveyLutOf(C, DATA.SURV_ZMAX, lcOn); }      /* S7 : 29_cone.js */
  Rr.setSurvey(surveyLut(fid)); let surveyDirty = false;
  // avenir : Soleil, planètes englouties, Andromède
  /* R5 : Mercure et Vénus suivent l'orbite calculée par planetTide (marées et frottement, Schröder et Smith 2008) ; engloutissement à la fin de la spirale. */
  const TIDE_P = { mercury: planetTide(DATA.JPL1.mercury[0], 3.3011e23), venus: planetTide(DATA.JPL1.venus[0], 4.8675e24) };
  /* R6 : la Terre suit son orbite calculée tant qu'elle s'élargit (perte de masse du Soleil : résultat commun à toutes les études). Au moment où les
     marées commencent à la resserrer, les études divergent : engloutie selon Schröder et Smith 2008 et Rasio et al. 1996, pourrait survivre selon Rybicki et
     Denis 2001. T_DIV est un résultat du modèle de Schröder et Smith (instant où les marées l'emportent), pas un consensus. À partir de là, la Terre n'est plus dessinée et un panneau le dit (décision 3 de Marc : « sort inconnu »). */
  const TIDE_E = planetTide(DATA.JPL1.emb[0], 5.9722e24 + 7.342e22), T_DIV = (() => { const T = TIDE_E.tab; let mx = 0, tm = 0; for (let i = 0; i < T.length; i += 2) if (T[i + 1] > mx) { mx = T[i + 1]; tm = T[i]; } return tm; })();
  const ENG = { mercury: TIDE_P.mercury.tEng, venus: TIDE_P.venus.tEng, earth: T_DIV }, SS = {}, m31r = [0, 0, 0], m31r0 = [0, 0, 0];
  let orbitDirty = true;
  // vitesse d'Andromède par rapport au centre de la Voie lactée (km/s, axes galactiques), selon trois mesures publiées de son mouvement propre
  const M31_MEAS = [['Gaia, 2025', [28.4, -109.8, 41.4]], ['Hubble, 2012', [44.1, -118.0, 3.1]], ['Gaia, 2021', DATA.M31.vel]];
  const vtOf = V => { const P = DATA.M31.pos, d = Math.hypot(P[0], P[1], P[2]), vr = (V[0] * P[0] + V[1] * P[1] + V[2] * P[2]) / d; return Math.hypot(V[0] - vr * P[0] / d, V[1] - vr * P[1] / d, V[2] - vr * P[2] / d); };
  const DTAB = dynTables(), LMCO = lmcOrbit(); andromedaAt(LMCO, 0, MAG.r0);
  const LMIN = 6.6, LMAX = 26.95, SPEED_MAX_LOG = 17.2, LMICRO = -20.0;      /* R13 : le zoom s'arrête à 10⁻²⁰ m, le plus fin jamais sondé (ordre de grandeur, LHC) ; accessible seulement en plongeant vers la Terre */
  const S = { logR: Math.log10(42 * AU), az: -0.95, el: 0.6, focus: 'sun', fa: null, curFo: [0, 0, 0], ty: 0, lastTy: 0, speed: 20 * DAY_S, dir: 1, playing: true, T1: 0, T2: 0, dmMix: 1, beltYears: 0, par: Object.assign({}, PLANCK), cosmo: fid, anim: null, lite: false, hit: null, vt: 33.7, m31V: null, tOn: null, dyn: null, orbit: null, sel: null, center: null, ck: 0, cpos: null,
    opts: { labels: true, orbits: true, realSize: false, dm: true, horizons: true, comoving: false, simWeb: false } };
  const F = { tg: [0, 0, 0], gcRel: [0, 0, 0], cos: {}, opts: S.opts, aFac: 1 };
  F.eng = {}; F.lgShift = [0, 0, 0]; F.lgShift2 = [0, 0, 0]; F.lmcGone = 0; F.sun = sunState(0, SS); F.sunCol = tempRgb(5774); F.orb = 1; F.mergeK = 0; F.selPos = null;
  let sol = solarSystemAt(T_NOW), scrubbing = false;
  const oSunDM = omegaGal(GAL.R0, true), oSunNo = omegaGal(GAL.R0, false), oArm = GAL.OMEGA_ARMS * KMS_KPC_RADGYR;
  const sunGal = [0, 0, 0];
  const bodyPosM = k => { const o = (F.orbP && F.orbP[k]) || F.orb || 1; if (k === 'sun') return [0, 0, 0]; if (k === 'moon') return [(sol.earth[0] * o + sol.moonGeo[0]) * AU, (sol.earth[1] * o + sol.moonGeo[1]) * AU, (sol.earth[2] * o + sol.moonGeo[2]) * AU]; const p = k === 'earth' ? sol.earth : sol.planets[k].pos; return [p[0] * o * AU, p[1] * o * AU, p[2] * o * AU]; };
  const minLog = () => Math.log10(2.4 * BODY[S.focus].r * 1e3);
  const clampZoom = l => clamp(l, S.focus === 'earth' && !S.center ? LMICRO : Math.max(LMIN, S.center ? (S.center.radM ? Math.log10(2.4 * S.center.radM) : LMIN) : minLog()), LMAX);      /* sur une étoile : on s'arrête à sa surface ; un objet sans rayon connu (comète, sonde) : à la borne générale, plus à celle de l'astre suivi */

  const sunDirLocal = new THREE.Vector3(...mulM(M, [-1, 0, 0])).applyQuaternion(Rr.qFrameGal.clone().invert());
  const AZ_GAL = Math.atan2(sunDirLocal.y, sunDirLocal.x) + 0.45;
  const STOPS = [
    { name: 'Terre et Lune', logR: Math.log10(5.6e8), focus: 'earth', speed: 6 * 3600, el: 0.4 },
    { name: 'Système solaire', logR: Math.log10(42 * AU), focus: 'sun', speed: 20 * DAY_S, el: 0.6 },
    { name: 'Nuage d’Oort', logR: Math.log10(1.3e5 * AU), focus: 'sun', el: 0.4 },
    { name: 'Étoiles proches', logR: Math.log10(15 * LY), focus: 'sun', el: 0.32 },
    { name: 'Voie lactée', logR: Math.log10(74000 * LY), focus: 'sun', speed: 5e6 * YEAR_S, el: 0.78, az: AZ_GAL },
    { name: 'Groupe local', logR: Math.log10(4.8e6 * LY), speed: 5e6 * YEAR_S, el: 0.5 },
    { name: 'Superamas voisins', logR: Math.log10(2.6e8 * LY), speed: 0.4e9 * YEAR_S, el: 0.42 },
    { name: 'Toile cosmique', logR: Math.log10(2.2e9 * LY), speed: 0.4e9 * YEAR_S, el: 0.34 },
    { name: 'Univers observable', logR: Math.log10(6.7e10 * LY), speed: 0.4e9 * YEAR_S, el: 0.3 },
    // l'infiniment petit : on plonge vers la Terre, puis dans une gouttelette d'eau, jusqu'à 10⁻²⁰ m (au-delà : inconnu)
    { name: 'Gouttelette d’eau', logR: Math.log10(3e-3), focus: 'earth', micro: true },
    { name: 'Molécules d’eau', logR: Math.log10(5.5e-10), focus: 'earth', micro: true },
    { name: 'Atome', logR: Math.log10(7e-11), focus: 'earth', micro: true },
    { name: 'Noyau atomique', logR: Math.log10(6.5e-15), focus: 'earth', micro: true },
    { name: 'Proton', logR: Math.log10(1.1e-15), focus: 'earth', micro: true },
    { name: 'Quarks', logR: Math.log10(8e-19), focus: 'earth', micro: true },
    { name: 'Limite du connu', logR: -20.0, focus: 'earth', micro: true },
  ];
  /* ---- l'infiniment petit : ce qui est affiché et dit à chaque palier. lo : le palier vaut tant que log10(demi-champ en mètres) reste au-dessus. ---- */
  const MLEV = [
    { id: 'survol', lo: 3.2, place: 'Au-dessus de la Terre', note: 'Vous plongez vers la surface. La simulation n’a pas d’image réelle du sol à moins de quelques kilomètres : plus bas, elle vise une gouttelette d’eau au-dessus de l’océan.' },
    { id: 'approche', lo: 0.3, place: 'Près de la surface', note: 'Entre le kilomètre et le mètre, rien n’est dessiné : la simulation n’a aucune donnée réelle à cette finesse. Repères : une baleine bleue mesure environ 25 m, un humain moins de 2 m.' },
    { id: 'goutte', lo: -4.2, place: 'Gouttelette d’eau', name: 'Gouttelette d’eau', sub: 'Un embrun au-dessus de l’océan', note: 'Une gouttelette de 2 mm contient environ 140 milliards de milliards de molécules d’eau.',
      rows: [['Diamètre', '2 mm (taille choisie pour l’exemple)'], ['Masse', '4,2 mg'], ['Molécules d’eau', 'environ 1,4 × 10²⁰'], ['Repères de taille', 'un cheveu : 0,05 à 0,1 mm d’épaisseur'], ['Certitude', 'Nombre de molécules calculé d’après la densité de l’eau et la constante d’Avogadro : Certain']] },
    { id: 'eau', lo: -8.6, place: 'Dans la goutte', name: 'À l’intérieur de l’eau', sub: 'Du millimètre au nanomètre', note: 'En dessous d’un demi-micromètre, la lumière visible ne peut plus rien montrer : ses ondes sont trop larges. Tout ce qui suit vient de mesures indirectes et de calculs.',
      rows: [['Ce que vous voyez', 'un fond uni : à cette échelle, l’eau paraît continue'], ['7 µm', 'un globule rouge'], ['1 à 2 µm', 'une bactérie'], ['0,4 à 0,7 µm', 'les ondes de la lumière visible'], ['0,1 µm', 'un virus de la grippe'], ['2 nm', 'la largeur de la double hélice d’ADN'], ['Unités', '1 µm = un millième de millimètre ; 1 nm = un millième de µm'], ['Certitude', 'Tailles usuelles arrondies : Certain']] },
    { id: 'mol', lo: -9.75, place: 'Molécules d’eau', name: 'Molécules d’eau', sub: 'H₂O : un atome d’oxygène, deux d’hydrogène', note: 'Vue en coupe de l’eau liquide. Chaque molécule est à sa vraie taille ; leur agitation est ralentie plus de mille milliards de fois.',
      rows: [['Liaison oxygène-hydrogène', '95,7 pm'], ['Angle entre les deux liaisons', '104,5°'], ['Écart entre molécules voisines', 'environ 0,28 nm'], ['Densité', '33 molécules par nanomètre cube'], ['Agitation', 'environ 640 m/s à 25 °C'], ['Unités', '1 pm = un millième de nanomètre'],
        ['Dans la simulation', 'Géométrie de chaque molécule : mesurée. Position des voisines : tirée au hasard, à la bonne densité. Rouge pour l’oxygène, blanc pour l’hydrogène : couleurs de convention.'], ['Sources', 'Géométrie : Benedict, Gailar et Plyler 1956 ; densité et agitation : calculées'], ['Certitude', 'Certain pour la géométrie et la densité ; modèle pour l’arrangement']] },
    { id: 'atome', lo: -12.3, place: 'Atome d’oxygène', name: 'Nuage d’électrons', sub: 'Une molécule d’eau vue de l’intérieur : 10 électrons', note: 'Un électron n’a pas de trajectoire : chaque point bleu est un endroit où l’on pourrait le trouver. Plus c’est dense, plus c’est probable.',
      rows: () => waterRows(DATA.WATER_QM) },
    { id: 'vide', lo: -13.6, place: 'Le vide de l’atome', name: 'Entre les électrons et le noyau', sub: 'Presque tout l’atome est vide', note: 'Si le noyau était une bille d’un centimètre, l’atome ferait plus de 200 mètres de large.',
      rows: [['Rayon du noyau d’oxygène', '2,70 fm'], ['Masse', '99,97 % de la masse de l’atome est dans le noyau'], ['Unités', '1 fm = un millionième de nanomètre'], ['Sources', 'Rayon : Angeli et Marinova 2013'], ['Certitude', 'Certain']] },
    { id: 'noyau', lo: -14.75, place: 'Noyau d’oxygène', name: 'Noyau d’oxygène 16', sub: '8 protons et 8 neutrons', note: 'Le noyau : 8 protons (rouges) et 8 neutrons (gris), tenus ensemble par l’interaction forte.',
      rows: [['Rayon de charge', '2,70 fm (2,6991 fm, mesuré)'], ['Contenu', '8 protons et 8 neutrons'], ['Ce qui les tient', 'l’interaction forte, environ cent fois plus intense que la répulsion électrique entre protons'], ['Vitesse des protons et neutrons', 'jusqu’à environ un quart de celle de la lumière (impulsion de Fermi ≈ 250 MeV/c)'],
        ['Dans la simulation', 'Place de chaque nucléon tirée au hasard dans la répartition mesurée (rayon mesuré). Couleurs de convention.'], ['Sources', 'Rayon : Angeli et Marinova 2013 ; répartition de charge : de Vries, de Jager et de Vries 1987 (oscillateur harmonique, a = 1,833 fm, α = 1,544) ; impulsion de Fermi : Moniz et al. 1971'], ['Certitude', 'Certain pour le rayon, le contenu et la répartition ; tirage au hasard pour la place de chaque nucléon']] },
    { id: 'proton', lo: -16.6, place: 'Proton', name: 'Intérieur d’un proton', sub: 'Quarks, paires et gluons, d’après les mesures', note: () => pdfNote(),
      rows: [['Rayon', '0,84 fm (CODATA 2022)'], ['Quarks de valence', 'deux « up » et un « down » : le compte net mesuré vaut 2 et 1'], ['Ce qui change avec la finesse', 'plus on regarde fin, plus la part d’impulsion des gluons et des paires quark-antiquark augmente'], ['Couleurs des points', 'rouge : quarks u principaux ; bleu : quark d principal ; turquoise : paires ; jaune : gluons'],
        ['Dans la simulation', 'Un point = une part d’impulsion, pas une particule. Parts mesurées, positions au hasard. Gros points : repères des trois quarks principaux (deux u, un d).'], ['Sources', 'Distributions de partons CT18NNLO (Hou et al. 2021, Phys. Rev. D 103, 014013), lues avec le format LHAPDF6 (Buckley et al. 2015) ; rayon : CODATA 2022'], ['Finesse et énergie', 'convention : la finesse est le demi-champ affiché, et l’énergie de la sonde Q = ħc / finesse (ordre de grandeur)'], ['Licence des données', 'aucune licence écrite pour les grilles (LHAPDF et CT18) ; l’article CT18 est sous CC BY 4.0 ; usage libre avec citation de Hou et al. 2021 et de LHAPDF6 (Buckley et al. 2015) [Probable]'], ['Certitude', 'Mesuré pour les parts d’impulsion et les comptes ; positions des points tirées au hasard']] },
    { id: 'quark', lo: -19.3, place: 'Quark', name: 'Quarks et électrons', sub: 'Aucune taille mesurée', note: 'Un quark reste un point : aucune expérience ne lui a trouvé de taille ni de structure.',
      rows: [['Taille d’un quark', 'inférieure à 0,43 × 10⁻¹⁸ m'], ['Portée de l’interaction faible', '2,5 × 10⁻¹⁸ m'], ['Détail le plus fin sondé', 'de l’ordre de 10⁻¹⁹ à 10⁻²⁰ m, au collisionneur LHC'], ['Dans la simulation', 'Le quark reste un point à toutes les échelles. Les cercles orangés marquent les limites mesurées.'],
        ['Sources', 'Limite : collaboration ZEUS 2016 ; portée : calculée d’après la masse du boson W'], ['Certitude', 'Certain pour la limite ; ordre de grandeur pour le LHC']] },
    { id: 'inconnu', lo: -99, place: 'Inconnu', name: 'Inconnu', sub: 'Aucune expérience n’a sondé plus fin', note: 'Inconnu : aucune expérience n’a sondé plus fin. Il reste quinze puissances de dix jusqu’à la longueur de Planck, 1,616 × 10⁻³⁵ m. Le zoom s’arrête ici.',
      rows: [['Détail le plus fin sondé', 'de l’ordre de 10⁻¹⁹ à 10⁻²⁰ m, au collisionneur LHC'], ['Jusqu’à la longueur de Planck', 'quinze puissances de dix, où aucune expérience n’est possible aujourd’hui'], ['Longueur de Planck', '1,616255 × 10⁻³⁵ m (CODATA 2022) : un chiffre calculé à partir de trois constantes, rien de plus n’est connu à cette échelle'], ['Dans la simulation', 'Le zoom s’arrête à 10⁻²⁰ m : rien n’est dessiné au-delà, faute de mesure.'], ['Certitude', 'Certain pour la valeur de la longueur de Planck ; inconnu pour tout le reste']] },
  ];
  const microOn = () => S.focus === 'earth' && !S.center && S.logR < 6.3, microLevel = lr => { for (const m of MLEV) if (lr > m.lo) return m; return MLEV[MLEV.length - 1]; }; let lastMl = '';

  /* ---- temps ---- */
  function setTime(ty) {
    const C = S.cosmo, lo = C.tBang !== null ? C.tBang * 1e9 + 1e5 : C.tStart * 1e9, hi = C.tEnd * 1e9 - (C.endKind === 'limit' ? 0 : 2e5);
    const t = clamp(ty, lo, hi), d = (t - S.ty) / 1e9;
    S.T1 += d * S.dmMix; S.T2 += d * (1 - S.dmMix); S.ty = t;
    return t !== ty ? (ty < lo ? 'start' : 'end') : null;
  }
  function setSpeed(sp) { S.speed = clamp(sp, 1, Math.pow(10, SPEED_MAX_LOG)); $('speed').value = Math.round(Math.log10(S.speed) / SPEED_MAX_LOG * 1000); $('speed-out').textContent = fmtSpeed(S.speed); }
  function syncPlay() { $('i-play').setAttribute('d', S.playing ? 'M3 1.5h3.5v13H3zM9.5 1.5H13v13H9.5z' : 'M3.5 1.5 14 8 3.5 14.5z'); $('b-play').setAttribute('aria-label', S.playing ? 'Mettre le temps en pause' : 'Relancer le temps'); }
  function setFocus(key, dur) { if (key === S.focus) return; S.fa = { from: S.curFo.slice(), t0: performance.now() / 1000, dur: reduced ? 0.001 : (dur || 1.2) }; S.focus = key; }
  /* ---- navigation : y aller, revenir en arrière, retour au système solaire, reculer ou avancer d'un cran ---- */
  const NAVH = []; let histT = 0;
  function syncNav() { const b = $('n-back'); if (b) b.disabled = !NAVH.length; }
  function pushHist() { const now = performance.now(); if (now - histT < 80) return; histT = now; NAVH.push({ lr: S.anim ? S.anim.l1 : S.logR, az: S.az, el: S.el, focus: S.focus, center: S.center, sel: S.sel }); if (NAVH.length > 40) NAVH.shift(); syncNav(); }
  function goBack() { const h = NAVH.pop(); if (!h) return; histT = performance.now(); zoffReset(); select(h.sel); goTo(h.lr, { az: h.az, el: h.el, focus: h.focus, noHist: true }); S.center = h.center; renderCard(); syncNav(); }
  function goHome() { pushHist(); select(null); zoffReset(); const st = STOPS[1]; goTo(st.logR, { az: st.az, el: st.el, focus: 'sun', speed: st.speed, noHist: true }); }
  function goLr(o) { if (o.lr) return o.lr; if (o.orbit && o.orbit.P) return clamp(Math.log10(Math.hypot(o.orbit.P[0], o.orbit.P[1], o.orbit.P[2]) * AU * 2.4), 6.6, 15.6); const d = vlen(o.get()); return d < 1e14 ? 12.4 : d < 3e16 ? 15.6 : d < 1e19 ? 16.4 : d < 1.2e21 ? 18.9 : d < 4e22 ? 21.6 : d < 1.5e24 ? 22.6 : 24.3; }
  function flyTo(o, lrWanted) { const ph = photoNear(o), lr = ph ? clamp(Math.log10(ph.half * 1.05), 19.0, 23.8) : (lrWanted || goLr(o)), opt = { focus: 'sun', noHist: true }; o.isGal = !!ph;
    if (ph) { const p = o.get(), d = vlen(p) || 1, ae = Rr.azelFrom([-p[0] / d, -p[1] / d, -p[2] / d], smoothstep(17.8, 19.9, lr)); opt.az = ae[0]; opt.el = ae[1]; }      // on arrive du côté du Soleil : la galaxie apparaît comme sur les photos
    if (!ph && o.exoI !== undefined) { const sy = exoSys(o.exoI), p0 = sy.list[sy.list.length - 1]; if (p0) { const h = vnorm(vcross(p0.P, p0.Q)), d = vnorm([0.82 * p0.P[0] + 0.57 * h[0], 0.82 * p0.P[1] + 0.57 * h[1], 0.82 * p0.P[2] + 0.57 * h[2]]), ae = Rr.azelFrom(d, 0); opt.az = ae[0]; opt.el = ae[1]; } }
    goTo(lr, opt); zoffReset(); S.center = o; renderCard(); }
  function goThere(o) { if (!o) return; if (o.isEvent) { o.go(); return; } pushHist(); if (S.sel !== o) select(o); flyTo(o); }
  function stepZoom(dir) {      // +1 : reculer (voir plus large) ; −1 : avancer (voir de plus près)
    const cur = S.anim ? S.anim.l1 : S.logR;
    if (S.focus === 'earth' && !S.center && (cur < 7.5 || dir < 0)) { const c = STOPS.filter(st => st.micro).map(st => st.logR).concat([Math.log10(BODY.earth.focusR), 7.2, 5.2]); let best = null;      // vers l'infiniment petit : d'arrêt en arrêt
      for (const l of c) { const d = (l - cur) * dir; if (d > 0.12 && (best === null || d < (best - cur) * dir)) best = l; } if (best !== null) { goTo(best, { noHist: true }); return; } if (dir < 0) return; }
    if (S.focus !== 'sun' && !S.center && dir > 0) { const fr = Math.log10(BODY[S.focus].focusR), st = STOPS[1];      // depuis une planète : d'abord sa vue d'ensemble, puis le système solaire
      if (cur < fr - 0.15) goTo(fr, { noHist: true }); else goTo(st.logR, { az: st.az, el: st.el, focus: 'sun', speed: st.speed, noHist: true }); return; }
    if (S.focus === 'sun' && !S.center) { let best = null; for (const st of STOPS) { if (st.micro) continue; const d = (st.logR - cur) * dir; if (d > 0.12 && (!best || d < (best.logR - cur) * dir)) best = st; } if (best) { goTo(best.logR, { az: best.az, el: best.el, focus: best.focus || null, speed: best.speed, noHist: true }); return; } }
    goTo(clampZoom(cur + dir * 0.8), { noHist: true }); }
  function goTo(logR, o) {
    o = o || {};
    const lmin = (o.focus || S.focus) === 'earth' ? LMICRO : LMIN;
    if (!o.noHist && ((o.focus && o.focus !== S.focus) || Math.abs(clamp(logR, lmin, LMAX) - S.logR) > 0.6)) pushHist();
    const l1 = clamp(logR, lmin, LMAX), dur = reduced || o.instant ? 0.001 : clamp(1.3 + 0.3 * Math.abs(l1 - S.logR), 1.3, 6.5);
    S.anim = { t0: performance.now() / 1000, dur, l0: S.logR, l1, a0: S.az, a1: o.az !== undefined ? S.az + wrapPi(o.az - S.az) : S.az, e0: S.el, e1: o.el !== undefined ? o.el : S.el };
    if (o.focus) setFocus(o.focus, Math.max(0.8, dur * 0.55));
    if (o.speed && S.playing) setSpeed(o.speed);
  }
  const goStop = (st, instant) => { zoffReset(); if (st.micro) { S.center = null; if (S.sel) select(null); } goTo(st.logR, { az: st.az, el: st.el, focus: st.focus || (S.focus !== 'sun' ? 'sun' : null), speed: st.speed, instant }); };
  function focusBody(key) { zoffReset(); if (key === 'sun') return goStop(STOPS[1]); goTo(Math.log10(BODY[key].focusR), { focus: key, speed: 3600 }); }

  /* ---- étiquettes ---- */
  const LB = [], labelsEl = $('labels'); Rr.keyStars = DATA.STAR_LABELS.map(l => l.i);
  function addLabel(text, kind, prio, lo, hi, get, o) {
    o = o || {};
    const el = document.createElement('div'); el.className = 'lb' + (kind ? ' k-' + kind : ''); el.textContent = text; labelsEl.appendChild(el);
    const L = Object.assign({ el, prio, lo, hi, get, a: 0, w: 0, kind }, o);
    if (o.click) { el.setAttribute('role', 'button'); el.addEventListener('click', o.click); }
    LB.push(L); return L;
  }
  const add3 = (a, b, k) => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k];
  for (const b of BODIES) {
    const a = b.key === 'sun' ? 0.02 : b.key === 'moon' ? 0.00257 : b.key === 'earth' ? 1 : DATA.JPL1[b.key][0];
    addLabel(b.name, 'body', 0.5, b.key === 'sun' ? 9 : b.key === 'moon' ? 7.3 : b.key === 'earth' ? 7.6 : Math.log10(a * AU) - 2.1, b.key === 'moon' ? 10.3 : 14.2, () => Rr.bodies[b.key].pos,
      { body: b.key, gate: () => { const o = Rr.bodies[b.key]; return o.vis * fadeOut(o.px, 46, 80); }, click: () => focusBody(b.key) });
  }
  const dirLon = (lon, r) => [Math.cos(lon * DEG) * r, Math.sin(lon * DEG) * r, 0];
  addLabel('Ceinture d’astéroïdes', 'region', 2, 11.3, 12.45, () => dirLon(205, 2.75 * AU), { gate: () => F.sysK * F.sunAlive });
  addLabel('Ceinture de Kuiper', 'region', 2, 12.65, 13.7, () => dirLon(300, 45 * AU), { gate: () => F.sysK * F.sunAlive });
  addLabel('Nuage d’Oort', 'region', 2, 15.3, 16.8, () => [1.9e4 * AU, 2.3e4 * AU, 2.4e4 * AU], { gate: () => F.sysK * F.sunAlive });
  { const ML = (text, key, lo, hi, o) => { addLabel(text, 'region', 2, lo, hi, () => Rr.micro.pos[key], o); LB[LB.length - 1].micro = true; };
    ML('gouttelette d’eau', 'drop', -3.2, -0.3, { center: true }); ML('molécule d’eau', 'mol', -9.55, -8.95, { center: true }); ML('oxygène', 'O', -10.25, -9.5); ML('hydrogène', 'H1', -10.25, -9.5); ML('hydrogène', 'H2', -10.25, -9.5);
    ML('noyau d’oxygène', 'nuc', -13.9, -10.6); ML('proton', 'p', -15.0, -13.95, { center: true }); ML('neutron', 'n', -15.0, -13.95, { center: true });
    ML('quark up', 'q0', -16.9, -15.2); ML('quark up', 'q1', -16.9, -15.2); ML('quark down', 'q2', -16.9, -15.2);
    ML('portée de l’interaction faible', 'weak', -18.35, -16.95, { center: true }); ML('aucune structure observée en dessous', 'lim', -19.15, -17.7, { center: true }); ML('détail le plus fin sondé (ordre de grandeur)', 'lhc', -20.5, -19.0, { center: true });
    }
  for (const tag of ['AST', 'TNO']) { const B = Rr[tag], ast = tag === 'AST';
    for (const l of DATA[tag + '_LABELS']) if (l.i < B.count) addLabel(l.n, '', l.p + 0.4, ast ? 11.05 : 12.35, ast ? 12.75 : 14.5, () => [B.pos[l.i * 3] * AU, B.pos[l.i * 3 + 1] * AU, B.pos[l.i * 3 + 2] * AU], { gate: () => (ast ? Rr.beltVis : Rr.kuiperVis) }); }
  addLabel('Soleil', 'here', 0, 14.75, 21.6, () => [0, 0, 0]);
  { const want = { '1P/Halley': 'Comète de Halley', '2P/Encke': 'Comète Encke', '67P/Churyumov-Gerasimenko': 'Comète Tchouri (67P)', '109P/Swift-Tuttle': 'Comète Swift-Tuttle', 'C/1995 O1 (Hale-Bopp)': 'Comète Hale-Bopp' }, B = Rr.COM;
    DATA.COM_NAMES.split('|').forEach((n, i) => { if (want[n]) addLabel(want[n], '', 3.4, 11.4, 14.6, () => [B.pos[i * 3] * AU * F.orb, B.pos[i * 3 + 1] * AU * F.orb, B.pos[i * 3 + 2] * AU * F.orb], { gate: () => Rr.comVis }); }); }
  // ---- figures des constellations : segments entre étoiles réelles (tracés de Stellarium) ; elles se déforment avec le mouvement des étoiles
  const hipAt = new Map(); { const hp = Rr.star.hip; for (let i = 0; i < Rr.star.N; i++) if (hp[i]) hipAt.set(hp[i], i); }
  const conSeg = [], conNames = []; for (const c of DATA.CONST_FIG || []) { const first = conSeg.length; for (let j = 0; j + 1 < c[2].length; j += 2) { const a = hipAt.get(c[2][j]), b = hipAt.get(c[2][j + 1]); if (a !== undefined && b !== undefined) conSeg.push(a, b); } if (conSeg.length > first) conNames.push([c[1], first, conSeg.length]); }
  const conPos = new Float32Array(conSeg.length * 3); Rr.initConst(conPos); S.constOn = true; for (const i of new Set(conSeg)) if (!Rr.keyStars.includes(i)) Rr.keyStars.push(i);
  function updateConst() { const sp = Rr.starPos, cam = Rr.camPos, tg = F.tg, sc = F.s, vis = Rr.constVis > 0.003 && cam && tg;      // un segment dont une extrémité est derrière l'observateur n'est pas tracé (sinon il traverse l'écran)
    const front = i => ((sp[i] * LY - tg[0]) * sc - cam.x) * -cam.x + ((sp[i + 1] * LY - tg[1]) * sc - cam.y) * -cam.y + ((sp[i + 2] * LY - tg[2]) * sc - cam.z) * -cam.z > 0;
    for (let k = 0; k < conSeg.length; k += 2) { const i = conSeg[k] * 3, j = conSeg[k + 1] * 3, m = !vis || (front(i) && front(j)) ? j : i;
      conPos[k * 3] = sp[i]; conPos[k * 3 + 1] = sp[i + 1]; conPos[k * 3 + 2] = sp[i + 2]; conPos[k * 3 + 3] = sp[m]; conPos[k * 3 + 4] = sp[m + 1]; conPos[k * 3 + 5] = sp[m + 2]; } }
  for (const c of conNames) addLabel(c[0], '', 4.6, 9.5, 17.5, () => { let x = 0, y = 0, z = 0; for (let k = c[1]; k < c[2]; k++) { x += conPos[k * 3]; y += conPos[k * 3 + 1]; z += conPos[k * 3 + 2]; } const n = c[2] - c[1]; return [x / n * LY, y / n * LY, z / n * LY]; }, { gate: () => Rr.constVis });
  $('c-const').addEventListener('change', e => { S.constOn = e.target.checked; });
  // ---- objets suivis sur leur orbite : lunes et sondes (JPL Horizons), étoiles autour du trou noir central (Gillessen et al. 2017)
  let EXA = null; const EXS = {}, exoLab = [];
  const AUKM = 149597870.7, yearOf = jd => 2000 + (jd - 2451545) / 365.25, PLUTO_I = DATA.TNO_NAMES.split('|').findIndex(n => n.indexOf('Pluton') === 0);
  const CEN = { pluto: () => { const B = Rr.TNO, k = AU * (F.orb || 1); return [B.pos[PLUTO_I * 3] * k, B.pos[PLUTO_I * 3 + 1] * k, B.pos[PLUTO_I * 3 + 2] * k]; }, sgra: () => [F.gcRel[0], F.gcRel[1], F.gcRel[2]], sun: () => [0, 0, 0], exo: () => (EXA ? EXA.c() : null) }, cenOf = key => CEN[key] ? CEN[key]() : bodyPosM(key);
  // trajectoires réelles des sondes (JPL Horizons) : croisière vue du Soleil, survols vus de la planète survolée
  const PTR = {}; for (const n in (DATA.PTRAJ || {})) { const q = DATA.PTRAJ[n], f32 = s => new Float32Array(b64ToBytes(s).buffer); PTR[n] = { jd0: q.jd0, jd1: q.jd1, b: f32(q.b), o: new Float64Array(6), q: new Float64Array(6), enc: q.enc.map(e => ({ body: e.body, jdc: e.jdc, km: e.km, t0: e.t0, t1: e.t1, b: f32(e.b) })) }; }
  function hermRow(b, dt, out) { const n = b.length / 7; let lo = 0, hi = n - 1; if (dt <= b[7]) hi = 1; else if (dt >= b[(n - 2) * 7]) lo = n - 2; else while (hi - lo > 1) { const m = (lo + hi) >> 1; if (b[m * 7] <= dt) lo = m; else hi = m; }
    const i = lo * 7, j = hi * 7, h = b[j] - b[i], u = clamp((dt - b[i]) / h, 0, 1), u2 = u * u, u3 = u2 * u, h00 = 2 * u3 - 3 * u2 + 1, h10 = (u3 - 2 * u2 + u) * h, h01 = 3 * u2 - 2 * u3, h11 = (u3 - u2) * h;
    for (let k = 0; k < 3; k++) { out[k] = h00 * b[i + 1 + k] + h10 * b[i + 4 + k] + h01 * b[j + 1 + k] + h11 * b[j + 4 + k]; out[3 + k] = lerp(b[i + 4 + k], b[j + 4 + k], u); } return out; }
  function probeTab(m, jd, hx, hy, hz) { const T = m.tab, o = hermRow(T.b, jd - T.jd0, T.o); let x = o[0], y = o[1], z = o[2]; m.tv = Math.hypot(o[3], o[4], o[5]) * 1731.4568; m.encNow = null;
    for (const e of T.enc) if (jd > e.t0 && jd < e.t1) { const q = hermRow(e.b, jd - e.jdc, T.q), c = cenOf(e.body), w = smoothstep(0, 1.5, Math.min(jd - e.t0, e.t1 - jd)); x = lerp(x, c[0] / AU + q[0], w); y = lerp(y, c[1] / AU + q[1], w); z = lerp(z, c[2] / AU + q[2], w); m.encNow = e; m.encD = Math.hypot(q[0], q[1], q[2]) * AU; }
    const k = smoothstep(T.jd1 - 40, T.jd1, jd); return [lerp(x, hx, k), lerp(y, hy, k), lerp(z, hz, k)]; }
  const tabPath = m => { const b = m.tab.b, n = b.length / 7, o = new Float32Array(257 * 3); for (let i = 0; i <= 256; i++) { const k = Math.min(n - 1, Math.round(i / 256 * (n - 1))) * 7; o[i * 3] = b[k + 1]; o[i * 3 + 1] = b[k + 2]; o[i * 3 + 2] = b[k + 3]; } return o; };
  // Devenir du système solaire (dates en milliards d'années depuis aujourd'hui). Phobos, anneaux, Triton : estimations publiées.
  // Dispersion des planètes : scénario typique des simulations de Zink, Batygin et Adams (2020). Tout se dérègle une trentaine de milliards d'années après la mort du Soleil,
  // une seule planète géante reste environ 50 milliards d'années de plus. L'ordre exact est aléatoire ; Mars n'était pas dans ces simulations, son sort est incertain.
  /* R7 (voir docs/verite-avenir.md) : dates de coupure, en milliards d'années. Au-delà, l'objet n'est plus dessiné et son repère dit « sort inconnu ».
     Phobos : fin entre 20 et 40 Ma (Black et Mittal 2015) → coupure à la borne basse. Anneaux de Saturne : au plus ~300 Ma, apport mesuré par Cassini
     de matière mesuré par la sonde Cassini compatible avec 100 Ma → coupure à 100 Ma. Triton : 1,4 ou 3,6 Ga selon son état de rotation (Chyba et al. 1989) → coupure
     à 1,4 Ga. Système solaire : instabilité déclenchée par les étoiles de passage environ 30 Ga après la fin de la perte de masse du Soleil, soit vers 37,7 Ga
     d'ici (Zink, Batygin et Adams 2020, § III.3 : « for roughly 30 Gyr after solar mass-loss, the system remains stable ») → plus aucune planète dessinée. */
  const FATE = { phobos: 0.02, rings: 0.1, triton: 1.4 }, SYS_END = 12.30 - SUN_NOW + 30, SYS_PL = ['mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'];
  const KO = [], PFROM = { 'Voyager 1': 1981, 'Voyager 2': 1990, 'Pioneer 10': 1974, 'Pioneer 11': 1980, 'New Horizons': 2016 };
  for (const m of DATA.MOONS.list) KO.push(Object.assign({ kind: 'moon', jd0: DATA.MOONS.jd0, aAU: m.a / AUKM }, m));
  { const y0 = yearOf(DATA.MOONS.jd0); for (const t of DATA.SSTARS.map(t => Object.assign(t, (DATA.SSTARS_FIX || {})[t.n] || {}))) KO.push(Object.assign({ kind: 'sstar', p: 'sgra', jd0: DATA.MOONS.jd0, aAU: t.a * GAL.R0 * 1000, M0: TAU * (y0 - t.tp) / t.per, nr: TAU / (t.per * 365.25) }, t)); }
  for (const t of DATA.PROBES.list) KO.push(Object.assign({ kind: 'probe', p: 'sun', jd0: DATA.PROBES.jd0, aAU: t.a, hyp: true, from: PFROM[t.n] || 1990, tab: PTR[t.n] || null }, t));
  for (let j = 0; j < 10; j++) KO.push({ kind: 'exo', p: 'exo', jd0: 2461355.5, aAU: 1, e: 0, P: [1, 0, 0], Q: [0, 1, 0], M0: 0, nr: 0.01, n: '', d: 1, on: false });
  const KSETS = {}; KO.forEach((m, k) => { const key = m.kind + ':' + m.p; (KSETS[key] = KSETS[key] || { key, kind: m.kind, cen: m.p, idx: [], vis: 0 }).idx.push(k); });
  const kSets = Object.values(KSETS), kPos = new Float64Array(KO.length * 3);
  for (const t of kSets) { t.rel = new Float32Array(t.idx.length * 3); t.look = new Float32Array(t.idx.length * 2); t.near = t.kind === 'sstar';
    t.col = t.kind === 'moon' ? [0.86, 0.9, 1.0] : t.kind === 'sstar' ? [0.72, 0.84, 1.0] : [1.0, 0.92, 0.55]; t.lr = t.kind === 'moon' ? [5.6, 6.3, 10.3, 10.9] : t.kind === 'sstar' ? [11.2, 11.9, 15.7, 16.4] : [11.6, 12.2, 15.2, 15.8];
    t.idx.forEach((k, j) => { const m = KO[k]; t.look[j * 2] = m.kind === 'moon' ? clamp(1.3 + Math.log10(m.d) * 0.6, 2, 3.4) : m.kind === 'sstar' ? clamp(4.7 - (parseFloat(m.k) || 16) * 0.13, 2, 3.2) : 2.8; t.look[j * 2 + 1] = 1; }); }
  { const t = KSETS['probe:sun']; if (t) t.lr = [6.4, 7.0, 15.2, 15.8]; }      // les sondes restent visibles de près, pour suivre leurs survols
  { const t = KSETS['exo:exo']; t.col = [0.62, 0.86, 1.0]; t.lr = [7.4, 8.1, 13.5, 14.2]; t.near = true; }
  Rr.initMoons(kSets);
  function solveKO(m, jd) { const M = m.M0 + m.nr * (jd - m.jd0);      // position dans le plan de l'orbite (UA) : ellipse, ou hyperbole pour les sondes qui quittent le système solaire
    if (m.hyp) { let H = Math.asinh(M / m.e); for (let i = 0; i < 40; i++) { const d = (m.e * Math.sinh(H) - H - M) / (m.e * Math.cosh(H) - 1); H -= d; if (Math.abs(d) < 1e-12) break; } return [m.aAU * (m.e - Math.cosh(H)), m.aAU * Math.sqrt(m.e * m.e - 1) * Math.sinh(H)]; }
    const E = keplerE(wrapPi(M), m.e); return [m.aAU * (Math.cos(E) - m.e), m.aAU * Math.sqrt(1 - m.e * m.e) * Math.sin(E)]; }
  function updateMoons() { F.moonC = F.moonC || {}; const yr = yearOf(F.jd);
    for (const t of kSets) { const c = cenOf(t.cen); F.moonC[t.key] = c; if (!c) continue; t.idx.forEach((k, j) => { const m = KO[k]; m.off = m.kind === 'probe' ? (m.tab ? F.jd < m.tab.jd0 : yr < m.from) : m.kind === 'exo' ? !m.on : m.kind === 'moon' && (!!F.eng[m.p] || (m.n === 'Phobos' && S.ty > FATE.phobos * 1e9) || (m.n === 'Triton' && S.ty > FATE.triton * 1e9) || S.ty < -4.5e9); let xy = m.off ? [0, 0] : solveKO(m, m.kind === 'probe' ? F.jd : m.kind === 'sstar' ? F.jdS : F.jdM); if (m.prec) { const f = m.prec * (yr - m.tp), cf = Math.cos(f), sf = Math.sin(f); xy = [xy[0] * cf - xy[1] * sf, xy[0] * sf + xy[1] * cf]; }      // précession relativiste : l'ellipse tourne lentement dans son plan
        let rx = m.P[0] * xy[0] + m.Q[0] * xy[1], ry = m.P[1] * xy[0] + m.Q[1] * xy[1], rz = m.P[2] * xy[0] + m.Q[2] * xy[1]; if (m.tab && !m.off && F.jd < m.tab.jd1) { const pt = probeTab(m, F.jd, rx, ry, rz); rx = pt[0]; ry = pt[1]; rz = pt[2]; }      // avant le dernier survol : trajectoire réelle
        if (m.off && m.kind === 'moon') rx = ry = rz = NaN; t.rel[j * 3] = rx; t.rel[j * 3 + 1] = ry; t.rel[j * 3 + 2] = rz; kPos[k * 3] = c[0] + rx * AU; kPos[k * 3 + 1] = c[1] + ry * AU; kPos[k * 3 + 2] = c[2] + rz * AU; }); } }
  { const SL = ['S1', 'S2', 'S4', 'S8', 'S9', 'S12', 'S13', 'S14', 'S38', 'S55'];
    KO.forEach((m, k) => { const t = KSETS[m.kind + ':' + m.p], l = Math.log10(m.aAU * AU), get = () => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]];
      if (m.kind === 'moon') addLabel(m.n, '', m.small ? 4 : 3.2, l - 0.8, l + (m.small ? 0.7 : 0.95), get, { gate: () => (m.off ? 0 : t.vis) });
      else if (m.kind === 'probe') addLabel(m.n, '', 3, 7.0, 15.5, get, { gate: () => (m.off ? 0 : t.vis) });
      else if (SL.indexOf(m.n) >= 0) addLabel(m.n, '', m.n === 'S2' ? 2.5 : 3.6, l - 0.9, l + 0.9, get, { gate: () => t.vis }); });
    addLabel('Sagittarius A*', '', 2, 11, 17.4, () => [F.gcRel[0], F.gcRel[1], F.gcRel[2]], { gate: () => KSETS['sstar:sgra'].vis > 0 ? 1 : fadeOut(S.logR, 16.4, 17.4) * 0 }); }
  KSETS['exo:exo'].idx.forEach((k, j) => { const m = KO[k], t = KSETS['exo:exo']; addLabel(' ', '', 2.8, 8, 13, () => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]], {}); const L = LB[LB.length - 1]; L.dyn = () => Math.log10(Math.max(m.aAU, 1e-4) * AU); L.span = 1.15; L.gate = () => (m.off ? 0 : t.vis); exoLab[j] = L; });
  const PLN = { mars: 'Mars', jupiter: 'Jupiter', saturn: 'Saturne', uranus: 'Uranus', neptune: 'Neptune', pluto: 'Pluton' };
  function selMoon(k) { const m = KO[k]; if (m.kind === 'exo') return selExoPlanet(k); if (m.kind === 'sstar') { const o = selSStar(k); if (m.prec) { const r0 = o.rows; o.rows = () => r0().concat([['Précession relativiste', 'son orbite tourne de 12 minutes d’arc à chaque tour, comme le prévoit la relativité générale (mesure GRAVITY, 2020)']]); } return o; } if (m.kind === 'probe') return selProbe(k);
    const per = TAU / m.nr, a = m.aAU, b = a * Math.sqrt(1 - m.e * m.e), cen = () => cenOf(m.p), get = () => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]];
    return { name: m.n, exist: () => !m.off ? null : S.ty < -4.5e9 ? 'pas encore formée' : 'sort inconnu', sub: 'Lune de ' + PLN[m.p], get, orbit: { e: m.e, P: m.P.map(x => x * a), Q: m.Q.map(x => x * b), c: cen }, rows: () => { const c = cen(), p = get(), d = Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]);
      return [['Distance à ' + PLN[m.p], nf(Math.round(d / 1e5) * 100, 0) + NBSP + 'km'], ['Orbite', 'de ' + nf(Math.round(m.a * (1 - m.e) / 100) * 100, 0) + ' à ' + nf(Math.round(m.a * (1 + m.e) / 100) * 100, 0) + NBSP + 'km'], ['Un tour de sa planète', fmtDays(per)], ['Vitesse sur l’orbite', sig(TAU * m.a / (per * 86400), 3) + NBSP + 'km/s'], ['Diamètre', (m.small ? 'environ ' : '') + nf(m.d, m.d < 100 ? 1 : 0) + NBSP + 'km'], ['Excentricité', sig(m.e, 2)], ['Découverte', m.disc],
        ['La lumière de sa planète l’atteint en', fmtLight(d)], ['Suivi', 'position fiable à quelques degrés près pendant un an autour d’aujourd’hui ; au-delà, seule l’orbite reste juste']]; } }; }
  function selSStar(k) { const m = KO[k], a = m.aAU, b = a * Math.sqrt(1 - m.e * m.e), cen = () => cenOf('sgra'), get = () => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]], vm = TAU * a / m.per * 4.74047;
    return { name: 'Étoile ' + m.n, sub: 'Étoile en orbite autour du trou noir central de la Voie lactée', get, orbit: { e: m.e, P: m.P.map(x => x * a), Q: m.Q.map(x => x * b), c: cen }, rows: () => { const c = cen(), p = get(), d = Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]) / AU, yr = yearOf(F.jd), vp = vm * Math.sqrt((1 + m.e) / (1 - m.e));
      return [['Distance au trou noir', nf(Math.round(d), 0) + NBSP + 'UA'], ['Orbite', 'de ' + nf(Math.round(a * (1 - m.e)), 0) + ' à ' + nf(Math.round(a * (1 + m.e)), 0) + NBSP + 'UA'], ['Un tour du trou noir', sig(m.per, 3) + NBSP + 'ans'], ['Vitesse actuelle', nf(Math.round(vm * Math.sqrt(Math.max(2 * a / Math.max(d, 1e-9) - 1, 0)) / 10) * 10, 0) + NBSP + 'km/s'],
        ['Vitesse au plus près', nf(Math.round(vp / 10) * 10, 0) + NBSP + 'km/s, soit ' + sig(vp / 2997.92458, 2) + NBSP + '% de la vitesse de la lumière'], ['Prochain passage au plus près', 'en ' + Math.floor(m.tp + Math.ceil((yr - m.tp) / m.per) * m.per)], ['Excentricité', sig(m.e, 3)], ['Type', m.sp === 'e' ? 'étoile jeune et chaude' : m.sp === 'l' ? 'étoile âgée et froide' : 'non déterminé'], ['Éclat en infrarouge', 'magnitude ' + String(m.k).replace('.', ',')],
        ['Source', 'orbite ajustée sur 25 ans de mesures (Gillessen et al. 2017)']].concat(skyRow(p)); } }; }
  function selProbe(k) { const m = KO[k], get = () => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]], pth = () => { const xy = solveKO(m, F.jd), r0 = Math.hypot(xy[0], xy[1]), hOf = r => Math.acosh(Math.max((r / m.aAU + 1) / m.e, 1)), H0 = hOf(0.25 * r0), H1 = hOf(3 * r0), o = new Float32Array(257 * 3);
      for (let i = 0; i <= 256; i++) { const H = H0 + (H1 - H0) * i / 256, x = m.aAU * (m.e - Math.cosh(H)), y = m.aAU * Math.sqrt(m.e * m.e - 1) * Math.sinh(H); o[i * 3] = m.P[0] * x + m.Q[0] * y; o[i * 3 + 1] = m.P[1] * x + m.Q[1] * y; o[i * 3 + 2] = m.P[2] * x + m.Q[2] * y; } return o; };
    return { name: m.n, exist: () => m.off ? 'pas encore lancée' : null, sub: 'Sonde spatiale lancée en ' + m.launch + ', en route vers l’espace interstellaire', get, orbit: { pts: m.tab && F.jd < m.tab.jd1 ? tabPath(m) : pth(), c: () => [0, 0, 0] }, rows: () => { const p = get(), r = vlen(p) / AU, ea = bodyPosM('earth'), dE = Math.hypot(p[0] - ea[0], p[1] - ea[1], p[2] - ea[2]), v = m.tab && F.jd < m.tab.jd1 && m.tv ? m.tv : 29.7847 * Math.sqrt(2 / Math.max(r, 1e-6) + 1 / m.aAU);
      return m.off ? [['Suivi', (m.tab ? 'pas encore lancée à cette date' : 'trajectoire non reconstituée avant ' + m.from + ' (survols de planètes)')]] : [['Distance au Soleil', sig(r, 4) + NBSP + 'UA'], ['Distance à la Terre', sig(dE / AU, 4) + NBSP + 'UA'], ['Son signal radio met', fmtLight(dE)], ['Vitesse', sig(v, 3) + NBSP + 'km/s'], ['Elle s’éloigne chaque année de', sig(v * 0.210949, 3) + NBSP + 'UA'],
        ['Atteindra une année-lumière', 'dans ' + fmtYears(Math.max(63241 - r, 0) / (v * 0.210949)) + ' environ'], ['Suivi', 'trajectoire du JPL, valable depuis ' + m.from + ' (dernier survol de planète)']].concat(skyRow([p[0] - ea[0], p[1] - ea[1], p[2] - ea[2]])); } }; }
  { const P = Rr.BHS.pos, want = [['Cygnus X-1', 'Cygnus X-1'], ['Gaia BH1', 'Gaia BH1'], ['Gaia BH3', 'Gaia BH3'], ['V404 Cyg', 'V404 Cygni'], ['A0620-00', 'A0620-00']];
    DATA.BHS.names.forEach((n, i) => { const w = want.find(w => n.indexOf(w[0]) >= 0); if (!w) return; const p = [P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY], l = Math.log10(vlen(p)); addLabel('Trou noir ' + w[1], '', 3, l - 0.75, l + 0.85, () => p, { gate: () => Rr.bhsVis }); }); }
  for (const s of DATA.STAR_LABELS) { const sp = Rr.starPos, j = s.i * 3, l = Math.log10(s.d * LY), span = [1.45, 1.0, 0.6][s.p - 1]; addLabel(s.n, '', s.p, l - 0.72, l + span, () => [sp[j] * LY, sp[j + 1] * LY, sp[j + 2] * LY], { span, dyn: () => Math.log10(Math.max(Math.hypot(sp[j], sp[j + 1], sp[j + 2]), 0.02) * LY), gate: () => { const t = F.tMyr, st = Rr.star, f = st.fate[s.i]; return t < st.life[j] || ((f === 1 || f === 3) && t > st.life[j + 2] + F.flash) ? 0 : fadeOut(Math.abs(S.ty), 3e6, 1.5e7); } }); }
  for (const s of DATA.DEEP) { const p = [s.pos[0] * LY, s.pos[1] * LY, s.pos[2] * LY], l = Math.log10(vlen(p)); addLabel(s.n, '', s.p, l - 0.8, l + 1.0, () => p, { gate: () => fadeOut(Math.abs(S.ty), 3e6, 1.5e7) }); }
  const galPoint = (r, beta) => { const xy = galXY(r, beta), th = -oArm * (S.T1 + S.T2), c = Math.cos(th), s = Math.sin(th); return add3(F.gcRel, mulM(M, [c * xy[0] - s * xy[1], s * xy[0] + c * xy[1], 0]), KPC); };
  for (const A of ARMS) addLabel(A.name, 'region', 2, 20.3, 21.45, () => galPoint(armR(A, A.labelBeta * DEG), A.labelBeta * DEG), { gate: () => 1 - F.mergeK });
  addLabel('Bras d’Orion', 'region', 1.5, 19.75, 21.1, () => galPoint(8.26 * Math.exp(-(26 - 9) * DEG * Math.tan(11.4 * DEG)), 26 * DEG), { gate: () => 1 - F.mergeK });
  addLabel('Centre galactique', '', 1.2, 19.9, 21.6, () => F.gcRel);
  addLabel('Voie lactée', 'here', 0, 21.85, 23.55, () => F.gcRel);
  for (const c of G.lg.centers) { const g = c.g, l = Math.log10(Math.max(vlen(c.c), 20) * KPC); addLabel(g.n, '', g.p, g.p >= 5 ? Math.max(l - 0.3, 21.05) : l - 0.85, g.p >= 5 ? Math.max(l + 0.45, 21.6) : g.p === 4 ? l + 0.5 : g.p === 3 ? l + 0.75 : 23.85, () => add3(F.gcRel, c.c, KPC), { gate: () => (c.gone || (F.dyn && g.p >= 3) ? 0 : 1) }); }
  for (const f of DATA.FAR) { const l = Math.log10(f.d * MPC); addLabel(f.n, f.k === 'void' ? 'region' : '', f.p, l - 0.75, l + [1.25, 0.9, 0.65, 0.45][f.p - 1], () => add3(F.gcRel, f.pos, MPC * F.cos.a)); }
  addLabel('Groupe local', 'here', 0, 23.85, 25.45, () => F.gcRel);
  addLabel('Nous sommes ici', 'here', 0, 25.75, 27.2, () => F.gcRel);
  const upM = r => { const u = Rr.camera.up; return [F.gcRel[0] + u.x * r, F.gcRel[1] + u.y * r, F.gcRel[2] + u.z * r]; };
  const hzL = (text, rad, ok) => addLabel(text, 'hz', 1, 25.5, 27.2, () => upM(rad()), { center: true, gate: () => (S.opts.horizons && ok() ? 1 : 0) });
  hzL('Sphère de Hubble', () => F.cos.rHubble * MPC, () => isFinite(F.cos.rHubble) && F.cos.rHubble * MPC < 1.2 * F.R * F.aFac);
  hzL('Horizon des événements', () => F.cos.chiEH * MPC * F.cos.a, () => F.cos.chiEH !== null);
  addLabel('Limite de l’univers observable', 'hz', 0.8, 25.6, 27.2, () => upM(F.cos.chiPH * MPC * F.cos.a), { center: true, gate: () => (F.cos.chiPH !== null ? 1 : 0) });
  LB.sort((a, b) => a.prio - b.prio);
  const measureLabels = () => { for (const L of LB) L.w = L.el.offsetWidth; };
  measureLabels(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(measureLabels);
  const sc = [0, 0, 0], placed = [];
  let hudBox = { w: 0, h: 0, bar: 120 };
  function updateLabels() {
    const lr = S.logR, W = Rr.cssW, H = Rr.cssH; placed.length = 0;
    for (const b of BODIES) { const o = Rr.bodies[b.key]; o.screen = o.vis > 0.3 ? (Rr.project(o.pos, F, sc) ? [sc[0], sc[1]] : null) : null; }
    for (const L of LB) {
      let a = 0;
      if (L.dyn) { const l = L.dyn(); L.lo = l - 0.72; L.hi = l + L.span; }
      if (S.opts.labels && (lr > 3 || L.micro) && lr > L.lo - 0.3 && lr < L.hi + 0.3) a = fadeIn(lr, L.lo - 0.3, L.lo) * fadeOut(lr, L.hi, L.hi + 0.3) * (L.gate ? L.gate() : 1);
      if (a > 0.03) {
        const p = L.get(), q = p && isFinite(p[0]) ? (L.micro ? Rr.projectLocal(p, F, sc) : Rr.project(p, F, sc)) : null;
        if (!q) a = 0; else {
          const dx = L.center ? -L.w / 2 : L.body ? Math.min(Rr.bodies[L.body].px, 60) + 3 : 6, x = q[0] + dx, y = q[1] + (L.center ? -16 : 0);
          const x0 = x, x1 = x + L.w, y0 = y - 9, y1 = y + 9;
          let bad = x0 < 4 || x1 > W - 26 || y0 < 4 || y1 > H - hudBox.bar - 10 || (x0 < hudBox.w && y0 < hudBox.h);
          const hit = (a0, a1) => { if (a0 < 4 || a1 > W - 26 || (a0 < hudBox.w && y0 < hudBox.h)) return true; for (const b of placed) if (a0 < b[1] && a1 > b[0] && y0 < b[3] && y1 > b[2]) return true; return false; };
          let xx = x; if (!bad && hit(x0, x1)) { const xl = q[0] - dx - L.w; if (!L.center && !hit(xl, xl + L.w)) xx = xl; else bad = true; }
          if (bad) a = 0; else { placed.push([xx, xx + L.w, y0, y1, L]); L.el.style.transform = 'translate(' + xx.toFixed(1) + 'px,' + (y - 11).toFixed(1) + 'px)'; }
        }
      }
      a = a > 0.03 ? Math.round(a * 20) / 20 : 0;
      if (a !== L.a) { L.a = a; L.el.style.opacity = a; L.el.style.visibility = a ? 'visible' : 'hidden'; }
    }
  }

  /* ---- règle des échelles ---- */
  const rail = $('rail'), RAILK = 0.34, railF = l => l >= LMIN ? RAILK + (1 - RAILK) * (l - LMIN) / (LMAX - LMIN) : RAILK * (l - LMICRO) / (LMIN - LMICRO), railL = f => f >= RAILK ? LMIN + (f - RAILK) / (1 - RAILK) * (LMAX - LMIN) : LMICRO + f / RAILK * (LMIN - LMICRO), SUP = '⁰¹²³⁴⁵⁶⁷⁸⁹';
  for (let d = Math.ceil(LMICRO); d <= 26; d++) { if (d < 7 && d % 5 !== 0) continue; const t = document.createElement('div'); t.className = 'tick'; t.style.bottom = railF(d) * 100 + '%'; if (d >= 7 ? d % 3 === 0 : d % 10 === 0) { t.style.width = '13px'; t.innerHTML = '<b>10' + (d < 0 ? '⁻' : '') + String(Math.abs(d)).split('').map(c => SUP[+c]).join('') + ' m</b>'; } $('ticks').appendChild(t); }
  const stopEls = STOPS.map(st => { const b = document.createElement('button'); b.className = 'stop'; b.type = 'button'; b.style.bottom = railF(st.logR) * 100 + '%'; b.innerHTML = '<span></span>'; b.firstChild.textContent = st.name; b.setAttribute('aria-label', 'Aller à : ' + st.name); b.addEventListener('click', () => { goStop(st); showRail(); }); rail.insertBefore(b, $('rail-hit')); return b; });
  let railTimer = 0;
  const showRail = () => { rail.classList.add('show'); clearTimeout(railTimer); railTimer = setTimeout(() => rail.classList.remove('show'), 3200); };
  { const hit = $('rail-hit'); let down = false;
    const at = e => { const r = rail.getBoundingClientRect(); S.anim = null; S.logR = clampZoom(railL(1 - (e.clientY - r.top) / r.height)); showRail(); };
    hit.addEventListener('pointerdown', e => { down = true; hit.setPointerCapture(e.pointerId); at(e); });
    hit.addEventListener('pointermove', e => { if (down) at(e); });
    const up = () => { down = false; }; hit.addEventListener('pointerup', up); hit.addEventListener('pointercancel', up); }

  /* ---- commandes sur la scène ---- */
  /* R3 : sans objet touché, la molette vise le point sous le curseur et le pincement le milieu des doigts. Ce point W (m, repère du Soleil)
     reste fixe à l'écran : la cible de la caméra glisse de (W − cible)(1 − k), k étant le rapport d'échelle. W est l'objet sous le point
     s'il y en a un à 8 px près (planète, étoile, galaxie… même recherche que le toucher), sinon le point du plan de visée. Le décalage
     (S.zoff) s'annule, en glissant, sur « Accueil », un arrêt de la barre, ou quand on touche un objet. */
  let zAnc = null;
  function zoffReset() { zAnc = null; if (!S.zoff) return; S.zoff = null; if (S.lastTg) S.cbl = { from: S.lastTg, t0: performance.now() / 1000 }; }
  function anchorAt(x, y) { const now = performance.now();
    if (zAnc && now - zAnc.t < 400 && Math.hypot(x - zAnc.x, y - zAnc.y) < 3) { zAnc.t = now; return zAnc.W; }      /* même geste : même point */
    let W = null; const sc = [0, 0, 0];
    for (const b of BODIES) { const o = Rr.bodies[b.key]; if (o.screen && Math.hypot(o.screen[0] - x, o.screen[1] - y) < Math.min(o.px, 200) + 6) { W = bodyPosM(b.key); break; } }
    if (!W) { const p = pickAt(x, y, true); if (p && Rr.project(p, F, sc) && Math.hypot(sc[0] - x, sc[1] - y) < 8) W = p; }
    if (!W) { const c = Rr.camPos, v = new THREE.Vector3(x / Rr.cssW * 2 - 1, 1 - y / Rr.cssH * 2, 0.5).unproject(Rr.camera), dir = v.sub(c).normalize(), n = c.clone().normalize(), dn = dir.dot(n);
      if (Math.abs(dn) < 1e-6) return null; const t = -c.dot(n) / dn; W = [(c.x + t * dir.x) / F.s + F.tg[0], (c.y + t * dir.y) / F.s + F.tg[1], (c.z + t * dir.z) / F.s + F.tg[2]]; }
    zAnc = { x, y, t: now, W }; return W; }
  function zoomAt(dl, x, y) { const l0 = S.logR, l1 = clampZoom(l0 + dl); S.anim = null; S.logR = l1;
    if (S.center || microOn() || (S.focus !== 'sun' && l0 < 14.4) || !(l1 !== l0) || !F.s) return;      /* objet touché ou astre suivi : le zoom reste centré sur lui (R1) */
    const W = anchorAt(x, y); if (!W || !isFinite(W[0])) return; const k = Math.pow(10, l1 - l0), z = S.zoff || [0, 0, 0];
    for (let i = 0; i < 3; i++) { const dz = (W[i] - F.tg[i]) * (1 - k); z[i] += dz; F.tg[i] += dz; } S.zoff = z; F.s /= k; }      /* F.tg et F.s suivent tout de suite : plusieurs crans dans la même image restent justes */
  { const ptrs = new Map(); let pinch = 0, moved = 0, t0 = 0, lastTap = [0, 0, 0];
    const dist = () => { const p = [...ptrs.values()]; return Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]); };
    canvas.addEventListener('pointerdown', e => { canvas.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); if (ptrs.size === 1) { moved = 0; t0 = performance.now(); } else { moved = 99; pinch = dist(); } canvas.classList.add('drag'); });
    canvas.addEventListener('pointermove', e => {
      const p = ptrs.get(e.pointerId); if (!p) return;
      const dx = e.clientX - p[0], dy = e.clientY - p[1]; p[0] = e.clientX; p[1] = e.clientY;
      if (ptrs.size === 1) { moved += Math.abs(dx) + Math.abs(dy); if (moved > 5) { if (S.anim) { S.anim.a0 = S.anim.a1 = S.az; S.anim.e0 = S.anim.e1 = S.el; } S.az -= dx * 0.0055; S.el = clamp(S.el + dy * 0.0055, -1.52, 1.52); if (S.anim) { S.anim.a0 = S.anim.a1 = S.az; S.anim.e0 = S.anim.e1 = S.el; } } }
      else if (ptrs.size === 2) { const d = dist(), q = [...ptrs.values()]; if (pinch > 0 && d > 0) zoomAt(-Math.log10(d / pinch) * 1.15, (q[0][0] + q[1][0]) / 2, (q[0][1] + q[1][1]) / 2); pinch = d; }      /* R3 : pincement vers le milieu des deux doigts */
    });
    const up = e => { if (!ptrs.has(e.pointerId)) return; ptrs.delete(e.pointerId); if (ptrs.size === 0) { canvas.classList.remove('drag'); if (e.type === 'pointerup' && moved < 6 && performance.now() - t0 < 450) tap(e.clientX, e.clientY); } pinch = 0; };
    canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
    canvas.addEventListener('wheel', e => { e.preventDefault(); zoomAt(e.deltaY * (e.deltaMode === 1 ? 0.035 : e.ctrlKey ? 0.006 : 0.0013) * (S.logR < -19.5 ? 3 : S.logR < 2.5 ? 1.6 : 1), e.clientX, e.clientY); /* l'infiniment petit couvre 26 puissances de dix : la molette y va plus vite */ }, { passive: false });
    function labelAt(x, y) { for (const b of placed) if (b[4] && x >= b[0] - 5 && x <= b[1] + 5 && y >= b[2] - 5 && y <= b[3] + 5) { const L = b[4]; if (L.micro) return null; if (L.body) return { body: L.body }; const p = L.get(), q = [0, 0, 0]; if (p && isFinite(p[0]) && Rr.project(p, F, q)) return { x: q[0], y: q[1] }; } return null; }
    S._tap = (x, y) => tap(x, y);
    function tap(x, y) { const now = performance.now(), dbl = now - lastTap[0] < 380 && Math.hypot(x - lastTap[1], y - lastTap[2]) < 26; lastTap = [now, x, y]; let best = null, bd = 30; for (const b of BODIES) { const o = Rr.bodies[b.key]; if (!o.screen) continue; const d = Math.hypot(o.screen[0] - x, o.screen[1] - y) - Math.min(o.px, 200); if (d < bd) { bd = d; best = b.key; } } if (best) { select(null); if (best !== S.focus) focusBody(best); return; }
      const hl = labelAt(x, y); if (hl && hl.body) { select(null); if (hl.body !== S.focus) focusBody(hl.body); return; }      // toucher un nom revient à toucher l'objet
      const o = hl ? pickAt(hl.x, hl.y) : pickAt(x, y); select(o); centerOn(o); if (o && dbl) goThere(o); }      /* toucher : l'objet devient le centre du zoom, sans changer l'échelle ; deux fois de suite : on y va */
    window.addEventListener('keydown', e => {
      if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
      if (e.key === ' ') { if (e.target && e.target.tagName === 'BUTTON') return; e.preventDefault(); S.playing = !S.playing; syncPlay(); }
      else if (e.key === '+' || e.key === '=') { S.anim = null; S.logR = clampZoom(S.logR - 0.15); }
      else if (e.key === '-') { S.anim = null; S.logR = clampZoom(S.logR + 0.15); }
      else if (e.key === 'ArrowLeft') S.az += 0.08; else if (e.key === 'ArrowRight') S.az -= 0.08;
      else if (e.key === 'ArrowUp') S.el = clamp(S.el + 0.06, -1.52, 1.52); else if (e.key === 'ArrowDown') S.el = clamp(S.el - 0.06, -1.52, 1.52);
      else if (e.key === 'Escape') openPanel(null);
      else if (e.key === '[') evStep(-1); else if (e.key === ']') evStep(1); else if (e.key === 'Backspace') { e.preventDefault(); goBack(); } else if (e.key === 'Home') goHome(); else if (e.key === 'PageUp') stepZoom(1); else if (e.key === 'PageDown') stepZoom(-1);
    });
  }

  /* ---- barre du temps ---- */
  $('b-play').addEventListener('click', () => { S.playing = !S.playing; S.hit = null; syncPlay(); });
  $('b-dir').addEventListener('click', () => { S.dir = -S.dir; S.hit = null; $('b-dir').setAttribute('aria-pressed', S.dir < 0); if (!S.playing) { S.playing = true; syncPlay(); } });
  $('speed').addEventListener('input', e => setSpeed(Math.pow(10, e.target.value / 1000 * SPEED_MAX_LOG)));
  $('b-now').addEventListener('click', () => { S.ty = 0; S.lastTy = 0; S.T1 = S.T2 = 0; S.beltYears = 0; S.hit = null; });
  $('card-back').addEventListener('click', () => { select(null); goStop(STOPS[1]); });
  $('card-close').addEventListener('click', () => select(null));
  $('card-center').addEventListener('click', () => goThere(S.sel));      /* « Y aller » : l'objet est déjà le centre, le bouton règle l'échelle */
  const panels = { chrono: [$('p-chrono'), $('b-chrono')], cosmo: [$('p-cosmo'), $('b-cosmo')], view: [$('p-view'), $('b-view')], about: [$('p-about'), $('b-about')], find: [$('p-find'), $('b-find')] };
  let openKey = null;
  function openPanel(k) { openKey = openKey === k ? null : k; for (const n in panels) { const on = n === openKey; panels[n][0].hidden = !on; panels[n][1].setAttribute('aria-expanded', on); } if (openKey === 'cosmo') { drawChart(); drawRot(); refreshCosmo(); } if (openKey === 'chrono') evScroll(); }
  for (const n in panels) { panels[n][1].addEventListener('click', () => openPanel(n)); panels[n][0].querySelector('[data-close]').addEventListener('click', () => openPanel(null)); }
  const bind = (id, key, fn) => $(id).addEventListener('change', e => { S.opts[key] = e.target.checked; if (fn) fn(); });
  bind('c-lab', 'labels'); bind('c-orb', 'orbits'); bind('c-real', 'realSize'); bind('c-hz', 'horizons'); bind('c-com', 'comoving'); bind('c-lc', 'lightcone', () => { lcOn = !!S.opts.lightcone; surveyDirty = true; }); bind('c-dm', 'dm', () => drawRot());
  { let busy = false;
    $('c-sim').addEventListener('change', async e => {
      const box = e.target;
      if (box.checked && !G.web && !busy) { busy = true; box.disabled = true;
        G.web = await genWeb(Q.web, Q.modes, 31, f => { $('sim-msg').textContent = 'Génération de la toile : ' + Math.round(f * 100) + NBSP + '%'; });
        G.far = genFar(Q.far, 32); Rr.addSim(G.web, G.far); $('sim-msg').textContent = ''; box.disabled = false; busy = false; }
      S.opts.simWeb = box.checked;
    }); }
  $('c-lite').addEventListener('change', e => { S.lite = e.target.checked; resize(); });
  $('n-stars').textContent = nf(starTotal(), 0); $('n-bodies').textContent = nf(DATA.AST_N + DATA.TNO_N, 0); $('n-comets').textContent = nf(DATA.COM_N, 0); $('n-bh').textContent = nf(DATA.BHS.n + DATA.BHM.n + 1, 0); $('n-exo').textContent = nf(DATA.EXO_N, 0); $('n-psr').textContent = nf(DATA.PSR_N, 0); $('n-clusters').textContent = nf(DATA.CLUSTERS_N[0] + DATA.CLUSTERS_N[1], 0); $('n-near').textContent = nf(DATA.LOCAL.length + DATA.NEAR_N, 0); $('n-surv').textContent = nf(DATA.SURV_N[0] + DATA.SURV_N[1] + DATA.SURV_N[2], 0);

  /* ---- cosmologie : curseurs, courbes, lectures ---- */
  const PRESETS = [['Notre univers', PLANCK], ['Sans énergie noire', { H0: 67.4, Om: 0.315, OL: 0, w: -1 }], ['Matière seule', { H0: 67.4, Om: 1, OL: 0, w: -1 }], ['Big Crunch', { H0: 67.4, Om: 3, OL: 0, w: -1 }], ['Big Rip', { H0: 67.4, Om: 0.315, OL: 0.685, w: -1.5 }]];
  const SL = [['s-om', 'o-om', 'Om', v => nf(v, 3)], ['s-ol', 'o-ol', 'OL', v => nf(v, 3)], ['s-h0', 'o-h0', 'H0', v => nf(v, 1) + NBSP + 'km/s/Mpc'], ['s-w', 'o-w', 'w', v => nf(v, 2).replace('-', '−')]];
  function syncSliders() { for (const s of SL) { $(s[0]).value = S.par[s[2]]; $(s[1]).textContent = s[3](S.par[s[2]]); } const w = S.par.w; $('w-hint').textContent = Math.abs(w + 1) < 0.005 ? 'À −1, c’est la constante cosmologique : sa densité ne change jamais.' : w < -1 ? 'Sous −1, l’énergie noire se renforce avec le temps et finit par tout déchirer.' : 'Au-dessus de −1, l’énergie noire se dilue lentement.'; }
  function rebuild() { S.cosmo = buildCosmo(S.par); surveyDirty = true; orbitDirty = true; S.hit = setTime(S.ty); syncSliders(); if (openKey === 'cosmo') { drawChart(); refreshCosmo(); } }
  for (const s of SL) $(s[0]).addEventListener('input', e => { S.par[s[2]] = +e.target.value; rebuild(); });
  for (const p of PRESETS) { const b = document.createElement('button'); b.className = 'btn'; b.type = 'button'; b.textContent = p[0]; b.addEventListener('click', () => { S.par = Object.assign({}, p[1]); rebuild(); }); $('presets').appendChild(b); }
  const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const GLY = 1 / 306.6013938;                       // 1 Mpc en milliards d'années-lumière
  let chartDom = null;
  function drawChart() {
    const cv = $('chart'), ctx = cv.getContext('2d'), W = cv.width, H = cv.height, C = S.cosmo, ink = cssVar('--ink'), dim = cssVar('--ink-dim'), line = cssVar('--line'), curve = cssVar('--curve'), warm = cssVar('--warm');
    const t0 = C.tBang !== null ? C.tBang : Math.max(C.tStart, -40);
    let t1 = Math.min(C.tEnd, 70), top = 0;
    for (let i = 0; i < C.n; i++) if (C.t[i] > 0 && C.a[i] > 4.2) { t1 = Math.min(t1, C.t[i]); break; }
    t1 = Math.max(t1, Math.min(C.tEnd, 8));
    for (let i = 0; i < C.n; i++) if (C.t[i] >= t0 && C.t[i] <= t1) top = Math.max(top, C.a[i]);
    top = Math.max(top * 1.1, 1.4);
    const L = 14, Rg = 14, T = 30, B = 44, X = t => L + (t - t0) / (t1 - t0) * (W - L - Rg), Y = a => H - B - a / top * (H - T - B);
    chartDom = { t0, t1, L, Rg, W };
    ctx.clearRect(0, 0, W, H); ctx.lineWidth = 2; ctx.font = '500 21px Jost, sans-serif'; ctx.textBaseline = 'alphabetic';
    ctx.strokeStyle = line; ctx.beginPath(); ctx.moveTo(L, Y(0)); ctx.lineTo(W - Rg, Y(0)); ctx.moveTo(L, Y(1)); ctx.lineTo(W - Rg, Y(1)); ctx.stroke();
    ctx.fillStyle = dim; ctx.textAlign = 'left'; ctx.fillText('taille actuelle', L + 4, Y(1) - 8);
    ctx.textAlign = 'center';
    for (let g = Math.ceil(t0 / 10) * 10; g <= t1; g += 10) { if (Math.abs(g) < 1) continue; const x = X(g); ctx.strokeStyle = line; ctx.beginPath(); ctx.moveTo(x, Y(0)); ctx.lineTo(x, Y(0) + 8); ctx.stroke(); ctx.fillText((g > 0 ? '+' : '−') + Math.abs(g), x, Y(0) + 30); }
    ctx.strokeStyle = dim; ctx.setLineDash([5, 6]); ctx.beginPath(); ctx.moveTo(X(0), T - 8); ctx.lineTo(X(0), Y(0) + 8); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = ink; ctx.textAlign = X(0) > W * 0.8 ? 'right' : 'center'; ctx.fillText('aujourd’hui', X(0), Y(0) + 30);
    ctx.fillStyle = dim; ctx.textAlign = 'left'; if (C.tBang !== null && X(0) - L > 150) ctx.fillText('Big Bang', L, Y(0) + 30);
    ctx.textAlign = 'right'; ctx.fillText(C.endKind === 'crunch' && t1 >= C.tEnd - 0.5 ? 'Big Crunch' : C.endKind === 'rip' && t1 >= C.tEnd - 0.5 ? 'Big Rip' : 'milliards d’années', W - Rg, T - 8);
    ctx.strokeStyle = curve; ctx.lineWidth = 4; ctx.lineJoin = 'round'; ctx.beginPath(); let first = true;
    if (C.tBang !== null) { ctx.moveTo(X(C.tBang), Y(0)); first = false; }
    for (let i = 0; i < C.n; i++) { const t = C.t[i]; if (t < t0 || t > t1) continue; const x = X(t), y = Y(C.a[i]); if (first) { ctx.moveTo(x, y); first = false; } else ctx.lineTo(x, y); }
    ctx.stroke();
    const tn = clamp(S.ty / 1e9, t0, t1), an = F.cos.a === undefined ? 1 : F.cos.a, xn = X(tn), yn = Y(Math.min(an, top));
    ctx.strokeStyle = warm; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(xn, T - 8); ctx.lineTo(xn, Y(0)); ctx.stroke();
    ctx.fillStyle = warm; ctx.beginPath(); ctx.arc(xn, yn, 8, 0, TAU); ctx.fill();
  }
  { const cv = $('chart'); let down = false;
    const at = e => { if (!chartDom) return; const r = cv.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * chartDom.W, t = chartDom.t0 + clamp((x - chartDom.L) / (chartDom.W - chartDom.L - chartDom.Rg), 0, 1) * (chartDom.t1 - chartDom.t0); S.hit = null; setTime(t * 1e9); S.lastTy = S.ty; };
    cv.addEventListener('pointerdown', e => { down = scrubbing = true; cv.setPointerCapture(e.pointerId); at(e); });
    cv.addEventListener('pointermove', e => { if (down) at(e); });
    const up = () => { down = scrubbing = false; }; cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up); }
  function drawRot() {
    const cv = $('rot'), ctx = cv.getContext('2d'), W = cv.width, H = cv.height, ink = cssVar('--ink'), dim = cssVar('--ink-dim'), line = cssVar('--line'), curve = cssVar('--curve'), warm = cssVar('--warm');
    const L = 14, Rg = 14, T = 26, B = 40, X = r => L + r / 26 * (W - L - Rg), Y = v => H - B - v / 270 * (H - T - B);
    ctx.clearRect(0, 0, W, H); ctx.font = '500 21px Jost, sans-serif'; ctx.lineWidth = 2;
    ctx.strokeStyle = line; ctx.beginPath(); ctx.moveTo(L, Y(0)); ctx.lineTo(W - Rg, Y(0)); ctx.stroke();
    ctx.fillStyle = dim; ctx.textAlign = 'center'; for (const r of [5, 10, 15, 20, 25]) ctx.fillText(String(Math.round(r * 3.2616)), X(r), Y(0) + 28);
    ctx.textAlign = 'right'; ctx.fillText('km/s', W - Rg, T - 4);
    const plot = (dm, col, wd) => { ctx.strokeStyle = col; ctx.lineWidth = wd; ctx.beginPath(); for (let r = 0.3; r <= 26; r += 0.25) { const x = X(r), y = Y(vCirc(r, dm)); if (r === 0.3) ctx.moveTo(x, y); else ctx.lineTo(x, y); } ctx.stroke(); };
    plot(false, S.opts.dm ? dim : warm, S.opts.dm ? 2 : 5); plot(true, S.opts.dm ? curve : dim, S.opts.dm ? 5 : 2);
    ctx.fillStyle = ink; ctx.textAlign = 'left'; ctx.fillText('avec halo', X(17), Y(vCirc(17, true)) - 12); ctx.fillText('sans halo', X(17), Y(vCirc(17, false)) + 30);
    ctx.fillStyle = warm; ctx.beginPath(); ctx.arc(X(GAL.R0), Y(vCirc(GAL.R0, S.opts.dm)), 8, 0, TAU); ctx.fill(); ctx.textAlign = 'center'; ctx.fillStyle = ink; ctx.fillText('Soleil', X(GAL.R0), Y(vCirc(GAL.R0, true)) - 18);
  }
  const FB = BARYON_H2 / (PLANCK.H0 / 100) ** 2 / PLANCK.Om;      // part de matière ordinaire dans la matière
  function refreshCosmo() {
    const C = S.cosmo, c = F.cos; if (c.a === undefined) return;
    const rows = [
      ['Âge de l’univers aujourd’hui', C.age !== null ? fmtYears(C.age * 1e9) : 'pas de Big Bang'],
      ['Distances, par rapport à aujourd’hui', '×' + NNBSP + sig(c.a, 3)],
      ['Vitesse d’expansion', sig(c.Hkms, 3) + NBSP + 'km/s/Mpc'],
      ['L’expansion', c.H < 0 ? 's’est inversée' : c.q < 0 ? 'accélère' : 'ralentit'],
      ['Géométrie de l’espace', C.Ok > 0.005 ? 'ouverte' : C.Ok < -0.005 ? 'fermée' : 'plate'],
      ['Univers observable, rayon', c.chiPH !== null ? sig(c.chiPH * c.a * GLY, 3) + NBSP + 'milliards d’al' : 'non défini'],
      ['Destin', C.endKind === 'crunch' ? 'Big Crunch dans ' + fmtYears(C.tEnd * 1e9) : C.endKind === 'rip' ? 'Big Rip dans ' + fmtYears(C.tEnd * 1e9) : C.accelEnd ? 'expansion sans fin, toujours plus rapide' : 'expansion sans fin, toujours plus lente'],
    ];
    $('readout').innerHTML = rows.map(r => '<dt>' + r[0] + '</dt><dd>' + r[1] + '</dd>').join('');
    const parts = [['Rayonnement', c.fr, 'var(--amber)'], ['Matière ordinaire', c.fm * FB, 'var(--ice)'], ['Matière noire', c.fm * (1 - FB), 'var(--indigo)'], ['Énergie noire', c.fde, 'var(--orchid)']];
    $('compo').innerHTML = parts.map(p => '<i style="width:' + (p[1] * 100).toFixed(2) + '%;background:' + p[2] + '"></i>').join('');
    $('compo-leg').innerHTML = parts.map(p => '<li style="--c:' + p[2] + '">' + p[0] + ' ' + (p[1] < 0.001 && p[1] > 0 ? '<' + NNBSP + '0,1' : nf(p[1] * 100, 1)) + NBSP + '%</li>').join('');
  }

  /* ---- tout est cliquable : recherche de l'objet le plus proche du doigt, parmi tout ce qui est visible ---- */
  const PM = new THREE.Matrix4(), pe = PM.elements, split = k => DATA[k].split('|');
  const NM = { AST: split('AST_NAMES'), TNO: split('TNO_NAMES'), clu: split('CLUSTER_NAMES'), near: split('NEAR_NAMES') }, CLSB = { AST: b64ToBytes(DATA.AST_CLS), TNO: b64ToBytes(DATA.TNO_CLS) }, CAGE = b64ToBytes(DATA.CLUSTER_AGE);
  const CLS_FR = ['Astéroïde de la ceinture principale', 'Astéroïde de la ceinture externe', 'Astéroïde de la ceinture interne', 'Astéroïde qui croise l’orbite de Mars', 'Astéroïde troyen de Jupiter', 'Objet transneptunien', 'Centaure', 'Astéroïde géocroiseur', 'Astéroïde géocroiseur', 'Astéroïde géocroiseur'];
  const KNOWN_D = { 'Pluton': 2377, 'Éris': 2326, 'Hauméa': 1560, 'Makémaké': 1430, 'Sedna': 1000, 'Gonggong': 1230, 'Quaoar': 1090, 'Orcus': 910, 'Cérès': 940, 'Vesta': 525, 'Pallas': 512, 'Hygie': 434 };
  const fmtTimes = x => x >= 1e9 ? sig(x / 1e9, 2) + NBSP + 'milliards de fois' : x >= 1e6 ? sig(x / 1e6, 2) + NBSP + 'millions de fois' : x >= 100 ? nf(Number(x.toPrecision(2)), 0) + NBSP + 'fois' : sig(x, 2) + NBSP + 'fois';
  const inTime = y => (y >= 0 ? 'dans ' : 'il y a ') + fmtYears(Math.abs(y));
  function lookbackGyr(z) { const C = S.cosmo, a = 1 / (1 + z); let hi = 0; while (hi < C.n - 1 && C.t[hi + 1] <= 1e-9) hi++; let lo = hi; while (lo > 0 && C.a[lo - 1] < C.a[lo] && C.a[lo] > a) lo--; if (C.a[lo] > a) return -C.t[lo]; const f = (a - C.a[lo]) / Math.max(C.a[lo + 1] - C.a[lo], 1e-12); return -(C.t[lo] + clamp(f, 0, 1) * (C.t[lo + 1] - C.t[lo])); }
  /* état d'une étoile à la date affichée selon starLife : un modèle statistique (place dans la vie tirée au hasard), pas une prédiction étoile par étoile ; le repère le dit. Même règle que l'affichage des points */
  function starState(L, fate) { const t = F.tMyr; if (t < L[0]) return 'pas encore née d’après un modèle statistique (âge réel inconnu)'; if ((fate === 1 || fate === 3) && t > L[2] + F.flash) return 'explosée d’après un modèle statistique (âge réel inconnu)'; return null; }
  /* S5 : extinction par la poussière mesurée (Edenhofer et al. 2024), vue de la Terre et vue d'ici */
  function dustRow(P, i) { const s = eclLyToGalPc([P[i * 3], P[i * 3 + 1], P[i * 3 + 2]]), cl = Rr.dustU.uCamLy.value, pr = dustPair(eclLyToGalPc([cl.x, cl.y, cl.z]), s), x = a => a < 0.05 ? 'presque pas atténuée' : sig(Math.pow(10, 0.4 * a), 2) + ' fois moins lumineuse';
    return 'vue de la Terre : ' + x(pr[1]) + (Rr.dustOn ? ' ; vue d’ici : ' + x(pr[0]) + ', son éclat en tient compte' : '') + (Math.hypot(...s) > DATA.DUST.rmax ? ' ; au-delà de la carte (1,25 kpc), poussière inconnue' : '') + ' (carte 3D mesurée, Edenhofer et al. 2024)'; }
  function selStar(i) {
    const st = Rr.star, sp = Rr.starPos, hip = st.hip[i], MV = st.mag[i], bv = st.bv[i], L = [st.life[i * 3], st.life[i * 3 + 1], st.life[i * 3 + 2]], fate = st.fate[i];
    const get = () => [sp[i * 3] * LY, sp[i * 3 + 1] * LY, sp[i * 3 + 2] * LY]; if (!Rr.keyStars.includes(i)) Rr.keyStars.push(i);
    return { exoI: STAREXO[i] >= 0 ? STAREXO[i] : undefined, exoC: true, lr: STAREXO[i] >= 0 ? exoLr(STAREXO[i]) : undefined, name: DATA.STAR_NAMES[i] || (hip ? 'HIP ' + hip : 'Étoile sans nom'), exist: () => starState(L, fate), sub: 'Étoile ' + STAR_CLASS[st.cls[i]] + ', type ' + bvSpectral(bv), get, rows: () => {
      const d = vlen(get()), t = F.tMyr, sn = fate === 1 || fate === 3, lum = Math.pow(10, 0.4 * (4.83 - MV));
      const fut = fate === 4 || (!sn && t >= L[2]) ? 'naine blanche qui refroidit' : sn && t >= L[2] ? 'a explosé en supernova' : sn ? 'supernova ' + inTime((L[2] - t) * 1e6) : t < L[1] ? 'géante rouge ' + inTime((L[1] - t) * 1e6) + ', puis naine blanche' : 'naine blanche ' + inTime((L[2] - t) * 1e6);
      return [['Distance', fmtDist(d)], ['Éclat', fmtTimes(lum) + ' le Soleil'], ['Température', nf(Math.round(bvTemp(bv) / 50) * 50, 0) + NBSP + 'K'], ['Masse estimée', sig(st.mass[i], 2) + NBSP + 'fois le Soleil'], ['Vitesse', Rr.K.vkms[i] > 0 ? sig(Rr.K.vkms[i], 3) + NBSP + 'km/s par rapport au Soleil' : 'non mesurée'], ['Mouvement', orbMotionText(Rr.K, i, F.tEff, false)], ['Poussière devant elle', dustRow(Rr.starPos, i)], ['Avenir estimé', fut]].concat(passRows(i), starExtra(get(), kvOf(Rr.K, i), MV, bv), STAREXO[i] >= 0 ? [['Planètes connues', EXOP[STAREXO[i]] + ' : « Y aller » pour les voir tourner autour de l’étoile']].concat(exoRows(STAREXO[i])) : []); } };
  }
  function selBody(tag, i) {
    const B = Rr[tag], raw = NM[tag][i] || '', parts = raw.split('~'), nm = parts[0] ? parts[0] + (parts[1] ? ' (' + parts[1] + ')' : '') : (parts[1] ? 'Astéroïde ' + parts[1] : 'Objet sans nom');
    const get = () => [B.pos[i * 3] * AU * F.orb, B.pos[i * 3 + 1] * AU * F.orb, B.pos[i * 3 + 2] * AU * F.orb], a = B.a[i], e = B.e[i], kd = KNOWN_D[parts[0]];
    const dia = kd || 1329 / Math.sqrt(tag === 'AST' ? 0.14 : 0.08) * Math.pow(10, -B.H[i] / 5);
    return { name: nm, sub: (parts[0] === 'Pluton' || parts[0] === 'Éris' || parts[0] === 'Cérès' || parts[0] === 'Hauméa' || parts[0] === 'Makémaké' ? 'Planète naine' : CLS_FR[CLSB[tag][i]] || 'Petit corps'), get, orbit: { e, P: [B.P[i * 3], B.P[i * 3 + 1], B.P[i * 3 + 2]], Q: [B.Q[i * 3], B.Q[i * 3 + 1], B.Q[i * 3 + 2]] }, rows: () => [['Distance au Soleil', sig(vlen(get()) / AU, 4) + NBSP + 'UA'], ['Orbite', 'de ' + sig(a * (1 - e), 3) + ' à ' + sig(a * (1 + e), 3) + NBSP + 'UA'], ['Excentricité', sig(e, 3)], ['Inclinaison', sig(B.inc[i] / DEG, 3) + '°'], ['Un tour du Soleil', fmtYears(Math.pow(a, 1.5))], ['Vitesse actuelle', sig(orbSpeed(vlen(get()) / AU / (F.orb || 1), a), 3) + NBSP + 'km/s'], ['Diamètre', (kd ? '' : 'environ ') + nf(Math.round(dia / (dia > 100 ? 10 : 1)) * (dia > 100 ? 10 : 1), 0) + NBSP + 'km' + (kd ? '' : ' (estimé d’après l’éclat)')]] };
  }
  // ---- compléments de fiche : orbite, vitesse, décalage spectral, trous noirs
  const zStr = z => (z < 0 ? '−' : '+') + Math.abs(z).toFixed(Math.abs(z) < 0.001 ? 6 : 4).replace('.', ',');
  const orbSpeed = (r, a) => 29.7847 * Math.sqrt(Math.max(2 / Math.max(r, 1e-6) - 1 / a, 0));       // km/s, r et a en UA
  const passAU = pc => nf(Math.round(pc * 206265 / 100) * 100, 0) + NBSP + 'UA', passWhen = t => (Math.abs(t) >= 1e6 ? sig(Math.abs(t) / 1e6, 3) + ' million' + (Math.abs(t) >= 2e6 ? 's' : '') + ' d’années' : nf(Math.round(Math.abs(t) / 1000), 0) + NBSP + '000 ans');
  function passRows(i) { const o = (Rr.passers || []).find(q => q.idx === i); return o ? [['Au plus près du Soleil', (o.t < 0 ? 'il y a ' : 'dans ') + passWhen(o.t) + ', à ' + passAU(o.d) + ' (' + sig(o.d * 3.2616, 2) + ' année' + (o.d * 3.2616 >= 2 ? 's' : '') + '-lumière)'], ['Incertitude', 'entre ' + passAU(o.d5) + ' et ' + passAU(o.d95)], ['Source du passage', (o.src || 'Bailer-Jones 2022 (Gaia DR3)') + ' · Probable']] : []; }
  const kvOf = (K, i) => [K.ve[i * 3] / KMS_LY_YR, K.ve[i * 3 + 1] / KMS_LY_YR, K.ve[i * 3 + 2] / KMS_LY_YR];
  const raDec = p => { const e = 23.4392911 * DEG, x = p[0], y = p[1] * Math.cos(e) - p[2] * Math.sin(e), z = p[1] * Math.sin(e) + p[2] * Math.cos(e), rr = Math.hypot(x, y, z) || 1; let ra = Math.atan2(y, x) / DEG / 15; if (ra < 0) ra += 24;
    const de = Math.asin(z / rr) / DEG, h = Math.floor(ra), m = Math.floor((ra - h) * 60), ad = Math.abs(de), dd = Math.floor(ad), dm = Math.floor((ad - dd) * 60); return 'ascension droite ' + h + NBSP + 'h ' + (m < 10 ? '0' : '') + m + ', déclinaison ' + (de < 0 ? '−' : '+') + dd + '° ' + (dm < 10 ? '0' : '') + dm + '′'; };
  const CST = DATA.CONST, CM = DATA.CONST_M;      // limites des 88 constellations (Roman 1987), données pour l'équinoxe 1875
  const constOf = p => { const e = 23.4392911 * DEG, x = p[0], y = p[1] * Math.cos(e) - p[2] * Math.sin(e), z = p[1] * Math.sin(e) + p[2] * Math.cos(e), X = CM[0][0] * x + CM[0][1] * y + CM[0][2] * z, Y = CM[1][0] * x + CM[1][1] * y + CM[1][2] * z, Z = CM[2][0] * x + CM[2][1] * y + CM[2][2] * z; let ra = Math.atan2(Y, X) / DEG / 15; if (ra < 0) ra += 24;
    const de = Math.asin(Z / (Math.hypot(X, Y, Z) || 1)) / DEG; for (let i = 0; i < CST.ab.length; i++) if (de >= CST.de[i] && ra >= CST.lo[i] && ra < CST.hi[i]) return DATA.CONST_FR[CST.ab[i]] || CST.ab[i]; return ''; };
  const skyRow = p => { const c = constOf(p); return [['Position dans le ciel', raDec(p) + (c ? ', dans ' + c : '')]]; };
  const fmtLight = d => { const t = d / 299792458; return t < 120 ? sig(t, 3) + NBSP + 's' : t < 7200 ? sig(t / 60, 3) + NBSP + 'min' : t < 172800 ? sig(t / 3600, 3) + NBSP + 'h' : sig(t / 86400, 3) + NBSP + 'jours'; };
  const fmtSec = t => t < 1 ? sig(t * 1000, 3) + NBSP + 'millisecondes' : t < 120 ? sig(t, 3) + NBSP + 's' : t < 7200 ? sig(t / 60, 3) + NBSP + 'min' : t < 172800 ? sig(t / 3600, 3) + NBSP + 'heures' : sig(t / 86400, 3) + NBSP + 'jours';
  const sci = x => { const e = Math.floor(Math.log10(x)); return sig(x / Math.pow(10, e), 2) + ' × 10<sup>' + String(e).replace('-', '−') + '</sup>'; };
  // correction bolométrique (Flower 1996, coefficients de Torres 2010) : passe de l'éclat visible à l'éclat total, pour un rayon plus juste
  const bcV = T => { const x = Math.log10(clamp(T, 3300, 40000)); return x < 3.70 ? -0.190537291496456e5 + 0.155144866764412e5 * x - 0.421278819301717e4 * x * x + 0.381476328422343e3 * x * x * x : x < 3.90 ? -0.370510203809015e5 + 0.385672629965804e5 * x - 0.150651486316025e5 * x * x + 0.261724637119416e4 * x * x * x - 0.170623810323864e3 * x * x * x * x : -0.118115450538963e6 + 0.137145973583929e6 * x - 0.636233812100225e5 * x * x + 0.147412923562646e5 * x * x * x - 0.170587278406872e4 * x * x * x * x + 0.788731721804990e2 * x * x * x * x * x; };
  const starExtra = (p, v, MV, bv) => { const r = [], d = vlen(p), vr = (v[0] * p[0] + v[1] * p[1] + v[2] * p[2]) / Math.max(d, 1), M = DATA.M_GAL2ECL, w = [(p[0] - F.gcRel[0]) / KPC, (p[1] - F.gcRel[1]) / KPC, (p[2] - F.gcRel[2]) / KPC], vv = v[0] * v[0] + v[1] * v[1] + v[2] * v[2], dpc = d / LY / 3.2615638;
    if (MV !== undefined) { const m = MV + 5 * Math.log10(Math.max(dpc, 1e-9) / 10), L = Math.pow(10, 0.4 * (4.83 - MV));
      const T = bvTemp(bv), Lb = L * Math.pow(10, -0.4 * (bcV(T) - bcV(5772)));
      r.push(['Éclat toutes couleurs confondues', fmtTimes(Lb) + ' le Soleil'], ['Rayon estimé', sig(Math.sqrt(Lb) * Math.pow(5772 / T, 2), 2) + NBSP + 'fois le Soleil'], ['Vue de la Terre', 'magnitude ' + sig(m, 3).replace('-', '−') + (m < 6 ? ', visible à l’œil nu' : m < 9.5 ? ', visible aux jumelles' : ', visible au télescope')]); }
    if (Math.abs(vr) >= 0.5) r.push(['Vitesse radiale', (vr < 0 ? 'se rapproche' : 's’éloigne') + ' à ' + sig(Math.abs(vr), 3) + NBSP + 'km/s : décalage vers le ' + (vr < 0 ? 'bleu' : 'rouge') + ', z = ' + zStr(vr / 299792.458)]);
    if (vv > 0.01) { const mu = Math.sqrt(Math.max(vv - vr * vr, 0)) / (4.74047 * Math.max(dpc, 1e-9)), ts = -(p[0] * v[0] + p[1] * v[1] + p[2] * v[2]) / (vv * 1e3), ty = ts / 3.15576e7, dm = Math.hypot(p[0] + v[0] * 1e3 * ts, p[1] + v[1] * 1e3 * ts, p[2] + v[2] * 1e3 * ts);
      if (mu > 0.0005) r.push(['Déplacement dans le ciel', mu >= 0.1 ? sig(mu, 3) + NBSP + 'seconde d’arc par an' : sig(mu * 1000, 3) + NBSP + 'millièmes de seconde d’arc par an']);
      if (Math.abs(ty) > 200 && Math.abs(ty) < 3e6) r.push(['Au plus près du Soleil', (ty > 0 ? 'dans ' : 'il y a ') + fmtYears(Math.abs(ty)) + ', à ' + fmtDist(dm)]); }
    const Rg = Math.max(Math.hypot(M[0][0] * w[0] + M[1][0] * w[1] + M[2][0] * w[2], M[0][1] * w[0] + M[1][1] * w[1] + M[2][1] * w[2]), 0.3), yr = 2000 + (F.jd - 2451545) / 365.25 - d / LY;
    r.push(['Orbite dans la galaxie', 'à ' + fmtDist(Rg * KPC) + ' du centre, un tour en ' + fmtYears(TAU * Rg / (vCirc(Rg, true) * KMS_KPC_GYR) * 1e9) + ' environ']);
    if (Math.abs(S.ty) < 1e4) r.push(['La lumière qu’on en voit', yr > 0 ? 'est partie vers ' + Math.round(yr) : 'est partie il y a ' + fmtYears(d / LY)]);
    return r.concat(skyRow(p)); };
  // ---- fiches de référence de la NASA (planètes, Lune, Soleil)
  const FA = DATA.FACTS, hrs = h => { const a = Math.abs(h); return (a < 48 ? sig(a, 3) + NBSP + 'heures' : sig(a / 24, 3) + NBSP + 'jours') + (h < 0 ? ', dans le sens inverse des autres planètes' : ''); }, yn = v => v === 'Yes' ? 'oui' : v === 'No' ? 'non' : 'inconnu';
  const factRows = key => { const f = FA[key]; if (!f || f.mass === undefined) return [];
    const r = [['Diamètre à l’équateur', nf(f.diam, 0) + NBSP + 'km'], ['Masse', key === 'earth' ? '5,97 × 10<sup>24</sup> kg' : sig(f.mass / FA.earth.mass, 3) + NBSP + 'fois la Terre'], ['Densité', sig(f.dens / 1000, 3) + NBSP + 'fois celle de l’eau'], ['Pesanteur', sig(f.grav, 3) + NBSP + 'm/s²' + (key === 'earth' ? '' : ', soit ' + sig(f.grav / FA.earth.grav, 2) + NBSP + 'fois celle de la Terre')], ['Vitesse de libération', sig(f.esc, 3) + NBSP + 'km/s'],
      ['Rotation sur elle-même', hrs(f.rot)], ['Durée du jour', hrs(Math.abs(f.day))], ['Inclinaison de l’axe', sig(f.obl, 3) + '°'], ['Température moyenne', String(f.temp).replace('-', '−') + NBSP + '°C'], ['Pression au sol', typeof f.pres === 'number' ? (f.pres === 0 ? 'presque nulle' : sig(f.pres, 2) + NBSP + 'bar') : 'pas de sol : planète gazeuse']];
    if (key !== 'moon') r.push(['Lunes connues', nf(f.moons, 0)], ['Anneaux', yn(f.rings)]); r.push(['Champ magnétique global', yn(f.mag)]);
    if (key !== 'earth' && key !== 'moon') { const e = bodyPosM('earth'), p = bodyPosM(key), d = Math.hypot(p[0] - e[0], p[1] - e[1], p[2] - e[2]); r.push(['Distance à la Terre', sig(d / AU, 3) + NBSP + 'UA'], ['Sa lumière nous parvient en', fmtLight(d)]); } return r; };
  const sunFacts = () => { const f = DATA.SUNFACT; return [['Diamètre aujourd’hui', nf(f.rad * 2, 0) + NBSP + 'km, soit ' + sig(f.rad * 2 / FA.earth.diam, 3) + NBSP + 'fois la Terre'], ['Masse aujourd’hui', nf(Math.round(f.mass / FA.earth.mass / 1000) * 1000, 0) + NBSP + 'fois la Terre'], ['Type', 'étoile naine jaune, ' + f.sp], ['Température au centre', sig(f.tc / 1e6, 3) + NBSP + 'millions de K'],
    ['Puissance rayonnée', sig(f.lum / 100, 4) + ' × 10<sup>26</sup> W'], ['Pesanteur en surface', sig(f.grav / FA.earth.grav, 3) + NBSP + 'fois celle de la Terre'], ['Vitesse de libération', sig(f.esc, 4) + NBSP + 'km/s'], ['Rotation sur lui-même', sig(f.rot / 24, 3) + NBSP + 'jours à l’équateur'], ['Densité', sig(f.dens / 1000, 3) + NBSP + 'fois celle de l’eau'], ['Sa lumière atteint la Terre en', fmtLight(vlen(bodyPosM('earth')))]]; };
  // ---- petits corps et comètes : compléments calculés à partir de l'orbite
  const orbPlus = o => { const ob = o.orbit; if (!ob) return o; const rows = o.rows, a = Math.hypot(ob.P[0], ob.P[1], ob.P[2]), e = ob.e, b2 = ob.Q[0] * ob.Q[0] + ob.Q[1] * ob.Q[1] + ob.Q[2] * ob.Q[2], comet = /^(\d+P|[CPD]\/)/.test(o.name || '');
    o.rows = () => { const p = o.get(), k = AU * (F.orb || 1), q = [p[0] / k, p[1] / k, p[2] / k], ea = bodyPosM('earth'), dE = Math.hypot(p[0] - ea[0], p[1] - ea[1], p[2] - ea[2]);
      const cE = (q[0] * ob.P[0] + q[1] * ob.P[1] + q[2] * ob.P[2]) / (a * a) + e, sE = (q[0] * ob.Q[0] + q[1] * ob.Q[1] + q[2] * ob.Q[2]) / b2, E = Math.atan2(sE, cE), M = ((E - e * sE) % TAU + TAU) % TAU;
      const r = rows().concat([['Distance à la Terre', sig(dE / AU, 3) + NBSP + 'UA'], ['La lumière du Soleil l’atteint en', fmtLight(vlen(p))], ['Vitesse au plus près du Soleil', sig(orbSpeed(a * (1 - e), a), 3) + NBSP + 'km/s'], ['Vitesse au plus loin', sig(orbSpeed(a * (1 + e), a), 3) + NBSP + 'km/s']]);
      if (!comet && Math.abs(S.ty) < 3000) r.push(['Prochain passage au plus près du Soleil', 'dans ' + fmtYears((1 - M / TAU) * Math.pow(a, 1.5))]); return r.concat(skyRow([p[0] - ea[0], p[1] - ea[1], p[2] - ea[2]])); }; return o; };
  // ---- trous noirs : grandeurs calculées à partir de la masse
  const bhExtra = (M, p, big) => { const d = vlen(p), r = [['Dernière orbite stable', 'un tour en ' + fmtSec(4.548e-4 * M) + ' (si le trou noir ne tourne pas)']];
    if (big) r.push(['Taille de son ombre vue d’ici', sig(15.345e3 * M / d * 206264.806e6, 2) + NBSP + 'millionièmes de seconde d’arc']);
    r.push(['Température de Hawking', sci(6.169e-8 / M) + ' K (prédiction théorique)'], ['Évaporation complète', 'dans ' + sci(2.098e67 * M * M * M) + ' ans (prédiction théorique)']); return r.concat(skyRow(p)); };
  // ---- amas, galaxies, pulsars : compléments des catalogues
  const velRow = v => ['Vitesse mesurée', (v < 0 ? 'se rapproche' : 's’éloigne') + ' à ' + nf(Math.abs(Math.round(v)), 0) + NBSP + 'km/s, z = ' + zStr(v / 299792.458)], metal = x => ['Éléments plus lourds que l’hélium', sig(Math.pow(10, x) * 100, 2) + NBSP + '% de la teneur du Soleil'];
  const cluExtra = i => { const x = DATA.CLU_X[i], r = []; if (!x) return r; if (x[1] !== null) r.push(velRow(x[1])); if (x[0] !== null) r.push(metal(x[0])); if (x[2]) r.push(['Moitié de sa lumière dans un rayon de', fmtDist(x[2] * LY)]); if (x[3]) r.push(['Distance au centre de la galaxie', fmtDist(x[3] * KPC)]); return r; };
  const lgExtra = (g, r, noVel) => { const gi = DATA.LOCAL.findIndex(q => q.n === g.n), x = DATA.LG_X[gi]; lgMove(gi, r); lgTurn(gi, r); if (!x) return; if (x[0]) r.push(['Type', x[0]]); if (x[1] !== null && !noVel) { const v = velRow(x[1]); v[0] = 'Vitesse mesurée, vue du Soleil'; v[1] += ' · mesuré'; r.push(v); } if (x[2]) r.push(['Masse en étoiles', bigMass(x[2] * 1e6)]); if (x[4]) r.push(['Gaz d’hydrogène', bigMass(x[4] * 1e6)]); if (x[3] !== null) r.push(metal(x[3])); };
  const nearExtra = i => { const x = DATA.NEAR_X[i], r = []; if (!x) return r; if (x[0] !== null) r.push(['Type', x[0] <= 0 ? 'elliptique ou lenticulaire' : x[0] <= 8 ? 'spirale' : 'irrégulière ou naine']); if (x[1] !== null) r.push(velRow(x[1])); if (x[2] !== null) r.push(['Éclat', bigMass(Math.pow(10, 0.4 * (5.48 - x[2])))]); if (x[3]) r.push(['Masse d’après sa rotation', bigMass(Math.pow(10, x[3]))]); if (x[4]) r.push(['Gaz d’hydrogène', bigMass(Math.pow(10, x[4]))]); return r; };
  const PSRA = DATA.PSR_AGE ? new Float32Array(b64ToBytes(DATA.PSR_AGE).buffer) : null;
  const psrExtra = (i, p) => { const r = []; if (PSRA && PSRA[i] > 0) r.push(['Âge estimé', fmtYears(PSRA[i])]); if (p > 0) r.push(['Vitesse à son équateur', sig(TAU * 12 / p / 299792.458 * 100, 2) + NBSP + '% de la vitesse de la lumière (pour un rayon supposé de 12 km)']); return r; };
  const planetRows = key => { const el = DATA.JPL1[key === 'earth' ? 'emb' : key], r = vlen(bodyPosM(key)) / AU, base = [['Distance au Soleil', nf(r, 3) + NBSP + 'UA']].concat(TIDE_P[key] ? [['Fin calculée', 'engloutie ' + (S.ty / 1e9 < TIDE_P[key].tEng ? inTime((TIDE_P[key].tEng - S.ty / 1e9) * 1e9) : 'il y a ' + fmtYears((S.ty / 1e9 - TIDE_P[key].tEng) * 1e9)) + '. Spirale calculée : orbite élargie par la perte de masse du Soleil, puis resserrée par marées et frottement (Schröder et Smith 2008 ; Soleil géant d’après le modèle MIST, Choi et al. 2016).']] : []); if (!el) return base; const a = el[0], e = el[1];
    return base.concat([['Orbite', 'de ' + sig(a * (1 - e), 3) + ' à ' + sig(a * (1 + e), 3) + NBSP + 'UA'], ['Excentricité', sig(e, 2)]], key === 'earth' ? [] : [['Inclinaison', sig(el[2], 2) + '° sur l’orbite de la Terre']], [['Un tour du Soleil', fmtYears(Math.pow(a, 1.5))], ['Vitesse sur l’orbite', sig(orbSpeed(r / ((F.orbP && F.orbP[key]) || F.orb || 1), a), 3) + NBSP + 'km/s']]); };
  const fmtDays = d => d < 2 ? sig(d * 24, 2) + NBSP + 'heures' : d < 800 ? sig(d, 3) + NBSP + 'jours' : sig(d / 365.25, 3) + NBSP + 'ans';
  const exoStar = i => { const q = (DATA.EXO_ST[i] || '').split('~'), o = []; if (q[0]) o.push('type ' + q[0]); if (+q[1] > 0) o.push(sig(+q[1], 2) + NBSP + 'fois la masse du Soleil'); if (+q[3] > 0) o.push(sig(+q[3], 2) + NBSP + 'fois son rayon'); if (+q[2] > 0) o.push(nf(Math.round(+q[2] / 10) * 10, 0) + NBSP + 'K'); if (+q[4] > 0) o.push('âge ' + sig(+q[4], 2) + NBSP + 'milliards d’années'); return o.length ? [['Son étoile', o.join(', ')]] : []; };
  const exoRows = i => { const L = (DATA.EXO_PL[i] || '').split(';').filter(Boolean), r = [];
    for (const t of L.slice(0, 8)) { const q = t.split('~'), P = +q[1], a = +q[2], M = +q[3], Rj = +q[4], ec = +q[6], T = +q[7], o = []; if (P > 0) o.push('un tour en ' + fmtDays(P)); if (a > 0) o.push('à ' + sig(a, 2) + NBSP + 'UA de son étoile'); if (M > 0) o.push(M < 0.03 ? sig(M * 317.8, 2) + NBSP + 'fois la masse de la Terre' : sig(M, 2) + NBSP + 'fois la masse de Jupiter');
      if (Rj > 0) o.push(Rj < 0.35 ? sig(Rj * 11.21, 2) + NBSP + 'fois le rayon de la Terre' : sig(Rj, 2) + NBSP + 'fois le rayon de Jupiter'); if (ec > 0.1) o.push('orbite allongée (excentricité ' + sig(ec, 2) + ')'); if (T > 0) o.push('environ ' + nf(Math.round(T / 10) * 10, 0) + NBSP + 'K'); if (q[5]) o.push('trouvée en ' + q[5] + (DATA.EXO_METH[q[8]] ? ' ' + DATA.EXO_METH[q[8]] : '')); r.push(['Planète ' + (q[0] || '?'), o.join(', ') || 'orbite mal connue']); }
    if (L.length > 8) r.push(['Et aussi', (L.length - 8) + ' autres planètes']); return r; };
  const survPlus = (o, P, i) => { const z = P.svInfo[i * 3], q = P.svInfo[i * 3 + 2] > 1.5, rows = o.rows;
    o.rows = () => rows().concat([['Taille de l’univers à l’émission', sig(100 / (1 + z), 3) + NBSP + '% de sa taille actuelle'], ['Distance au moment de l’émission', fmtDist(vlen(o.get()) / (1 + z) / (F.cos.a || 1))]], q ? [['Moteur', 'un trou noir supermassif qui avale la matière autour de lui']] : [], [['Âge de l’univers à l’émission', fmtYears(Math.max(F.age - S.ty / 1e9 - lookbackGyr(z), 0) * 1e9)]], skyRow([P.svDir[i * 3], P.svDir[i * 3 + 1], P.svDir[i * 3 + 2]])); return o; };
  const horizon = M => { const d = 5.906 * M; return d < 2e6 ? 'environ ' + nf(Number(d.toPrecision(2)), 0) + NBSP + 'km de diamètre' : fmtDist(d * 1e3) + ' de diamètre'; };       // diamètre de l'horizon : 2 × 2,953 km par masse solaire
  const bigMass = M => M >= 1e9 ? sig(M / 1e9, 2) + NBSP + 'milliards de fois le Soleil' : M >= 1e6 ? sig(M / 1e6, 2) + NBSP + 'millions de fois le Soleil' : nf(Number(M.toPrecision(2)), 0) + NBSP + 'fois le Soleil';
  const BHSM = new Float32Array(b64ToBytes(DATA.BHS.mass).buffer), BHSP = new Float32Array(b64ToBytes(DATA.BHS.per).buffer), BHML = new Float32Array(b64ToBytes(DATA.BHM.logm).buffer);
  const BH_KIND = ['Trou noir stellaire révélé par des sursauts de rayons X', 'Trou noir stellaire qui arrache la matière de son étoile compagne', 'Trou noir stellaire « dormant », trahi par l’orbite de son étoile compagne'];
  const BH_METH = { reverb: 'l’écho lumineux du gaz qui l’entoure', gas: 'le mouvement du gaz autour de lui', maser: 'des masers en orbite autour de lui', star: 'le mouvement des étoiles autour de lui', stars: 'le mouvement des étoiles autour de lui', CO: 'le mouvement du gaz moléculaire autour de lui' };
  function selBHS(i) { const P = Rr.BHS.pos, m = BHSM[i], per = BHSP[i], get = () => [P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY];
    return { name: DATA.BHS.names[i], sub: BH_KIND[DATA.BHS.kind[i]] || BH_KIND[0], get, rows: () => [['Distance', fmtDist(vlen(get()))], ['Masse', m > 0 ? (DATA.BHS.lim[i] ? 'plus de ' : '') + sig(m, 3) + NBSP + 'fois le Soleil' : 'pas encore mesurée']].concat(m > 0 ? [['Horizon', horizon(m)]] : [], per > 0 ? [['Orbite avec son étoile', 'un tour en ' + fmtDays(per / 24)]] : [], [['Repéré en', DATA.BHS.year[i]]], m > 0 ? bhExtra(m, get(), false) : skyRow(get())) }; }
  function selBHM(i) { const P = Rr.BHM.pos, eht = DATA.BHM.names[i] === 'M87', M = eht ? 6.5e9 : Math.pow(10, BHML[i]), get = () => add3(F.gcRel, [P[i * 3], P[i * 3 + 1], P[i * 3 + 2]], MPC * F.cos.a);
    return { name: 'Trou noir central de ' + DATA.BHM.names[i], sub: 'Trou noir supermassif au cœur d’une galaxie', get, rows: () => [['Distance', fmtDist(vlen(get()))], ['Masse', bigMass(M)], ['Horizon', horizon(M)], ['Mesuré par', eht ? 'l’image de son ombre (Event Horizon Telescope, 2019)' : BH_METH[DATA.BHM.meth[i]] || 'plusieurs méthodes'], ['Décalage vers le rouge', 'z = ' + zStr(F.cos.Hkms * vlen(get()) / MPC / 299792.458) + ' (expansion seule)']].concat(eht ? [['Lumière déviée', 'calculée à moins de ' + horizonX(M) + ' : ombre, anneau de photons, images doubles. Trou noir supposé sans rotation (non mesurée sûrement). Aucun disque de gaz dessiné : l’anneau de l’image EHT, qui en est la lumière, n’apparaît pas. Les noms restent à leur place non déviée. Les étoiles proches sont traitées comme si elles étaient très loin. À moins d’une fois et demie la taille de l’horizon : non calculé']] : [], bhExtra(M, get(), true)) }; }
  function selSgrA() { const M = Math.pow(10, DATA.SGRA_LOGM || 6.63), get = () => [F.gcRel[0], F.gcRel[1], F.gcRel[2]];
    return { name: 'Sagittarius A*', sub: 'Trou noir supermassif au centre de la Voie lactée', get, rows: () => [['Distance', fmtDist(vlen(get()))], ['Masse', bigMass(M)], ['Horizon', horizon(M)], ['Mesuré par', 'le mouvement des étoiles autour de lui'], ['Le Soleil en fait le tour en', fmtYears(TAU * GAL.R0 / (vCirc(GAL.R0, true) * KMS_KPC_GYR) * 1e9) + ' environ'], ['À voir de près', 'centre la vue ici puis zoome jusqu’à quelques jours-lumière : 39 étoiles tournent autour de lui sur leur orbite mesurée'], ['Lumière déviée', 'calculée à moins de ' + horizonX(M) + ' : ombre, anneau de photons, images doubles. Trou noir supposé sans rotation (non mesurée sûrement). Aucun disque de gaz dessiné : l’anneau de l’image EHT, qui en est la lumière, n’apparaît pas. Les noms restent à leur place non déviée. Les étoiles proches sont traitées comme si elles étaient très loin. À moins d’une fois et demie la taille de l’horizon : non calculé']].concat(bhExtra(M, get(), true)) }; }
  const horizonX = M => fmtDist(1e7 * GM_C2_SUN * M);      /* S6 : distance d'allumage de la lentille (LENS_RON dans 40_render.js) */
  function loadAstNames() { if (!TL.astP) { const m = TL.list.find(m => m.kind === 'ast' && (m.names || m.namesUrl)); TL.astP = m ? fetch(m.namesUrl || ('/_blob/' + m.names)).then(r => r.text()).then(t => { TL.astN = t.split('\n'); FIDX = null; }).catch(() => {}) : Promise.resolve(); } return TL.astP; }
  function selAstT(T, i) { const j = i * 3, e = T.el[j], P = [T.pos[j], T.pos[j + 1], T.pos[j + 2]], Q = [T.q[j], T.q[j + 1], T.q[j + 2]], a = Math.hypot(P[0], P[1], P[2]), bq = Math.hypot(Q[0], Q[1], Q[2]), H = T.H[i], inc = Math.acos(clamp((P[0] * Q[1] - P[1] * Q[0]) / (a * bq), -1, 1)) / DEG;
    const get = () => { const E = keplerE(wrapPi(T.el[j + 1] + T.el[j + 2] * (F.jd - T.epoch)), e), x = Math.cos(E) - e, y = Math.sin(E), k = AU * (F.orb || 1); return [(P[0] * x + Q[0] * y) * k, (P[1] * x + Q[1] * y) * k, (P[2] * x + Q[2] * y) * k]; };
    const nm = () => { const t = TL.astN ? TL.astN[i] : null; if (!t) return 'Astéroïde'; const q = t.split('~'); return q[0] ? q[0] + ' (' + q[1] + ')' : 'Astéroïde ' + q[1]; };
    const o = { name: nm(), sub: 'Astéroïde', get, orbit: { e, P, Q }, rows: () => [['Distance au Soleil', sig(vlen(get()) / AU, 4) + NBSP + 'UA'], ['Orbite', 'de ' + sig(a * (1 - e), 3) + ' à ' + sig(a * (1 + e), 3) + NBSP + 'UA'], ['Excentricité', sig(e, 3)], ['Inclinaison', sig(inc, 3) + '°'], ['Un tour du Soleil', fmtYears(Math.pow(a, 1.5))], ['Vitesse actuelle', sig(orbSpeed(vlen(get()) / AU / (F.orb || 1), a), 3) + NBSP + 'km/s'], ['Diamètre estimé', sig(1329 / Math.sqrt(0.14) * Math.pow(10, -H / 5), 2) + NBSP + 'km (d’après son éclat)']] };
    loadAstNames().then(() => { o.name = nm(); if (S.sel === o) renderCard(); }); return orbPlus(o); }
  function selStarT(T, i) {      // étoile reçue en flux : mouvement en ligne droite, suivie sur quelques millions d'années
    const j = i * 3, MV = T.mag[i], bv = T.ci[i] / 80 - 0.5, L = starLife(MV, bv, i + 500000, 0), get = () => { const kv = S.ty * 2 * KMS_LY_YR; return [(T.pos[j] + T.vel[j] * kv) * LY, (T.pos[j + 1] + T.vel[j + 1] * kv) * LY, (T.pos[j + 2] + T.vel[j + 2] * kv) * LY]; };
    return { name: 'Étoile du catalogue Gaia', sub: 'Étoile ' + STAR_CLASS[L[5]] + ', type ' + bvSpectral(bv), get, rows: () => [['Distance', fmtDist(vlen(get()))], ['Éclat', fmtTimes(Math.pow(10, 0.4 * (4.83 - MV))) + ' le Soleil'], ['Température', nf(Math.round(bvTemp(bv) / 50) * 50, 0) + NBSP + 'K'], ['Masse estimée', sig(L[4], 2) + NBSP + 'fois le Soleil'], ['Vitesse', sig(2 * Math.hypot(T.vel[j], T.vel[j + 1], T.vel[j + 2]), 3) + NBSP + 'km/s par rapport au Soleil']].concat(starExtra(get(), [2 * T.vel[j], 2 * T.vel[j + 1], 2 * T.vel[j + 2]], MV, bv)) };
  }
  function selStar2(i) {
    const st = Rr.star2, sp = st.pos, MV = st.mag[i], bv = st.bv[i], L = [st.life[i * 3], st.life[i * 3 + 1], st.life[i * 3 + 2]], fate = st.fate[i], get = () => [sp[i * 3] * LY, sp[i * 3 + 1] * LY, sp[i * 3 + 2] * LY];
    return { name: 'Étoile du catalogue Gaia', exist: () => starState(L, fate), sub: 'Étoile ' + STAR_CLASS[st.cls[i]] + ', type ' + bvSpectral(bv), get, rows: () => {
      const d = vlen(get()), t = F.tMyr, sn = fate === 1 || fate === 3, lum = Math.pow(10, 0.4 * (4.83 - MV));
      const fut = fate === 4 || (!sn && t >= L[2]) ? 'naine blanche qui refroidit' : sn && t >= L[2] ? 'a explosé en supernova' : sn ? 'supernova ' + inTime((L[2] - t) * 1e6) : t < L[1] ? 'géante rouge ' + inTime((L[1] - t) * 1e6) + ', puis naine blanche' : 'naine blanche ' + inTime((L[2] - t) * 1e6);
      return [['Distance', fmtDist(d)], ['Éclat', fmtTimes(lum) + ' le Soleil'], ['Température', nf(Math.round(bvTemp(bv) / 50) * 50, 0) + NBSP + 'K'], ['Masse estimée', sig(st.mass[i], 2) + NBSP + 'fois le Soleil'], ['Vitesse', sig(st.K.vkms[i], 3) + NBSP + 'km/s par rapport au Soleil'], ['Mouvement', orbMotionText(st.K, i, F.tEff, true)], ['Avenir estimé', fut]].concat(starExtra(get(), kvOf(st.K, i), MV, bv)); } };
  }
  const COMN = DATA.COM_NAMES.split('|'), COMC = b64ToBytes(DATA.COM_CLS), EXON = DATA.EXO_NAMES.split('|'), EXOP = b64ToBytes(DATA.EXO_NP), PSRN = DATA.PSR_NAMES.split('|'), PSRP = new Float32Array(b64ToBytes(DATA.PSR_P0).buffer);
  const COM_FR = { JFC: 'Comète de la famille de Jupiter', JFc: 'Comète de la famille de Jupiter', HTC: 'Comète de type Halley', ETc: 'Comète de type Encke', CTc: 'Comète de type Chiron' };
  const MOIS_C = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  const jdDate = jd => { const z = Math.floor(jd + 0.5), al = Math.floor((z - 1867216.25) / 36524.25), A = z + 1 + al - Math.floor(al / 4), B = A + 1524, C = Math.floor((B - 122.1) / 365.25), Dd = Math.floor(365.25 * C), E = Math.floor((B - Dd) / 30.6001), d = B - Dd - Math.floor(30.6001 * E), m = E < 14 ? E - 1 : E - 13, y = m > 2 ? C - 4716 : C - 4715; return 'le ' + d + (d === 1 ? 'er ' : ' ') + MOIS_C[m - 1] + ' ' + y; };
  const CFIX = {}; { const fx = DATA.COM_FIX || {}; for (const k in fx) { const i = COMN.indexOf(k); if (i >= 0 && fx[k].next) CFIX[i] = fx[k].next; } }
  function selComet(i) {
    const B = Rr.COM, a = B.a[i], e = B.e[i], Pd = TAU / B.n[i], get = () => [B.pos[i * 3] * AU * F.orb, B.pos[i * 3 + 1] * AU * F.orb, B.pos[i * 3 + 2] * AU * F.orb];
    return { name: COMN[i] || 'Comète', sub: COM_FR[DATA.COM_CLSN[COMC[i]]] || 'Comète', get, orbit: { e, P: [a * B.P[i * 3], a * B.P[i * 3 + 1], a * B.P[i * 3 + 2]], Q: [a * Math.sqrt(1 - e * e) * B.Q[i * 3], a * Math.sqrt(1 - e * e) * B.Q[i * 3 + 1], a * Math.sqrt(1 - e * e) * B.Q[i * 3 + 2]] }, rows: () => { const nx = B.tp[i] + Math.ceil((F.days - B.tp[i]) / Pd) * Pd;
      return [['Distance au Soleil', sig(vlen(get()) / AU, 4) + NBSP + 'UA'], ['Orbite', 'de ' + sig(a * (1 - e), 3) + ' à ' + sig(a * (1 + e), 3) + NBSP + 'UA'], ['Inclinaison', sig(B.inc[i] / DEG, 3) + '°'], ['Excentricité', sig(e, 4)], ['Un tour du Soleil', fmtYears(Math.pow(a, 1.5))], ['Vitesse actuelle', sig(orbSpeed(vlen(get()) / AU / (F.orb || 1), a), 3) + NBSP + 'km/s'],
        ['Prochain passage près du Soleil', CFIX[i] && Math.abs(S.ty) < 20 && F.jd < CFIX[i] ? jdDate(CFIX[i]) + ' (calcul du JPL, attraction des planètes comprise)' : Math.abs(S.ty) < 3000 ? 'vers ' + Math.round(2000 + nx / 365.25) + ' (sans l’attraction des planètes)' : 'non suivi aussi loin dans le temps']]; } };
  }
  // Chaque planète est placée sur son orbite réelle : taille, forme et durée mesurées. L'inclinaison vient des transits quand il y en a ;
  // l'orientation sur le ciel n'est jamais mesurée : elle est tirée une fois pour toutes, par système. La position sur l'orbite vient des dates de transit ou de passage au plus près.
  function exoSys(i) { if (EXS[i]) return EXS[i]; const P = Rr.EXO.pos, c0 = [P[i * 3], P[i * 3 + 1], P[i * 3 + 2]], d = Math.hypot(c0[0], c0[1], c0[2]) || 1, l = [c0[0] / d, c0[1] / d, c0[2] / d];
    const st = (DATA.EXO_ST[i] || '').split('~'), Ms = +st[1] > 0 ? +st[1] : 1, Ls = st[5] ? Math.pow(10, +st[5]) : (+st[3] > 0 && +st[2] > 0 ? st[3] * st[3] * Math.pow(st[2] / 5772, 4) : null);
    const e1 = vnorm(vcross(l, Math.abs(l[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0])), e2 = vcross(l, e1), pa = hash01(i * 13 + 5) * TAU, nd = [Math.cos(pa) * e1[0] + Math.sin(pa) * e2[0], Math.cos(pa) * e1[1] + Math.sin(pa) * e2[1], Math.cos(pa) * e1[2] + Math.sin(pa) * e2[2]], mm = vcross(l, nd), num = x => x !== undefined && x !== '' && isFinite(+x);
    const list = (DATA.EXO_PL[i] || '').split(';').filter(Boolean).map((t, j) => { const q = t.split('~'), per = +q[1] > 0 ? +q[1] : 0; let a = +q[2] > 0 ? +q[2] : 0; if (!a && per) a = Math.cbrt(Ms * Math.pow(per / 365.25, 2)); if (!a) return null; const perd = per || Math.sqrt(a * a * a / Ms) * 365.25;
      const e = clamp(+q[6] || 0, 0, 0.95), tran = q[13] === '1', incK = num(q[9]), inc = (incK ? +q[9] : tran ? 89 : 60) * DEG, wK = num(q[11]), w = (wK ? +q[11] : 90) * DEG, ci = Math.cos(inc), si = Math.sin(inc), h = [-ci * l[0] + si * mm[0], -ci * l[1] + si * mm[1], -ci * l[2] + si * mm[2]], v = vcross(h, nd), cw = Math.cos(w), sw = Math.sin(w);
      const Pv = [cw * nd[0] + sw * v[0], cw * nd[1] + sw * v[1], cw * nd[2] + sw * v[2]], Qv = [-sw * nd[0] + cw * v[0], -sw * nd[1] + cw * v[1], -sw * nd[2] + cw * v[2]], nr = TAU / perd, jd0 = 2461355.5; let M0, src = '';
      if (num(q[10]) && +q[10] > 2400000) { const nu = Math.PI / 2 - w, E = 2 * Math.atan(Math.sqrt((1 - e) / (1 + e)) * Math.tan(nu / 2)); M0 = E - e * Math.sin(E) + nr * (jd0 - (+q[10])); src = 'tr'; } else if (num(q[12]) && +q[12] > 2400000) { M0 = nr * (jd0 - (+q[12])); src = 'pe'; } else M0 = hash01(i * 31 + j * 7 + 3) * TAU;
      return { n: q[0] || '?', a, e, P: Pv, Q: Qv, M0: wrapPi(M0), nr, jd0, per: perd, mass: +q[3] || 0, rad: +q[4] || 0, temp: +q[7] || 0, year: q[5], meth: q[8], insol: +q[14] || 0, tran, incK, src }; }).filter(Boolean);
    return (EXS[i] = { list, amax: Math.max.apply(null, list.map(p => p.a * (1 + p.e)).concat([0.01])), L: Ls }); }
  const exoLr = i => clamp(Math.log10(exoSys(i).amax * AU * 2.7), 9.2, 13.4);
  function setExoSystem(i, getC) { const P = Rr.EXO.pos, c = getC || (() => [P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY]); if (EXA && EXA.i === i) { EXA.c = c; return; } const sy = exoSys(i), t = KSETS['exo:exo']; EXA = { i, c, sy };
    t.idx.forEach((k, j) => { const m = KO[k], p = sy.list[j]; m.on = !!p; if (p) { Object.assign(m, { aAU: p.a, e: p.e, P: p.P, Q: p.Q, M0: p.M0, nr: p.nr, jd0: p.jd0, n: EXON[i] + ' ' + p.n, pl: p }); t.look[j * 2] = clamp(1.8 + Math.log10(Math.max(p.rad * 11.21, 0.5)) * 1.2, 1.7, 3.6); } const L = exoLab[j]; if (L) { L.el.textContent = p ? p.n : ' '; L.w = p ? 10 + p.n.length * 7 : 0; } });
    Rr.moonLookDirty('exo:exo'); Rr.setSysOrbits(sy.list.map(p => ({ e: p.e, P: p.P.map(x => x * p.a), Q: p.Q.map(x => x * p.a * Math.sqrt(1 - p.e * p.e)) }))); }
  function selExoPlanet(k) { const m = KO[k], p = m.pl, sy = EXA.sy, cen = () => cenOf('exo'), get = () => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]], a = p.a, b = a * Math.sqrt(1 - p.e * p.e), re = p.rad * 11.21, me = p.mass * 317.8;
    const kind = re > 0 ? (re < 1.25 ? 'de taille comparable à la Terre' : re < 2 ? 'de type super-Terre' : re < 4 ? 'de type mini-Neptune' : re < 8 ? 'de la taille de Neptune' : 'géante gazeuse') : me > 0 ? (me < 2 ? 'de masse comparable à la Terre' : me < 10 ? 'de type super-Terre' : me < 50 ? 'de masse comparable à Neptune' : 'géante gazeuse') : '';
    return { name: m.n, sub: 'Exoplanète ' + kind, get, orbit: { e: p.e, P: p.P.map(x => x * a), Q: p.Q.map(x => x * b), c: cen }, rows: () => { const c = cen(), q = get(), d = Math.hypot(q[0] - c[0], q[1] - c[1], q[2] - c[2]) / AU;
      const r = [['Distance à son étoile', sig(d, 3) + NBSP + 'UA'], ['Orbite', p.e > 0.005 ? 'de ' + sig(a * (1 - p.e), 3) + ' à ' + sig(a * (1 + p.e), 3) + NBSP + 'UA' : 'presque circulaire, à ' + sig(a, 3) + NBSP + 'UA'], ['Un tour de son étoile', fmtDays(p.per)]];
      if (me > 0) r.push(['Masse', me < 30 ? sig(me, 2) + NBSP + 'fois la Terre' : sig(p.mass, 2) + NBSP + 'fois Jupiter']); if (re > 0) r.push(['Rayon', re < 6 ? sig(re, 2) + NBSP + 'fois la Terre' : sig(p.rad, 2) + NBSP + 'fois Jupiter']);
      if (p.temp > 0) r.push(['Température d’équilibre', nf(Math.round(p.temp / 10) * 10, 0) + NBSP + 'K, soit ' + String(Math.round((p.temp - 273.15) / 10) * 10).replace('-', '−') + NBSP + '°C']); if (p.insol > 0) r.push(['Lumière reçue', sig(p.insol, 2) + NBSP + 'fois celle que reçoit la Terre']);
      if (sy.L) { const hi = 0.95 * Math.sqrt(sy.L), ho = 1.67 * Math.sqrt(sy.L); r.push(['Zone habitable de l’étoile', 'de ' + sig(hi, 2) + ' à ' + sig(ho, 2) + NBSP + 'UA : ' + (a < hi ? 'cette planète est trop près, trop chaude' : a > ho ? 'cette planète est trop loin, trop froide' : 'cette planète est dedans (calcul simple, sans tenir compte de son atmosphère)')]); }
      if (p.year) r.push(['Découverte', 'en ' + p.year + (DATA.EXO_METH[p.meth] ? ', ' + DATA.EXO_METH[p.meth] : '')]);
      r.push(['Position sur son orbite', p.src === 'tr' ? 'calculée d’après ses transits observés' : p.src === 'pe' ? 'calculée d’après son passage au plus près mesuré' : 'inconnue : la planète est placée au hasard sur son orbite'], ['Orientation de l’orbite', (p.incK ? 'inclinaison mesurée' : p.tran ? 'vue par la tranche depuis la Terre' : 'inclinaison inconnue') + ' ; son orientation sur le ciel n’est pas mesurée, elle est choisie arbitrairement']); return r; } }; }
  // correspondance entre les étoiles du catalogue principal et les étoiles à planètes (même direction, même distance)
  const STAREXO = (() => { const N = Rr.star.N, sp = Rr.starPos, P = Rr.EXO.pos, out = new Int32Array(N).fill(-1), grid = new Map(), key = (lo, la) => Math.floor(lo) * 1000 + Math.floor(la + 90);
    for (let h = 0; h < Rr.EXO.N; h++) { const x = P[h * 3], y = P[h * 3 + 1], z = P[h * 3 + 2], d = Math.hypot(x, y, z) || 1, k = key((Math.atan2(y, x) / DEG + 360) % 360, Math.asin(z / d) / DEG); (grid.get(k) || grid.set(k, []).get(k)).push(h); }
    for (let i = 0; i < N; i++) { const x = sp[i * 3], y = sp[i * 3 + 1], z = sp[i * 3 + 2], d = Math.hypot(x, y, z); if (!(d > 0)) continue; const lo = (Math.atan2(y, x) / DEG + 360) % 360, la = Math.asin(z / d) / DEG, tol = Math.max(0.03, 4 / d) * DEG; let best = -1, bs = tol;
      for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const L = grid.get(key((lo + a + 360) % 360, la + b)); if (!L) continue; for (const h of L) { const hx = P[h * 3], hy = P[h * 3 + 1], hz = P[h * 3 + 2], hd = Math.hypot(hx, hy, hz); if (Math.abs(hd / d - 1) > 0.25) continue; const sep = Math.acos(clamp((x * hx + y * hy + z * hz) / (d * hd), -1, 1)); if (sep < bs) { bs = sep; best = h; } } }
      out[i] = best; } return out; })();
  function selExo(i) { const P = Rr.EXO.pos, n = EXOP[i], get = () => [P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY];
    return { exoI: i, lr: exoLr(i), name: EXON[i], sub: 'Étoile entourée de ' + (n > 1 ? n + ' planètes connues' : 'une planète connue'), get, rows: () => [['Distance', fmtDist(vlen(get()))], ['Planètes confirmées', n + ' : « Y aller » pour les voir tourner autour de l’étoile']].concat(exoStar(i), exoRows(i), skyRow(get())) }; }
  function selPsr(i) { const P = Rr.PSR.pos, p = PSRP[i], get = () => [P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY];
    return { name: 'PSR ' + PSRN[i], sub: 'Pulsar : étoile à neutrons en rotation rapide', get, rows: () => [['Distance', fmtDist(vlen(get())) + ' (estimée)'], ['Un tour sur lui-même', p > 0 ? (p < 0.1 ? sig(p * 1000, 3) + NBSP + 'millisecondes' : sig(p, 3) + NBSP + 's') : 'non mesuré'], ['Tours par seconde', p > 0 ? sig(1 / p, 3) : 'non mesuré']].concat(psrExtra(i, p), skyRow(get())) }; }
  function selCluster(i) {
    const c = Rr.clu, glob = i < DATA.CLUSTERS_N[0], get = () => [c.pos[i * 3] * LY, c.pos[i * 3 + 1] * LY, c.pos[i * 3 + 2] * LY];
    return { name: NM.clu[i] || 'Amas', sub: glob ? 'Amas globulaire : des centaines de milliers d’étoiles très âgées' : 'Amas ouvert : des étoiles nées ensemble', get, rows: () => [['Distance', fmtDist(vlen(get()))], ['Âge', glob ? 'plus de 10 milliards d’années' : fmtYears(Math.pow(10, CAGE[i] / 20))], ['Éclat', fmtTimes(Math.pow(10, 0.4 * (4.83 - c.mag[i]))) + ' le Soleil' + (glob ? '' : ' (estimé)')]].concat(glob ? cluExtra(i) : [], skyRow(get())) };
  }
  /* Cosmicflows-4 (Tully et al. 2023) : distance mesurée depuis la Terre, aujourd'hui, galaxie par galaxie, et méthodes publiées.
     rec = [pgc, module de distance, erreur, {méthode: [module, erreur]}]. « Distance » plus haut suit le point de vue et l'époque ;
     cette ligne-ci est la mesure brute. Précision : ln10/5 × erreur sur le module (approximation usuelle), au moins 1 %. */
  const CF4_M = { ceph: 'Céphéides', trgb: 'sommet de la branche des géantes rouges', mas: 'maser d’eau autour du trou noir central', snIa: 'supernova de type Ia', sbf: 'fluctuations de brillance de surface', snII: 'supernova de type II', tf: 'relation de Tully-Fisher (rotation et éclat)', fp: 'plan fondamental (galaxie elliptique ou lenticulaire)' };
  function cf4Rows(rec) { if (!rec || rec[1] === null) return [];
    const d = Math.pow(10, rec[1] / 5 + 1) * PC, rel = rec[2] === null ? null : Math.max(1, Math.round(Math.LN10 / 5 * rec[2] * 100));
    const ms = Object.keys(rec[3]).sort((a, b) => (rec[3][a][1] || 9) - (rec[3][b][1] || 9)).map(k => CF4_M[k] || k);
    return [['Mesure depuis la Terre', fmtDist(d, rel !== null && rel > 10 ? 2 : 3) + (rel !== null ? ', à ' + rel + NBSP + '% près' : '')],
      ['Mesurée par', ms.length ? ms[0] + (ms.length > 1 ? ' (et ' + (ms.length - 1) + ' autre' + (ms.length > 2 ? 's' : '') + ' : ' + ms.slice(1).join(', ') + ')' : '') : 'non précisé']]; }
  function cf4Src(rec) { return rec && rec[1] !== null ? [['Source de la mesure', 'Cosmicflows-4 (Tully et al. 2023), galaxie PGC ' + rec[0]]] : []; }
  function selLG(c) {
    const g = c.g, get = () => add3(F.gcRel, c.c, KPC);
    return { name: g.n, exist: () => c.gone ? 'fondue dans une autre galaxie (calculé)' : null, sub: c.own ? 'Grande galaxie spirale du Groupe local' : 'Galaxie du Groupe local', get, rows: () => { const r = [['Distance', fmtDist(vlen(get()))]].concat(cf4Rows(DATA.CF4_LOCAL && DATA.CF4_LOCAL[DATA.LOCAL.indexOf(g)])); { const mv = c.own ? -21.0 : g.mv; if (mv !== undefined && mv < 0) r.push(['Éclat', bigMass(Math.pow(10, 0.4 * (4.83 - mv)))]); }      // Andromède : magnitude absolue −21,0 (McConnachie 2012)
      if (c.own) { const O = S.orbit, p = O.peri[0]; r.push(['Vitesse', 'radiale ' + nf(Math.round(O.vr), 0).replace('-', '−') + NBSP + 'km/s, transverse ' + nf(Math.round(O.vt), 0) + NBSP + 'km/s']); if (p) r.push(['Au plus près', 'dans ' + fmtYears(p[0] * 1e9) + ', à ' + fmtDist(Number((p[1] * KPC).toPrecision(2)))]); r.push(['Fusion', O.tMerge ? 'dans ' + fmtYears(O.tMerge * 1e9) + ' (scénario calculé)' : 'pas avant 14 milliards d’années dans ce scénario']); }
      lgExtra(g, r, c.own || MAG.c.indexOf(c) >= 0);
      if (c.own) r.push(['Décalage mesuré', 'vers le bleu, z = −0,0010 : elle se rapproche du Soleil à 301 km/s']);
      const mi = MAG.c.indexOf(c); if (mi >= 0) { r.push(['Décalage mesuré', mi === 0 ? 'vers le rouge, z = +0,00087 : il s’éloigne du Soleil à 262 km/s' : 'vers le rouge, z = +0,00049 : il s’éloigne du Soleil à 146 km/s']);
        const p = LMCO.peri[0]; if (p) r.push(['Orbite calculée', 'repasse au plus près de la Voie lactée dans ' + fmtYears(p[0] * 1e9) + ', à ' + fmtDist(Number((p[1] * KPC).toPrecision(2)))]); if (LMCO.tMerge) r.push(['Absorption', 'dans ' + fmtYears(LMCO.tMerge * 1e9) + ' (scénario calculé, très sensible à sa masse)']); }
      return r.concat(cf4Src(DATA.CF4_LOCAL && DATA.CF4_LOCAL[DATA.LOCAL.indexOf(g)])); } };
  }
  /* R18 : chaque galaxie dit pourquoi elle bouge ou non, et pourquoi elle tourne ou non (décision 14 : sans vitesse mesurée, en place, raison affichée) */
  function galMotionRows(get, far) { const ph = !far && photoNear({ get });
    return [['Mouvement dans la simulation', far ? 'S’éloigne avec l’expansion de l’univers (équations de Friedmann) ; à cette distance, aucun déplacement propre n’est mesuré · calculé' : 'En place parmi les autres galaxies (son déplacement dans le ciel n’est pas mesuré) ; s’éloigne avec l’expansion · calculé'],
      ['Rotation dans la simulation', ph ? 'Non montrée : sa photo réelle est affichée telle quelle, autour d’aujourd’hui ; le sens de rotation n’est dans aucun catalogue · inconnu' : far ? 'Non montrée : dessinée comme un point · inconnu' : 'Non montrée : dessinée comme un point ; le sens de rotation n’est dans aucun catalogue · inconnu']]; }
  function selNear(i) { const P = Rr.pick, get = () => add3(F.gcRel, [P.nPos[i * 3], P.nPos[i * 3 + 1], P.nPos[i * 3 + 2]], MPC * F.cos.a);
    return { name: NM.near[i] || 'Galaxie', sub: 'Galaxie proche, à distance mesurée', get, rows: () => [['Distance', fmtDist(vlen(get()))]].concat(cf4Rows(DATA.CF4_NEAR && DATA.CF4_NEAR[i]), [['Diamètre', fmtDist(P.nLook[i * 2] * 2 * MPC, 2)], ['S’éloigne à', nf(Math.round(F.cos.Hkms * vlen(get()) / MPC), 0) + NBSP + 'km/s (expansion seule)'], ['Décalage vers le rouge', 'z = ' + zStr(F.cos.Hkms * vlen(get()) / MPC / 299792.458) + ' (expansion seule)']]).concat(nearExtra(i), galMotionRows(get, false), skyRow(get()), cf4Src(DATA.CF4_NEAR && DATA.CF4_NEAR[i])) }; }
  function selSurv(i, PP) { const P = PP || Rr.pick, z = P.svInfo[i * 3], kind = P.svInfo[i * 3 + 2], get = () => add3(F.gcRel, [P.svDir[i * 3], P.svDir[i * 3 + 1], P.svDir[i * 3 + 2]], P.svDist[i] * MPC * F.cos.a);
    return { name: kind > 1.5 ? 'Quasar' : 'Galaxie', sub: kind > 1.5 ? 'Noyau de galaxie très lumineux, relevé SDSS ou DESI' : kind > 0.5 ? 'Galaxie d’un relevé profond (6dF, 2dF, SDSS ou DESI)' : 'Galaxie du relevé 2MRS', get, rows: () => { const d = P.svDist[i] * MPC * F.cos.a, v = F.cos.Hkms * d * (S.opts.lightcone ? 1 + z : 1) / MPC;      /* S7 : vitesse d'éloignement d'aujourd'hui, même quand la galaxie est placée là où sa lumière est partie */
      return [['Décalage vers le rouge', 'z = ' + sig(z, 3)], ['Couleur', kind > 1.5 ? 'calculée : forme moyenne des quasars (SDSS), décalée de z' + (z > DATA.ZCOL.zq ? ' (tel qu’à z = ' + sig(DATA.ZCOL.zq, 3) + ', au-delà le spectre manque)' : '') : 'calculée : spectre d’une spirale Sb (Kinney 1996) décalé de z ; type réel inconnu' + (z > DATA.ZCOL.zg ? ' (tel qu’à z = ' + sig(DATA.ZCOL.zg, 3) + ', au-delà le spectre manque)' : '')], [S.opts.lightcone ? 'Distance quand sa lumière est partie' : 'Distance à cet instant', fmtDist(d)], ['Sa lumière a voyagé', fmtYears(lookbackGyr(z) * 1e9)], ['S’éloigne à', v > 299792 ? sig(v / 299792.458, 3) + NBSP + 'fois la vitesse de la lumière : c’est l’espace qui s’étire' : nf(Math.round(v / 10) * 10, 0) + NBSP + 'km/s']].concat(galMotionRows(get, true)); } }; }
  function pickAt(x, y, posOnly) { if (S.logR < 3) return null; let bp = null, lx = 0, ly = 0, lz = 0;      /* posOnly (R3) : rend la position (m) de l'objet sous le point, sans ouvrir de fiche */      // dans l'infiniment petit, on ne sélectionne pas les astres restés derrière le fond
   
    PM.multiplyMatrices(Rr.camera.projectionMatrix, Rr.camera.matrixWorldInverse);
    const W = Rr.cssW, H = Rr.cssH, s = F.s, tg = F.tg, cam = Rr.camPos, V = Rr.vis; let best = null, bd = 24, X = 0, Y = 0, Z = 0;
    const dpx = (mx, my, mz) => { lx = mx; ly = my; lz = mz; X = (mx - tg[0]) * s; Y = (my - tg[1]) * s; Z = (mz - tg[2]) * s; const w = pe[3] * X + pe[7] * Y + pe[11] * Z + pe[15]; if (w <= 0.01) return 1e9;
      return Math.hypot(((pe[0] * X + pe[4] * Y + pe[8] * Z + pe[12]) / w * 0.5 + 0.5) * W - x, (0.5 - (pe[1] * X + pe[5] * Y + pe[9] * Z + pe[13]) / w * 0.5) * H - y); };
    const appMag = M => M + 5 * Math.log10(Math.max(Math.hypot(X - cam.x, Y - cam.y, Z - cam.z) * Rr.unitToPc, 1e-7) / 10);
    for (const tag of ['AST', 'TNO']) if ((tag === 'AST' ? Rr.beltVis : Rr.kuiperVis) > 0.3) { const B = Rr[tag], k = AU * F.orb; for (let i = 0; i < B.count; i++) { const d = dpx(B.pos[i * 3] * k, B.pos[i * 3 + 1] * k, B.pos[i * 3 + 2] * k) - 3; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => orbPlus(selBody(tag, i)); } } }
    if (V.stars > 0.25) { const st = Rr.star, sp = Rr.starPos, t = F.tMyr; for (let i = 0; i < st.N; i++) { const d = dpx(sp[i * 3] * LY, sp[i * 3 + 1] * LY, sp[i * 3 + 2] * LY); if (d < bd) { const f = st.fate[i]; if (t < st.life[i * 3] || ((f === 1 || f === 3) && t > st.life[i * 3 + 2] + F.flash)) continue; if (appMag(st.mag[i]) - Rr.expo < 9.3) { bd = d; bp = [lx, ly, lz]; best = () => selStar(i); } } } }
    if (V.stars > 0.25) { const st = Rr.star2, sp = st.pos, t = F.tMyr; for (let i = 0; i < st.N; i++) { const d = dpx(sp[i * 3] * LY, sp[i * 3 + 1] * LY, sp[i * 3 + 2] * LY); if (d < bd) { const f = st.fate[i]; if (t < st.life[i * 3] || ((f === 1 || f === 3) && t > st.life[i * 3 + 2] + F.flash)) continue; if (appMag(st.mag[i]) - Rr.expo < 9.3) { bd = d; bp = [lx, ly, lz]; best = () => selStar2(i); } } } }
    if (Rr.comVis > 0.3) { const B = Rr.COM, k = AU * F.orb; for (let i = 0; i < B.N; i++) { const d = dpx(B.pos[i * 3] * k, B.pos[i * 3 + 1] * k, B.pos[i * 3 + 2] * k) - 4; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => orbPlus(selComet(i)); } } }
    if (Rr.exoVis > 0.3) { const P = Rr.EXO.pos; for (let i = 0; i < Rr.EXO.N; i++) { const d = dpx(P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY) - 3; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selExo(i); } } }
    if (Rr.psrVis > 0.3) { const P = Rr.PSR.pos; for (let i = 0; i < Rr.PSR.N; i++) { const d = dpx(P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY) - 3; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selPsr(i); } } }
    if (V.stars > 0.25 && Math.abs(S.ty) < 3e6) for (const T of Rr.tiles) if (T.kind === 'star') { const sp = T.pos, vl = T.vel, kv = S.ty * 2 * KMS_LY_YR;
      const scan = (i0, i1) => { for (let i = i0; i < i1; i++) { const j = i * 3, d = dpx((sp[j] + vl[j] * kv) * LY, (sp[j + 1] + vl[j + 1] * kv) * LY, (sp[j + 2] + vl[j + 2] * kv) * LY); if (d < bd && appMag(T.mag[i]) - Rr.expo < 9.3) { bd = d; bp = [lx, ly, lz]; best = () => selStarT(T, i); } } };
      if (T.leaves) { for (const L of T.leaves) if (L.dc) scan(L.a, L.a + L.dc); } else scan(0, T.draw); }
    if (V.surv > 0.25) for (const T of Rr.tiles) if (T.kind === 'gal') { const k = MPC * F.cos.a, cr = Rr.survCR, kp = Rr.keep2 * Rr.pick.keep; for (let i = 0; i < T.draw; i++) { const r = T.dist[i], pk = kp * Math.min(1, Math.pow(r / cr, 1.7)); if (pk - T.info[i * 3 + 1] < 0.1 * pk) continue; const d = dpx(F.gcRel[0] + T.dir[i * 3] * r * k, F.gcRel[1] + T.dir[i * 3 + 1] * r * k, F.gcRel[2] + T.dir[i * 3 + 2] * r * k); if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => survPlus(selSurv(i, T.P), T.P, i); } } }
    if (Rr.astVis > 0.3) for (const T of Rr.tiles) if (T.kind === 'ast') { const k = AU * (F.orb || 1), dt = F.jd - T.epoch, P = T.pos, Q = T.q, el = T.el; for (let i = 0; i < T.n; i++) { const j = i * 3, e = el[j], E = keplerE(wrapPi(el[j + 1] + el[j + 2] * dt), e), x = Math.cos(E) - e, y = Math.sin(E), d = dpx((P[j] * x + Q[j] * y) * k, (P[j + 1] * x + Q[j + 1] * y) * k, (P[j + 2] * x + Q[j + 2] * y) * k) - 2; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selAstT(T, i); } } }
    for (const t of kSets) if (t.vis > 0.3) for (const k of t.idx) { if (KO[k].off) continue; const d = dpx(kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]) - 5; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selMoon(k); } }
    if (Rr.bhsVis > 0.3) { const P = Rr.BHS.pos; for (let i = 0; i < Rr.BHS.N; i++) { const d = dpx(P[i * 3] * LY, P[i * 3 + 1] * LY, P[i * 3 + 2] * LY) - 6; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selBHS(i); } } }
    if (Rr.bhmVis > 0.3) { const P = Rr.BHM.pos, k = MPC * F.cos.a; for (let i = 0; i < Rr.BHM.N; i++) { const d = dpx(F.gcRel[0] + P[i * 3] * k, F.gcRel[1] + P[i * 3 + 1] * k, F.gcRel[2] + P[i * 3 + 2] * k) - 6; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selBHM(i); } } }
    if (S.logR > 17.6 && S.logR < 22.2) { const d = dpx(F.gcRel[0], F.gcRel[1], F.gcRel[2]) - 8; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selSgrA(); } }
    if (V.clusters > 0.25) { const c = Rr.clu; for (let i = 0; i < c.N; i++) { const d = dpx(c.pos[i * 3] * LY, c.pos[i * 3 + 1] * LY, c.pos[i * 3 + 2] * LY); if (d < bd && appMag(c.mag[i]) - Rr.expoC < 9.5) { bd = d; bp = [lx, ly, lz]; best = () => selCluster(i); } } }
    if (V.lg > 0.12) for (const c of G.lg.centers) { if (c.gone) continue; const d = dpx(F.gcRel[0] + c.c[0] * KPC, F.gcRel[1] + c.c[1] * KPC, F.gcRel[2] + c.c[2] * KPC) - 5; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selLG(c); } }
    if (V.near > 0.25) { const P = Rr.pick, k = MPC * F.cos.a; for (let i = 0; i < P.nN; i++) { const d = dpx(F.gcRel[0] + P.nPos[i * 3] * k, F.gcRel[1] + P.nPos[i * 3 + 1] * k, F.gcRel[2] + P.nPos[i * 3 + 2] * k) - 2; if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => selNear(i); } } }
    if (V.surv > 0.25) { const P = Rr.pick, k = MPC * F.cos.a, cr = Rr.survCR; for (let i = 0; i < P.svN; i++) { const r = P.svDist[i], pk = P.keep * Math.min(1, Math.pow(r / cr, 1.7)); if (pk - P.svInfo[i * 3 + 1] < 0.1 * pk) continue; const d = dpx(F.gcRel[0] + P.svDir[i * 3] * r * k, F.gcRel[1] + P.svDir[i * 3 + 1] * r * k, F.gcRel[2] + P.svDir[i * 3 + 2] * r * k); if (d < bd) { bd = d; bp = [lx, ly, lz]; best = () => survPlus(selSurv(i), Rr.pick, i); } } }
    if (posOnly) return bp;
    return best ? best() : null;
  }
  /* R2 : repère de l'objet suivi (anneau, nom, état à la date affichée), à toutes les échelles. Objet suivi : le centre du zoom (R1),
     sinon l'astre suivi s'il n'est pas le Soleil. Hors du champ, le repère reste au bord, du côté de l'objet ; derrière la caméra, il est masqué. */
  const SS_BORN = -4.567e9;      /* âge du système solaire : 4,567 milliards d'années (Connelly et al. 2012, inclusions CAI) */
  function bodyState(k) { if (S.ty < SS_BORN) return 'pas encore formée'; const p = k === 'moon' ? 'earth' : k; if (!F.eng[p]) return null;
    return p === 'mercury' || p === 'venus' ? 'engloutie par le Soleil (calculé)' : 'sort inconnu'; }
  function followInfo() { const o = S.center; if (o) return { name: o.name, pos: o.get(), st: o.exist ? o.exist() : null };
    if (S.focus !== 'sun') return { name: BODY[S.focus].name, pos: bodyPosM(S.focus), st: bodyState(S.focus) }; return null; }
  const FOL = $('follow'), folSc = [0, 0, 0]; let folKey = '';
  function updateFollow() { const fi = microOn() ? null : followInfo(), q = fi && fi.pos && isFinite(fi.pos[0]) ? Rr.project(fi.pos, F, folSc) : null;
    F.followOn = !!q; if (!q) { if (!FOL.hidden) FOL.hidden = true; return; }
    const W = Rr.cssW, H = Rr.cssH, x = clamp(q[0], 18, W - 18), y = clamp(q[1], 18, H - (hudBox.bar || 0) - 56)      /* nom et état restent au-dessus de la barre du temps */, key = fi.name + '|' + (fi.st || '');
    if (key !== folKey) { folKey = key; FOL.querySelector('b').textContent = fi.name; const sm = FOL.querySelector('small'); sm.textContent = fi.st || ''; sm.hidden = !fi.st; FOL.classList.toggle('gone', !!fi.st); }
    FOL.classList.toggle('edge', x !== q[0] || y !== q[1]); FOL.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)'; if (FOL.hidden) FOL.hidden = false; }
  /* R1 : l'objet touché devient le centre du zoom (molette, pincement, boutons, barre), sans changer l'échelle. Un événement de la chronologie
     n'a pas de position : il ne devient pas un centre. Fermer la fiche (select(null)) rend le centre en douceur (S.ck, 0,9 s). */
  function centerOn(o) { if (!o || o.isEvent) return; const p = o.get(); if (!p || !isFinite(p[0]) || !isFinite(p[1]) || !isFinite(p[2])) return; zoffReset(); S.center = o; renderCard(); }
  function select(o) { S.sel = o; if (!o) S.center = null; if (o && o.exoI !== undefined) setExoSystem(o.exoI, o.exoC ? o.get : null); Rr.setSelOrbit(o && o.orbit ? o.orbit : null); renderCard(); }
  function renderCard() {
    const sel = S.sel, body = !sel && (S.focus !== 'sun' || S.logR < 10.7) ? BODY[S.focus] : null, card = $('card'), mic = !sel && microOn() && S.logR < 3.2 ? microLevel(S.logR) : null;
    if (!sel && !body) { if (!card.hidden) card.hidden = true; return; }
    let rows;
    if (sel) { $('card-title').textContent = sel.name; $('card-sub').textContent = sel.sub; rows = sel.rows(); }
    else if (mic && mic.rows) { $('card-title').textContent = mic.name; $('card-sub').textContent = mic.sub; rows = typeof mic.rows === 'function' ? mic.rows() : mic.rows; }
    else { const s = F.sun; $('card-sub').textContent = body.info; rows = body.key === 'sun' ? [['État à cette date', s.phase], ['Rayon', sig(s.R, 3) + NBSP + 'fois l’actuel'], ['Éclat', sig(s.L, 3) + NBSP + 'fois l’actuel'], ['Température', nf(Math.round(s.T / 10) * 10, 0) + NBSP + 'K'], ['Masse', sig(s.M, 3) + NBSP + 'fois l’actuelle']].concat(Math.abs(S.ty) < 1e6 ? sunFacts() : [])
      : body.key === 'moon' ? [['Distance à la Terre', nf(Math.round(vlen(sol.moonGeo) * AU / 1e5) * 100, 0) + NBSP + 'km'], ['Orbite', 'de 363 300 à 405 500 km en moyenne'], ['Excentricité', '0,055'], ['Un tour de la Terre', '27,3 jours'], ['Vitesse sur l’orbite', '1,02 km/s en moyenne']].concat(factRows('moon'), [['Retour de la même phase', 'tous les 29,5 jours'], ['S’éloigne de la Terre de', '3,8 cm par an']]) : planetRows(body.key).concat(factRows(body.key), F.eng[body.key] ? [['État à cette date', 'engloutie par le Soleil']] : []); }
    const keep = innerWidth < 600 ? 4 : 7, many = rows.length > keep + 1, shown = many && !S.more ? rows.slice(0, keep) : rows, dl = $('card-dl'), top = dl.scrollTop; $('card-more').hidden = !many; if (many) $('card-more').textContent = S.more ? 'Moins de détails' : 'Plus de détails (' + (rows.length - keep) + ')';
    $('card-title').hidden = !sel && !(mic && mic.rows); dl.innerHTML = shown.map(r => '<dt>' + r[0] + '</dt><dd>' + r[1] + '</dd>').join(''); dl.scrollTop = top;
    $('card-center').hidden = !sel; $('card-close').hidden = !sel; $('card-back').hidden = !!sel; $('card-center').textContent = sel && sel.isEvent ? 'Revoir' : 'Y aller';
    if (card.hidden) card.hidden = false;
  }

  /* ---- le temps : événements réels, frise, dates ----
     Chaque événement porte sa date (mesurée, datée ou calculée ici), sa source et son degré de certitude.
     Avant le 15 octobre 1582, les dates sont données dans le calendrier julien, celui des chroniques. */
  const closest = (name, t0, t1, st) => { const l = DATA.STAR_LABELS.find(l => l.n === name), o = new Float32Array(Rr.star.N * 3); let b = [0, 1e9]; if (!l) return b; for (let t = t0; t <= t1; t += st) { starPositions(Rr.K, t, t / 1e9, o, l.i, l.i + 1); const d = Math.hypot(o[l.i * 3], o[l.i * 3 + 1], o[l.i * 3 + 2]); if (d < b[1]) b = [t, d]; } return b; };
  const EV_AC = closest('Alpha du Centaure', 0, 6e4, 100), EV_GL = closest('Gliese 710', 1.0e6, 1.6e6, 500);
  const EVCAT = { U: 'Univers', G: 'Voie lactée et étoiles', S: 'Système solaire', T: 'Terre et vie', H: 'Ciel observé et exploration', O: 'Ondes gravitationnelles' }, EVCONF = { C: 'Certain', P: 'Probable', S: 'Supposition (modèle ou estimation)', V: 'Contesté, à vérifier' };
  const isoJd = s => { const jul = s[0] === 'J', m = (jul ? s.slice(1) : s).match(/^(-?\d+)-(\d\d)-(\d\d)(?:T(\d\d):(\d\d))?$/); return jdFromCal(+m[1], +m[2], +m[3], jul) + (m[4] ? (+m[4] + (+m[5]) / 60) / 24 : 0.5); };
  const jyr = y => (jdFromCal(y, 1, 1, y < 1583) - JD_NOW) / 365.25;
  const H3 = 3 * 3600 / YEAR_S, D1 = DAY_S / YEAR_S, FLY = { sp: 3600 / YEAR_S, lead: 8 / 8766, sim: 'Vue centrée sur la planète : la sonde est le point qui porte son nom. Sa trajectoire est réelle (JPL Horizons), la planète est à sa position calculée. Les lunes ne sont pas à leur place réelle à cette date.' };
  const EV_RAW = [
    // ---------------- Univers
    [{ a: 0 }, 'U', 1, 'Big Bang', 'Début de l’expansion : tout l’univers observable est concentré, brûlant et dense. La simulation commence 100 000 ans plus tard ; avant, il n’y a qu’un plasma uniforme à montrer.', 'C', 'Âge de l’univers : 13,787 ± 0,020 milliards d’années (Planck 2018)', 'u', { lab: 'Instant zéro' }],
    [{ a: 0 }, 'U', 2, 'Inflation', 'En une fraction de seconde, l’univers grossit d’un facteur gigantesque. C’est une théorie solide, appuyée par le fond diffus, mais pas une observation directe.', 'P', 'Guth 1981 ; contraintes de Planck 2018', 'u', { lab: 'Première fraction de seconde' }],
    [{ a: 0 }, 'U', 2, 'Premiers noyaux d’atomes', 'Protons et neutrons s’assemblent : environ 75 % d’hydrogène et 25 % d’hélium en masse, avec des traces de deutérium et de lithium. Ces proportions se mesurent encore aujourd’hui.', 'C', 'Nucléosynthèse primordiale (Particle Data Group 2024)', 'u', { lab: 'De 3 à 20 minutes après le Big Bang' }],
    [{ z: 3402 }, 'U', 3, 'La matière prend le dessus', 'La matière devient plus dense que le rayonnement : la gravité commence à rassembler la matière noire en grumeaux.', 'C', 'z = 3402 ± 26 (Planck 2018)', 'u'],
    [{ z: 1089.92 }, 'U', 1, 'L’univers devient transparent', 'La température tombe vers 3 000 K : les électrons se lient aux noyaux et la lumière circule enfin librement. Cette lumière, étirée par l’expansion, est le fond diffus cosmologique.', 'C', 'z = 1089,92 ± 0,25 (Planck 2018)', 'u', { sp: 6e4, sim: 'La lueur de fond suit la température du rayonnement, calculée avec le modèle cosmologique de la page.' }],
    [{ a: 3e6 }, 'U', 2, 'Début des âges sombres', 'La lueur du Big Bang a glissé dans l’infrarouge. Aucune étoile n’existe encore : l’univers reste noir pendant plus de cent millions d’années.', 'C', 'Refroidissement du rayonnement : T = 2,725 K × (1 + z)', 'u', { sp: 2e5 }],
    [{ z: 20 }, 'U', 1, 'Premières étoiles', 'Les premiers nuages d’hydrogène s’effondrent et s’allument : des étoiles très massives, sans éléments lourds. Aucune n’a encore été observée directement ; la date est une estimation.', 'P', 'Simulations (Bromm et Yoshida 2011) ; galaxies déjà évoluées vues par Webb', 'w'],
    [{ z: 14.44 }, 'U', 2, 'La plus lointaine galaxie connue', 'MoM-z14 : sa lumière part maintenant. Elle est minuscule, très lumineuse et déjà riche en azote. Record confirmé en janvier 2026.', 'C', 'z = 14,44 (Naidu et al. 2026, télescope Webb)', 'w'],
    [{ z: 10.6 }, 'U', 3, 'Galaxie GN-z11', 'Repérée par Hubble, confirmée par Webb : une galaxie déjà brillante, avec un trou noir actif en son centre.', 'C', 'z = 10,60 (Bunker et al. 2023)', 'w'],
    [{ z: 7.67 }, 'U', 2, 'Réionisation à mi-parcours', 'Le rayonnement des premières étoiles arrache de nouveau les électrons de l’hydrogène qui remplit l’espace : la moitié du gaz est ionisée.', 'C', 'z = 7,67 ± 0,73 (Planck 2018)', 'w'],
    [{ z: 7.642 }, 'U', 3, 'Le plus lointain quasar connu', 'Un trou noir de 1,6 milliard de masses solaires avale déjà de la matière. Comment il a grossi si vite reste une question ouverte.', 'C', 'J0313−1806, z = 7,642 (Wang et al. 2021)', 'w'],
    [{ z: 5.3 }, 'U', 3, 'Fin de la réionisation', 'Presque tout l’hydrogène entre les galaxies est ionisé : l’univers est transparent aux ultraviolets, comme aujourd’hui.', 'P', 'z ≈ 5,3 (Bosman et al. 2022)', 'w'],
    [{ z: 1.9 }, 'U', 1, 'Pic de formation d’étoiles', 'Les galaxies fabriquent des étoiles environ dix fois plus vite qu’aujourd’hui. Depuis, le rythme ne cesse de baisser.', 'C', 'z ≈ 1,9 (Madau et Dickinson 2014)', 'w'],
    [-1.3e9, 'U', 3, 'Deux trous noirs fusionnent au loin', 'À environ 1,3 milliard d’années-lumière, deux trous noirs de 36 et 29 masses solaires fusionnent. L’onde gravitationnelle atteindra la Terre le 14 septembre 2015.', 'P', 'GW150914 : 410 (+160/−180) Mpc (Abbott et al. 2016)', 'w'],
    // ---------------- Voie lactée et étoiles
    [-13.0e9, 'G', 1, 'La Voie lactée commence à se former', 'Le disque épais de notre galaxie se met à fabriquer des étoiles ; les plus vieilles étoiles connues ont cet âge.', 'P', 'Xiang et Rix 2022 (Nature) : il y a environ 13 milliards d’années', 'g'],
    [-10e9, 'G', 1, 'Fusion avec la galaxie Gaia-Encelade', 'Une galaxie naine, environ quatre fois moins massive que la Voie lactée d’alors, est absorbée. Ses étoiles forment aujourd’hui une grande partie du halo.', 'P', 'Helmi et al. 2018 ; Belokurov et al. 2018 (données Gaia) : il y a 8 à 11 milliards d’années', 'g'],
    [-8.5e9, 'G', 2, 'Le disque mince se met en place', 'Après la période agitée des fusions, le gaz se pose dans un disque fin où naîtront la plupart des étoiles actuelles, dont le Soleil.', 'P', 'Haywood et al. 2013 ; Xiang et Rix 2022', 'g'],
    [-7.6e9, 'G', 3, 'Naissance de TRAPPIST-1', 'Cette petite étoile rouge et ses sept planètes sont plus vieilles que le Soleil.', 'P', 'Âge 7,6 ± 2,2 milliards d’années (Burgasser et Mamajek 2017)', 'g'],
    [-5.7e9, 'G', 2, 'Premier passage de la naine du Sagittaire', 'Cette galaxie naine traverse le disque et y déclenche une flambée de naissances d’étoiles. Deux autres passages suivront, il y a 1,9 puis 1 milliard d’années.', 'P', 'Ruiz-Lara et al. 2020 (Nature Astronomy)', 'g'],
    [-5.3e9, 'G', 3, 'Naissance d’Alpha du Centaure', 'Nos plus proches voisines sont un peu plus âgées que le Soleil.', 'P', 'Âge 5,3 ± 0,3 milliards d’années (Joyce et Chaboyer 2018)', 'g'],
    [-1.9e9, 'G', 3, 'Deuxième passage de la naine du Sagittaire', 'Nouvelle flambée de formation d’étoiles dans le disque.', 'P', 'Ruiz-Lara et al. 2020', 'g'],
    [-2.28e8, 'G', 3, 'Naissance de Sirius', 'Sirius A et sa compagne naissent ensemble. La compagne, plus massive, est devenue une naine blanche il y a environ 126 millions d’années.', 'P', 'Âge 228 ± 10 millions d’années (Bond et al. 2017)', 'n'],
    [-1.2e8, 'G', 3, 'Naissance des Pléiades', 'Un millier d’étoiles naissent du même nuage.', 'P', 'Âge 110 à 130 millions d’années (Dahm 2015)', 'n'],
    [-1.44e7, 'G', 2, 'La Bulle locale commence à se creuser', 'Une série de supernovas souffle une cavité de 1 000 années-lumière dans le gaz interstellaire. Le Soleil y est entré il y a environ 5 millions d’années.', 'P', 'Zucker et al. 2022 (Nature)', 'n'],
    [-9e6, 'G', 3, 'Naissance de Bételgeuse', 'Une étoile d’une vingtaine de masses solaires naît dans Orion. Elle brûle si vite qu’elle est déjà en fin de vie.', 'P', 'Âge 8 à 10 millions d’années (Dolan et al. 2016)', 'n'],
    [-3.5e6, 'G', 2, 'Éruption du trou noir central', 'Sagittarius A* avale une grande quantité de gaz et souffle deux bulles géantes, encore visibles en rayons gamma (bulles de Fermi).', 'P', 'Bland-Hawthorn et al. 2019 : il y a 3,5 ± 1 million d’années', 'g'],
    [-2.6e6, 'G', 3, 'Une supernova explose près du Soleil', 'À une distance de 150 à 300 années-lumière. Sa poussière, riche en fer 60, se retrouve au fond des océans.', 'P', 'Knie et al. 2004 ; Wallner et al. 2016', 'n'],
    [-1.68e5, 'G', 2, 'L’étoile de la supernova 1987A explose', 'Dans le Grand Nuage de Magellan, une supergéante bleue s’effondre. Sa lumière mettra 168 000 ans à nous parvenir.', 'C', 'Distance 51,4 kpc (Panagia 1999)', '@Grand Nuage de Magellan'],
    // ---------------- Système solaire
    [-4.568e9, 'S', 1, 'Naissance du Soleil', 'Un nuage de gaz et de poussière s’effondre. Au centre, le Soleil s’allume ; autour, un disque où naîtront les planètes.', 'C', 'Premiers solides du système solaire : 4 567,30 ± 0,16 millions d’années (Connelly et al. 2012)', 's', { sp: 2e6, lead: 4e6 }],
    [-4.5665e9, 'S', 2, 'Jupiter grossit en premier', 'En moins d’un million d’années, le cœur de Jupiter atteint 20 fois la masse de la Terre, puis il aspire le gaz du disque. Saturne suit.', 'P', 'Kruijer et al. 2017 (météorites)', 's'],
    [-4.563e9, 'S', 3, 'Le disque de gaz se dissipe', 'Environ 4 millions d’années après les premiers solides, le gaz restant a disparu : les planètes géantes ne peuvent plus grossir.', 'P', 'Wang et al. 2017 (Science)', 's'],
    [-4.54e9, 'S', 1, 'La Terre est formée', 'Par collisions successives de corps de plus en plus gros, la Terre atteint presque sa masse finale.', 'C', 'Âge de la Terre : 4,54 ± 0,05 milliards d’années (Patterson 1956 ; Dalrymple 2001)', 'i'],
    [-4.52e9, 'S', 2, 'Les planètes géantes changent d’orbite', 'Jupiter, Saturne, Uranus et Neptune se perturbent et migrent ; d’innombrables petits corps sont éjectés ou précipités vers le Soleil. La date est débattue.', 'S', 'Modèle de Nice (Tsiganis et al. 2005) ; datation révisée par Nesvorný et al. 2018', 's'],
    [-4.51e9, 'S', 1, 'Un impact géant forme la Lune', 'Un corps de la taille de Mars, Théia, percute la jeune Terre. Les débris mis en orbite s’assemblent pour former la Lune.', 'P', 'Barboni et al. 2017 : il y a au moins 4,51 milliards d’années', 'e'],
    [-3.92e9, 'S', 2, 'Naissance de la mer des Pluies, sur la Lune', 'Un astéroïde d’environ 250 km creuse le bassin Imbrium, la grande tache sombre visible à l’œil nu.', 'P', 'Échantillons Apollo : 3,92 milliards d’années (Nemchin et al. 2021)', 'e'],
    [-3.7e9, 'S', 2, 'Mars perd son champ magnétique', 'Le cœur de Mars cesse d’entretenir un champ magnétique ; le vent solaire arrache peu à peu l’atmosphère et l’eau liquide disparaît de la surface.', 'P', 'Mittelholz et al. 2020 : dynamo encore active il y a 3,7 milliards d’années', 'i'],
    [-2.023e9, 'S', 3, 'Le plus grand cratère connu sur Terre', 'Un astéroïde de 20 à 25 km creuse le cratère de Vredefort, en Afrique du Sud : 250 à 280 km de diamètre à l’origine.', 'C', 'Kamo et al. 1996 : 2 023 ± 4 millions d’années', 'e'],
    [-3e8, 'S', 3, 'Naissance possible des anneaux de Saturne', 'Les anneaux pourraient n’avoir que quelques centaines de millions d’années, nés d’une lune ou d’une comète déchiquetée. D’autres travaux les jugent aussi vieux que Saturne.', 'V', 'Iess et al. 2019 ; Kempf et al. 2023 ; avis contraire : Hyodo et al. 2024', 's'],
    [-6.604e7, 'S', 1, 'Un astéroïde frappe le Yucatán', 'Un astéroïde d’environ 10 km creuse le cratère de Chicxulub. Hiver d’impact et incendies : trois quarts des espèces disparaissent, dont les dinosaures non aviens.', 'C', 'Renne et al. 2013 : 66,04 ± 0,05 millions d’années', 'e'],
    [-5e4, 'S', 3, 'Meteor Crater', 'Une météorite de fer de 50 m creuse un cratère de 1,2 km en Arizona.', 'C', 'Environ 50 000 ans (Nishiizumi et al. 1991)', 'e'],
    ['J1066-03-20', 'S', 3, 'Passage de la comète de Halley', 'Elle apparaît peu avant la bataille d’Hastings et figure sur la tapisserie de Bayeux.', 'C', 'Périhélie le 20 mars 1066 (Yeomans et Kiang 1981)', 's', { sim: 'À cette date ancienne, la comète affichée n’est pas à sa position réelle : son orbite a été modifiée depuis par les planètes.' }],
    ['1759-03-13', 'S', 2, 'La comète de Halley revient comme prévu', 'Edmond Halley avait annoncé en 1705 le retour de la comète de 1682. Elle passe au plus près du Soleil le 13 mars 1759 : les comètes obéissent aux lois de Newton.', 'C', 'Halley 1705 ; Clairaut 1758', 's', { sim: 'À cette date ancienne, la comète affichée n’est pas à sa position réelle.' }],
    ['1908-06-30T00:14', 'S', 2, 'Explosion de la Toungouska', 'Un corps de 50 à 60 m explose à quelques kilomètres d’altitude au-dessus de la Sibérie et couche 2 000 km² de forêt.', 'C', 'Relevés sismiques et barométriques de 1908', 'e'],
    ['1910-04-20', 'S', 3, 'Passage de la comète de Halley', 'La Terre traverse la queue de la comète le 19 mai.', 'C', 'Périhélie le 20 avril 1910', 's'],
    ['1986-02-09', 'S', 2, 'Passage de la comète de Halley', 'Périhélie le 9 février. Cinq sondes vont à sa rencontre ; Giotto passe à 596 km du noyau le 14 mars.', 'C', 'ESA (mission Giotto)', '@Halley|12.6', { sp: 4 * D1, lead: 0.1 }],
    ['1989-09-05', 'S', 3, 'Pluton au plus près du Soleil', 'À 29,7 UA. De 1979 à 1999, Pluton est plus proche du Soleil que Neptune.', 'C', 'JPL Horizons', 's'],
    ['1994-07-16T20:13', 'S', 2, 'Une comète percute Jupiter', 'Brisée en 21 fragments, la comète Shoemaker-Levy 9 tombe sur Jupiter du 16 au 22 juillet : premier choc entre deux corps du système solaire observé en direct.', 'C', 'Télescope Hubble et sonde Galileo', '@Jupiter'],
    ['1997-04-01', 'S', 2, 'La comète Hale-Bopp au plus près du Soleil', 'Visible à l’œil nu pendant 18 mois, un record. Elle ne reviendra que vers l’an 4385.', 'C', 'JPL Small-Body Database', 's'],
    ['2011-07-12', 'S', 3, 'Neptune boucle son premier tour depuis sa découverte', 'Une année de Neptune dure 164,8 ans : découverte en 1846, elle revient au même point.', 'C', 'Calcul d’éphémérides', 's'],
    ['2012-06-06T01:29', 'S', 2, 'Dernier transit de Vénus', 'Vénus passe exactement entre la Terre et le Soleil. Le prochain aura lieu en décembre 2117.', 'C', 'NASA (Espenak)', 'i', { sp: 6 * 3600 / YEAR_S, lead: 2 / 365.25 }],
    ['2013-02-15T03:20', 'S', 2, 'Météore de Tcheliabinsk', 'Un astéroïde de 18 m explose à 30 km d’altitude au-dessus de la Russie : l’onde de choc blesse environ 1 500 personnes.', 'C', 'Popova et al. 2013 (Science)', 'e'],
    ['2017-09-09', 'S', 2, 'Premier visiteur interstellaire : ʻOumuamua', 'Un objet venu d’un autre système stellaire passe à 0,26 UA du Soleil. Il n’est repéré que le 19 octobre, déjà en train de repartir.', 'C', 'Meech et al. 2017 (Nature)', 'i'],
    ['2019-11-11T15:20', 'S', 3, 'Transit de Mercure', 'Mercure passe devant le Soleil vu de la Terre. Prochain transit : 13 novembre 2032.', 'C', 'NASA (Espenak)', 'i', { sp: 6 * 3600 / YEAR_S, lead: 2 / 365.25 }],
    ['2019-12-08', 'S', 3, 'Comète interstellaire Borisov', 'Deuxième visiteur interstellaire, au plus près du Soleil à 2,0 UA.', 'C', 'JPL Small-Body Database', 's'],
    ['2020-12-21T18:20', 'S', 2, 'Grande conjonction de Jupiter et Saturne', 'Vues de la Terre, les deux planètes ne sont séparées que de 0,1 degré : leur rapprochement le plus serré depuis 1623.', 'C', 'Calcul d’éphémérides', 's', { sp: 10 * D1, lead: 0.5 }],
    ['2024-09-27', 'S', 3, 'Comète Tsuchinshan-ATLAS', 'La comète C/2023 A3 passe au plus près du Soleil, puis devient visible à l’œil nu en octobre.', 'C', 'JPL Small-Body Database', 's'],
    ['2025-10-29', 'S', 2, 'Comète interstellaire 3I/ATLAS', 'Troisième visiteur interstellaire, découvert le 1er juillet 2025 ; au plus près du Soleil à 1,36 UA.', 'C', 'JPL Small-Body Database ; Minor Planet Center', 's'],
    ['2029-04-13T21:46', 'S', 1, 'L’astéroïde Apophis frôle la Terre', 'Un astéroïde de 340 m passe à environ 32 000 km de la surface, sous les satellites géostationnaires. Visible à l’œil nu ; aucun risque d’impact.', 'C', 'JPL (Center for Near-Earth Object Studies)', 'e', { sim: 'Apophis n’est pas dans le catalogue d’astéroïdes de la page : seuls la Terre et la Lune sont montrées.' }],
    ['2032-11-13T08:54', 'S', 3, 'Transit de Mercure', 'Mercure passe devant le Soleil vu de la Terre.', 'C', 'NASA (Espenak)', 'i', { sp: 6 * 3600 / YEAR_S, lead: 2 / 365.25 }],
    ['2061-07-28', 'S', 1, 'Prochain passage de la comète de Halley', 'Périhélie calculé le 28 juillet 2061.', 'C', 'JPL Horizons', '@Halley|12.6', { sp: 4 * D1, lead: 0.1 }],
    ['2117-12-11T02:48', 'S', 2, 'Prochain transit de Vénus', 'Vénus repasse exactement entre la Terre et le Soleil, 105 ans après le précédent.', 'C', 'NASA (Espenak)', 'i', { sp: 6 * 3600 / YEAR_S, lead: 2 / 365.25 }],
    [1e8, 'S', 3, 'Anneaux de Saturne : sort inconnu', 'Leurs glaces tombent en pluie sur la planète. Leur durée de vie est au plus d’environ 300 millions d’années selon O’Donoghue et al. 2019 ; l’apport de matière mesuré par la sonde Cassini est compatible avec 100 millions. Au-delà de 100 millions d’années, ils ne sont plus dessinés.', 'S', 'O’Donoghue et al. 2019 (Icarus 322, 251) ; mesures de Cassini', '@Saturne'],
    [1.4e9, 'S', 3, 'Triton : sort inconnu', 'Triton tourne à l’envers et se rapproche lentement de Neptune : il finira brisé par les marées, dans environ 1,4 ou 3,6 milliards d’années selon l’état de sa rotation, que l’on ne connaît pas. Au-delà de 1,4 milliard d’années, il n’est plus dessiné.', 'S', 'Chyba, Jankowski et Nicholson 1989 (A&A 219, L23)', '@Neptune'],
    [3.77e10, 'S', 1, 'Le système solaire se défait : suite inconnue', 'Les orbites, élargies par la mort du Soleil, sont déréglées par les étoiles qui passent : les simulations déclenchent l’instabilité environ 30 milliards d’années après la mort du Soleil, puis éjectent les planètes géantes sur environ 10 milliards d’années ; la dernière part en moyenne 100 milliards d’années après la mort du Soleil. L’ordre et les dates ne sont pas connus, et Mars n’était pas simulé : à partir d’ici, plus aucune planète n’est dessinée.', 'S', 'Zink, Batygin et Adams 2020 (Astronomical Journal 160, 232)', 's', { sp: 4e8 }],
    [2e7, 'S', 3, 'Phobos : sort inconnu', 'Phobos descend de 1,8 cm par an : il se brisera en anneau ou s’écrasera sur Mars d’ici 20 à 40 millions d’années. Au-delà de 20 millions d’années, il n’est plus dessiné.', 'P', 'Black et Mittal 2015 (Nature Geoscience 8, 913)', 'i'],
    // ---------------- Terre et vie
    [-4.404e9, 'T', 2, 'Plus vieux minéraux connus', 'Des zircons cristallisent en Australie occidentale : leur chimie indique déjà une croûte et de l’eau liquide.', 'C', 'Zircons de Jack Hills : 4,404 ± 0,008 milliards d’années (Wilde et al. 2001)', 'e'],
    [-4.2e9, 'T', 2, 'Dernier ancêtre commun de tous les vivants', 'Toutes les espèces actuelles descendent d’une même cellule, qui vivait probablement déjà à cette époque. La date vient des horloges moléculaires.', 'P', 'Moody et al. 2024 : 4,2 milliards d’années (de 4,09 à 4,33)', 'e'],
    [-3.48e9, 'T', 1, 'Plus anciennes traces de vie reconnues', 'Des tapis de microbes laissent des structures fossiles, les stromatolites, en Australie. Des traces plus anciennes (3,7 milliards d’années, Groenland) sont débattues.', 'C', 'Formation de Dresser (Van Kranendonk et al. 2008) ; Nutman et al. 2016', 'e'],
    [-2.43e9, 'T', 1, 'L’oxygène envahit l’atmosphère', 'Des bactéries produisent de l’oxygène par photosynthèse : il s’accumule dans l’air pour la première fois.', 'C', 'Grande Oxydation, à partir de 2,43 milliards d’années (Gumsley et al. 2017)', 'e'],
    [-1.65e9, 'T', 2, 'Premières cellules à noyau', 'Les plus anciens fossiles d’eucaryotes, la lignée des animaux, des plantes et des champignons.', 'P', 'Environ 1,65 milliard d’années (Javaux et Lepot 2018)', 'e'],
    [-7.17e8, 'T', 2, 'La Terre devient une boule de neige', 'Les glaces atteignent les tropiques pendant près de 60 millions d’années, puis de nouveau vers 640 millions d’années.', 'C', 'Glaciation sturtienne : de 717 à 660 millions d’années (Rooney et al. 2015)', 'e'],
    [-5.74e8, 'T', 2, 'Premiers grands organismes', 'La faune d’Ediacara : des êtres mous, de quelques centimètres à un mètre, premiers organismes complexes visibles à l’œil nu.', 'C', 'À partir de 574 millions d’années (Matthews et al. 2021)', 'e'],
    [-5.388e8, 'T', 1, 'Explosion cambrienne', 'En une vingtaine de millions d’années apparaissent presque tous les grands groupes d’animaux : yeux, coquilles, pattes articulées.', 'C', 'Début du Cambrien : 538,8 ± 0,2 millions d’années (échelle des temps géologiques, ICS)', 'e'],
    [-4.7e8, 'T', 2, 'Les plantes sortent de l’eau', 'Les premières plantes terrestres, proches des mousses, colonisent les rivages.', 'P', 'Spores fossiles d’environ 470 millions d’années (Rubinstein et al. 2010)', 'e'],
    [-4.45e8, 'T', 2, 'Extinction de la fin de l’Ordovicien', 'Une glaciation brutale fait disparaître environ 85 % des espèces marines.', 'C', 'Il y a 445 à 443 millions d’années (Harper et al. 2014)', 'e'],
    [-3.75e8, 'T', 2, 'Des poissons se hissent hors de l’eau', 'Tiktaalik, un poisson muni d’un cou et d’ébauches de pattes : la lignée des vertébrés terrestres.', 'C', 'Daeschler et al. 2006 : 375 millions d’années', 'e'],
    [-3.72e8, 'T', 3, 'Extinction du Dévonien tardif', 'Les océans perdent leur oxygène à plusieurs reprises : environ 75 % des espèces disparaissent.', 'C', 'Crise de Kellwasser, il y a 372 millions d’années', 'e'],
    [-3.35e8, 'T', 3, 'La Pangée s’assemble', 'Tous les continents se soudent en un seul.', 'C', 'Stampfli et al. 2013', 'e'],
    [-2.5194e8, 'T', 1, 'La plus grande extinction', 'Des éruptions gigantesques en Sibérie bouleversent le climat et les océans : 80 à 90 % des espèces marines disparaissent en moins de 100 000 ans.', 'C', 'Burgess et al. 2014 : 251,94 ± 0,04 millions d’années', 'e'],
    [-2.32e8, 'T', 2, 'Premiers dinosaures', 'De petits dinosaures bipèdes apparaissent ; ils domineront les continents pendant 165 millions d’années.', 'C', 'Formation d’Ischigualasto, 231 à 233 millions d’années (Martínez et al. 2011)', 'e'],
    [-2.0156e8, 'T', 3, 'Extinction de la fin du Trias', 'L’ouverture de l’Atlantique s’accompagne d’éruptions massives ; les dinosaures en sortent gagnants.', 'C', 'Blackburn et al. 2013 : 201,56 millions d’années', 'e'],
    [-1.5e8, 'T', 3, 'Archéoptéryx', 'Un dinosaure à plumes capable de voler : les oiseaux sont des dinosaures.', 'C', 'Calcaires de Solnhofen, 150 millions d’années', 'e'],
    [-5.6e7, 'T', 3, 'Coup de chaud planétaire', 'En quelques milliers d’années, la température monte de 5 à 8 °C : un analogue naturel du réchauffement actuel.', 'C', 'Maximum thermique Paléocène-Éocène (McInerney et Wing 2011)', 'e'],
    [-7e6, 'T', 2, 'Premiers hominines', 'La lignée humaine se sépare de celle des chimpanzés ; Sahelanthropus (« Toumaï »), au Tchad, en est l’un des plus anciens représentants possibles.', 'P', 'Brunet et al. 2002 : environ 7 millions d’années', 'e'],
    [-3.3e6, 'T', 3, 'Premiers outils de pierre', 'Des pierres taillées à Lomekwi, au Kenya, avant même le genre Homo.', 'C', 'Harmand et al. 2015 : 3,3 millions d’années', 'e'],
    [-2.8e6, 'T', 2, 'Genre Homo', 'Le plus ancien fossile attribué au genre Homo, une mâchoire trouvée en Éthiopie.', 'C', 'Villmoare et al. 2015 : 2,8 millions d’années', 'e'],
    [-3.15e5, 'T', 1, 'Homo sapiens', 'Les plus anciens fossiles de notre espèce, à Jebel Irhoud, au Maroc.', 'C', 'Hublin et al. 2017 : 315 ± 34 milliers d’années', 'e'],
    [-7.39e4, 'T', 3, 'Super-éruption du Toba', 'À Sumatra, la plus grande éruption des deux derniers millions d’années.', 'C', 'Storey et al. 2012 : 73 880 ± 320 ans', 'e'],
    [-3.6e4, 'T', 3, 'Peintures de la grotte Chauvet', 'Parmi les plus anciennes œuvres figuratives connues.', 'C', 'Quiles et al. 2016 : environ 36 000 ans', 'e'],
    [-2.1e4, 'T', 3, 'Dernier maximum glaciaire', 'Les calottes couvrent le Canada et le nord de l’Europe ; le niveau des mers est 125 m plus bas.', 'C', 'Clark et al. 2009 : de 26 500 à 19 000 ans', 'e'],
    [-1.17e4, 'T', 2, 'Fin de la dernière glaciation', 'Début de l’Holocène, la période chaude et stable où naissent l’agriculture puis les villes.', 'C', 'Walker et al. 2009 : il y a 11 700 ans', 'e'],
    [-5325, 'T', 2, 'Invention de l’écriture', 'Des tablettes d’argile gravées à Uruk, en Mésopotamie.', 'C', 'Vers 3300 av. J.-C.', 'e'],
    [2.5e8, 'T', 3, 'Un nouveau supercontinent', 'Les continents se ressoudent ; le climat y serait trop chaud pour la plupart des mammifères.', 'S', 'Farnsworth et al. 2023 (Nature Geoscience)', 'e'],
    [6e8, 'T', 2, 'La photosynthèse s’épuise', 'Le Soleil chauffe davantage et le gaz carbonique de l’air s’effondre : la plupart des plantes ne peuvent plus vivre.', 'S', 'Lenton et von Bloh 2001 ; O’Malley-James et al. 2013', 'e'],
    // ---------------- Ciel observé et exploration
    ['J0185-12-07', 'H', 3, 'Plus ancienne supernova consignée', 'Des astronomes chinois notent une « étoile invitée » visible huit mois.', 'P', 'Livre des Han postérieurs', 'n'],
    ['J1006-05-01', 'H', 2, 'Supernova de 1006', 'L’étoile la plus brillante jamais consignée : visible en plein jour, elle projette des ombres la nuit.', 'C', 'Chroniques d’Égypte, de Chine, du Japon et d’Europe', 'n'],
    ['J1054-07-04', 'H', 1, 'Supernova de 1054', 'Une étoile explose dans le Taureau : elle reste visible 23 jours en plein jour. Ses restes forment la nébuleuse du Crabe, avec un pulsar au centre.', 'C', 'Chroniques chinoises (dynastie Song)', 'n'],
    ['J1543-05-01', 'H', 2, 'Copernic place le Soleil au centre', 'Publication de son traité sur les révolutions des sphères célestes.', 'C', 'Copernic 1543', 's'],
    ['J1572-11-11', 'H', 2, 'Supernova de Tycho', 'Tycho Brahe montre que cette « nouvelle étoile » est bien plus loin que la Lune : le ciel n’est pas immuable.', 'C', 'Tycho Brahe, De nova stella (1573)', 'n'],
    ['1604-10-09', 'H', 2, 'Supernova de Kepler', 'La dernière supernova de notre galaxie vue à l’œil nu.', 'C', 'Kepler, De stella nova (1606)', 'n'],
    ['1610-01-07', 'H', 1, 'Galilée découvre les lunes de Jupiter', 'Avec une lunette de sa fabrication, il voit quatre points tourner autour de Jupiter : tout ne tourne pas autour de la Terre.', 'C', 'Galilée, Sidereus Nuncius (1610)', '@Jupiter', { sim: 'Jupiter est à sa position calculée ; ses lunes ne sont pas à leur place réelle à cette date.' }],
    ['1676-12-07', 'H', 3, 'La lumière a une vitesse', 'En chronométrant les éclipses de Io, Ole Rømer montre que la lumière met environ 11 minutes à parcourir la distance Terre-Soleil (valeur réelle : 8 min 19 s).', 'C', 'Rømer 1676', '@Jupiter'],
    ['1687-07-15', 'H', 1, 'Newton publie la gravitation universelle', 'Une seule loi explique la chute des corps et le mouvement des planètes.', 'C', 'Newton, Principia (1687)', 's'],
    ['1769-06-03T22:25', 'H', 2, 'Transit de Vénus observé dans le monde entier', 'Des expéditions, dont celle de Cook à Tahiti, chronomètrent le passage de Vénus devant le Soleil pour mesurer la distance Terre-Soleil.', 'C', 'NASA (Espenak), catalogue des transits', 'i', { sp: 6 * 3600 / YEAR_S, lead: 2 / 365.25 }],
    ['1781-03-13', 'H', 2, 'Découverte d’Uranus', 'William Herschel repère une « comète » qui se révèle être une planète : la première découverte au télescope.', 'C', 'Herschel 1781', '@Uranus'],
    ['1801-01-01', 'H', 3, 'Découverte de Cérès', 'Giuseppe Piazzi trouve le premier astéroïde, entre Mars et Jupiter.', 'C', 'Piazzi 1801', 's'],
    ['1838-12-01', 'H', 2, 'Première distance d’une étoile', 'Friedrich Bessel mesure la parallaxe de 61 du Cygne : 10,4 années-lumière (valeur actuelle : 11,4).', 'C', 'Bessel 1838', 'n'],
    ['1846-09-23', 'H', 2, 'Découverte de Neptune', 'Johann Galle trouve Neptune à moins d’un degré de la position calculée par Urbain Le Verrier d’après les écarts d’Uranus.', 'C', 'Galle 1846 ; Le Verrier 1846', '@Neptune'],
    ['1859-09-01T11:18', 'H', 3, 'Tempête solaire de Carrington', 'La plus forte tempête géomagnétique consignée : aurores jusqu’aux tropiques, télégraphes en panne.', 'C', 'Carrington 1859', 'e'],
    ['1915-11-25', 'H', 1, 'Relativité générale', 'Einstein présente les équations qui relient la gravitation à la courbure de l’espace-temps. Elles expliquent l’avance du périhélie de Mercure.', 'C', 'Einstein 1915', 'i'],
    ['1919-05-29T13:08', 'H', 1, 'L’éclipse qui confirme Einstein', 'Pendant cette éclipse totale, Eddington et Dyson mesurent la déviation de la lumière des étoiles par le Soleil, conforme à la relativité générale.', 'C', 'Dyson, Eddington et Davidson 1920', 'e', { sp: 1800 / YEAR_S, lead: 0.1 / 365.25, sim: 'Terre et Lune à leur position calculée : l’axe de l’ombre de la Lune (trait gris) touche la Terre.' }],
    ['1925-01-01', 'H', 1, 'Il existe d’autres galaxies', 'Grâce à des étoiles variables, Edwin Hubble montre qu’Andromède est bien au-delà de la Voie lactée.', 'C', 'Hubble 1925', '@Andromède'],
    ['1929-03-15', 'H', 1, 'L’univers est en expansion', 'Hubble publie la relation entre distance et vitesse des galaxies, que Georges Lemaître avait déduite dès 1927.', 'C', 'Lemaître 1927 ; Hubble 1929', 'w'],
    ['1930-02-18', 'H', 3, 'Découverte de Pluton', 'Clyde Tombaugh repère Pluton sur des plaques photographiques.', 'C', 'Observatoire Lowell', '#pluto|8.6'],
    ['1957-10-04T19:28', 'H', 1, 'Spoutnik 1', 'Premier satellite artificiel : début de l’ère spatiale.', 'C', 'NASA (NSSDCA)', 'e'],
    ['1959-09-13T21:02', 'H', 3, 'Luna 2 atteint la Lune', 'Premier objet fabriqué à toucher un autre monde.', 'C', 'NASA (NSSDCA)', 'e'],
    ['1961-04-12T06:07', 'H', 1, 'Premier humain dans l’espace', 'Youri Gagarine fait un tour de la Terre en 108 minutes.', 'C', 'NASA (NSSDCA)', 'e'],
    ['1965-07-01', 'H', 1, 'Découverte du fond diffus cosmologique', 'Arno Penzias et Robert Wilson captent un bruit radio venu de toutes les directions : la lumière émise quand l’univers est devenu transparent.', 'C', 'Penzias et Wilson 1965', 'u'],
    ['1965-07-15T01:01', 'H', 3, 'Premier survol de Mars', 'Mariner 4 envoie 21 images d’un monde couvert de cratères.', 'C', 'NASA (NSSDCA)', '@Mars'],
    ['1967-11-28', 'H', 3, 'Premier pulsar', 'Jocelyn Bell repère un signal radio qui bat toutes les 1,337 seconde : une étoile à neutrons en rotation.', 'C', 'Hewish, Bell et al. 1968', 'g'],
    ['1968-12-24T09:59', 'H', 2, 'Premiers humains autour de la Lune', 'Apollo 8 se met en orbite lunaire ; photo du « lever de Terre ».', 'C', 'NASA', 'e'],
    ['1969-07-20T20:17', 'H', 1, 'Premiers pas sur la Lune', 'Le module d’Apollo 11 se pose dans la mer de la Tranquillité. Neil Armstrong pose le pied sur la Lune à 2 h 56 TU le 21 juillet.', 'C', 'NASA', 'e'],
    ['1970-12-15T05:34', 'H', 3, 'Premier atterrissage sur une autre planète', 'Venera 7 transmet 23 minutes depuis la surface de Vénus : 475 °C et 90 fois la pression terrestre.', 'C', 'NASA (NSSDCA)', '@Vénus'],
    ['1972-03-03T01:49', 'H', 2, 'Lancement de Pioneer 10', 'Première sonde à traverser la ceinture d’astéroïdes et à atteindre Jupiter.', 'C', 'NASA (NSSDCA)', 'i', { sp: 5 * D1 }],
    ['1973-04-06T02:11', 'H', 3, 'Lancement de Pioneer 11', 'Elle visitera Jupiter, puis Saturne.', 'C', 'NASA (NSSDCA)', 'i', { sp: 5 * D1 }],
    ['1973-12-04T02:25', 'H', 2, 'Pioneer 10 : premier survol de Jupiter', 'À 203 100 km du centre de la planète, soit 130 000 km au-dessus des nuages.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Jupiter', FLY],
    ['1974-12-03T05:21', 'H', 3, 'Pioneer 11 survole Jupiter', 'À 113 500 km du centre, en passant sous le pôle sud : Jupiter la renvoie vers Saturne.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Jupiter', FLY],
    ['1976-07-20T11:53', 'H', 2, 'Viking 1 se pose sur Mars', 'Premières images et analyses du sol martien depuis la surface.', 'C', 'NASA (NSSDCA)', '@Mars'],
    ['1977-08-20T14:29', 'H', 2, 'Lancement de Voyager 2', 'Elle profite d’un alignement des planètes géantes qui ne revient que tous les 176 ans.', 'C', 'NASA', 'i', { sp: 5 * D1 }],
    ['1977-09-05T12:56', 'H', 2, 'Lancement de Voyager 1', 'Partie après Voyager 2 mais sur une route plus rapide : elle la double avant Jupiter.', 'C', 'NASA', 'i', { sp: 5 * D1 }],
    ['1979-03-05T12:04', 'H', 1, 'Voyager 1 survole Jupiter', 'À 348 400 km du centre de Jupiter. Découverte des volcans actifs de Io et des anneaux de Jupiter.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Jupiter', FLY],
    ['1979-07-09T22:29', 'H', 3, 'Voyager 2 survole Jupiter', 'À 721 400 km du centre de Jupiter.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Jupiter', FLY],
    ['1979-09-01T16:29', 'H', 2, 'Pioneer 11 : premier survol de Saturne', 'À 80 900 km du centre de Saturne, environ 20 000 km au-dessus des nuages.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Saturne', FLY],
    ['1980-11-12T23:45', 'H', 2, 'Voyager 1 survole Saturne', 'À 184 000 km du centre, après un passage rapproché de Titan qui la fait sortir du plan des planètes.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Saturne', FLY],
    ['1981-08-26T03:24', 'H', 3, 'Voyager 2 survole Saturne', 'À 160 700 km du centre de Saturne.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Saturne', FLY],
    ['1986-01-24T17:58', 'H', 1, 'Voyager 2 survole Uranus', 'À 107 200 km du centre : seul survol d’Uranus à ce jour. Dix nouvelles lunes découvertes.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Uranus', FLY],
    ['1987-02-23T07:35', 'H', 1, 'Supernova 1987A', 'La lumière et les neutrinos d’une étoile du Grand Nuage de Magellan atteignent la Terre : la supernova la plus proche depuis 1604.', 'C', 'Détecteurs Kamiokande-II et IMB', '@Grand Nuage de Magellan'],
    ['1989-08-25T03:55', 'H', 1, 'Voyager 2 survole Neptune', 'À 29 240 km du centre, moins de 5 000 km au-dessus des nuages : seul survol de Neptune à ce jour. Geysers d’azote sur Triton.', 'C', 'Trajectoire JPL Horizons ; NASA', '@Neptune', FLY],
    ['1990-02-14', 'H', 2, 'Un point bleu pâle', 'À 6 milliards de km, Voyager 1 se retourne et photographie la Terre : moins d’un pixel.', 'C', 'NASA', '@Voyager 1'],
    ['1990-04-24T12:33', 'H', 2, 'Lancement du télescope Hubble', 'Premier grand télescope optique au-dessus de l’atmosphère.', 'C', 'NASA', 'e'],
    ['1992-04-23', 'H', 2, 'Les germes des galaxies', 'Le satellite COBE détecte dans le fond diffus des écarts de température de 1 pour 100 000 : les graines des futures galaxies.', 'C', 'Smoot et al. 1992', 'u'],
    ['1995-10-06', 'H', 1, 'Première planète autour d’une étoile comme le Soleil', 'Michel Mayor et Didier Queloz annoncent 51 Pegasi b, une géante qui boucle son orbite en 4,2 jours.', 'C', 'Mayor et Queloz 1995 (Nature)', '@51 Peg', { sp: 0.5 * D1 }],
    ['1998-09-01', 'H', 1, 'L’expansion de l’univers accélère', 'Deux équipes le montrent grâce aux supernovas lointaines : c’est la découverte de l’énergie noire.', 'C', 'Riess et al. 1998 ; Perlmutter et al. 1999', 'w'],
    ['2000-11-02', 'H', 3, 'La Station spatiale habitée en permanence', 'Depuis ce jour, il y a toujours eu des humains en orbite.', 'C', 'NASA', 'e'],
    ['2004-07-01T02:48', 'H', 3, 'Cassini en orbite autour de Saturne', 'Treize ans d’étude ; la sonde Huygens se pose sur Titan le 14 janvier 2005.', 'C', 'NASA et ESA', '@Saturne'],
    ['2006-01-19T19:00', 'H', 3, 'Lancement de New Horizons', 'La sonde la plus rapide jamais lancée, en route vers Pluton.', 'C', 'NASA', 'i', { sp: 5 * D1 }],
    ['2006-08-24', 'H', 2, 'Pluton devient une planète naine', 'L’Union astronomique internationale définit le mot « planète » après la découverte d’Éris, aussi massive que Pluton.', 'C', 'Résolution B5 de l’Union astronomique internationale', '#pluto|8.6'],
    ['2012-08-25', 'H', 1, 'Voyager 1 entre dans l’espace interstellaire', 'À 121 UA du Soleil, elle franchit la limite où le vent solaire cède devant le gaz de la Galaxie.', 'C', 'Gurnett et al. 2013 (Science)', '@Voyager 1'],
    ['2013-03-21', 'H', 2, 'Planck dresse la carte du fond diffus', 'La carte la plus précise de la première lumière : l’âge de l’univers est fixé à 13,8 milliards d’années.', 'C', 'Collaboration Planck 2013, 2018', 'u'],
    ['2014-11-12T15:34', 'H', 3, 'Philae se pose sur une comète', 'Premier atterrissage sur un noyau de comète, 67P/Tchourioumov-Guérassimenko.', 'C', 'ESA (mission Rosetta)', '@67P|12.3'],
    ['2015-07-14T11:48', 'H', 1, 'New Horizons survole Pluton', 'À 13 700 km du centre, soit 12 500 km de la surface. Montagnes de glace d’eau et glacier d’azote en forme de cœur.', 'C', 'Trajectoire JPL Horizons ; Stern et al. 2015', '#pluto|7.9', { sp: 1200 / YEAR_S, lead: 3 / 8766, sim: 'Vue centrée sur Pluton : la sonde est le point qui porte son nom. Sa trajectoire est réelle (JPL Horizons).' }],
    ['2015-09-14T09:50', 'H', 1, 'Première onde gravitationnelle détectée', 'Les deux détecteurs LIGO enregistrent la fusion de deux trous noirs survenue 1,3 milliard d’années plus tôt.', 'C', 'Abbott et al. 2016', 'e'],
    ['2017-02-22', 'H', 2, 'Sept planètes autour de TRAPPIST-1', 'Sept planètes de la taille de la Terre, dont trois dans la zone habitable.', 'C', 'Gillon et al. 2017 (Nature)', '@TRAPPIST-1', { sp: 0.3 * D1 }],
    ['2017-08-17T12:41', 'H', 2, 'Fusion de deux étoiles à neutrons', 'Onde gravitationnelle puis lumière, vues par 70 observatoires : on y voit se former de l’or et du platine.', 'C', 'Abbott et al. 2017', 'w'],
    ['2018-04-25', 'H', 2, 'Gaia cartographie 1,3 milliard d’étoiles', 'Deuxième catalogue de la mission Gaia. Les étoiles de cette page viennent du troisième, publié le 13 juin 2022.', 'C', 'ESA (Gaia DR2, DR3)', 'g'],
    ['2018-11-05', 'H', 2, 'Voyager 2 entre dans l’espace interstellaire', 'À 119 UA du Soleil.', 'C', 'Richardson et al. 2019 ; NASA', '@Voyager 2'],
    ['2019-01-01T05:33', 'H', 3, 'New Horizons survole Arrokoth', 'À 3 500 km d’un petit corps de la ceinture de Kuiper : l’objet le plus lointain jamais visité.', 'C', 'NASA', '@New Horizons'],
    ['2019-04-10', 'H', 1, 'Première image d’un trou noir', 'Le réseau Event Horizon Telescope montre l’ombre du trou noir de M87 : 6,5 milliards de masses solaires.', 'C', 'Collaboration EHT 2019', '@M87'],
    ['2021-12-25T12:20', 'H', 2, 'Lancement du télescope Webb', 'Un miroir de 6,5 m pour l’infrarouge, à 1,5 million de km de la Terre.', 'C', 'NASA, ESA et CSA', 'e'],
    ['2022-05-12', 'H', 2, 'Image du trou noir de notre galaxie', 'Sagittarius A*, 4,3 millions de masses solaires.', 'C', 'Collaboration EHT 2022', 'g'],
    ['2022-09-26T23:14', 'H', 3, 'Une sonde dévie un astéroïde', 'DART percute Dimorphos et raccourcit son orbite de 33 minutes : premier essai de défense planétaire.', 'C', 'Thomas et al. 2023 (Nature)', 'i'],
    ['2024-04-04', 'H', 3, 'L’énergie noire varie-t-elle ?', 'Premiers résultats du relevé DESI : un indice, pas encore une preuve, que l’énergie noire s’affaiblit avec le temps. Les galaxies lointaines de cette page viennent de ce relevé.', 'V', 'Collaboration DESI 2024, 2025', 'w'],
    ['2024-04-08T18:17', 'H', 2, 'Éclipse totale de Soleil sur l’Amérique du Nord', 'L’ombre de la Lune traverse le Mexique, les États-Unis et le Canada, dont le sud du Québec.', 'C', 'NASA (Espenak)', 'e', { sp: 1800 / YEAR_S, lead: 0.1 / 365.25, sim: 'Terre et Lune à leur position calculée : l’axe de l’ombre de la Lune (trait gris) touche la Terre.' }],
    ['2024-12-24T11:53', 'H', 3, 'Une sonde frôle le Soleil', 'Parker Solar Probe passe à 6,1 millions de km de la surface du Soleil, à 192 km/s : l’objet le plus rapide jamais construit.', 'C', 'NASA', 'i'],
    ['2026-03-03T11:34', 'H', 3, 'Éclipse totale de Lune', 'La Lune traverse l’ombre de la Terre.', 'C', 'NASA (Espenak)', 'e', { sp: 1800 / YEAR_S, lead: 0.1 / 365.25, sim: 'Terre et Lune à leur position calculée : la Lune croise l’axe de l’ombre de la Terre (trait gris).' }],
    ['2026-04-06T23:05', 'H', 1, 'Des humains de nouveau autour de la Lune', 'Artemis II : quatre astronautes survolent la face cachée et atteignent 406 771 km de la Terre, record de distance pour des humains. Lancement le 1er avril, retour le 10.', 'C', 'NASA', 'e'],
    ['2026-08-12T17:46', 'H', 2, 'Éclipse totale de Soleil', 'L’ombre de la Lune traverse le Groenland, l’Islande et l’Espagne.', 'C', 'NASA (Espenak)', 'e', { sp: 1800 / YEAR_S, lead: 0.1 / 365.25, sim: 'Terre et Lune à leur position calculée : l’axe de l’ombre de la Lune (trait gris) touche la Terre.' }],
    ['2026-11-18T10:20', 'H', 1, 'Voyager 1 à un jour-lumière de la Terre', 'Un signal radio met désormais plus de 24 heures à l’atteindre : 25,9 milliards de km. Date calculée ici d’après la trajectoire JPL ; la NASA annonçait le 15 novembre, l’écart tient sans doute à la définition retenue.', 'C', 'Calcul d’après JPL Horizons', '@Voyager 1'],
    ['2027-08-02T10:07', 'H', 2, 'Éclipse totale de Soleil', 'Plus de 6 minutes de totalité au-dessus de l’Égypte, la plus longue sur terre ferme du siècle. L’ombre passe aussi sur le sud de l’Espagne.', 'C', 'NASA (Espenak) : 6 min 23 s', 'e', { sp: 1800 / YEAR_S, lead: 0.1 / 365.25, sim: 'Terre et Lune à leur position calculée : l’axe de l’ombre de la Lune (trait gris) touche la Terre.' }],
    [300, 'H', 3, 'Voyager 1 atteint le nuage d’Oort', 'Elle mettra ensuite environ 30 000 ans à le traverser.', 'P', 'NASA (JPL)', '@Voyager 1'],
    [4.0e4, 'H', 3, 'Voyager 1 passe près d’une autre étoile', 'À 1,6 année-lumière de Gliese 445. La sonde sera éteinte depuis longtemps.', 'C', 'NASA (JPL)', 'n'],
  ];
  let EVL = []; S.evCats = { U: true, G: true, S: true, T: true, H: true, O: false };   /* O : 391 détections, masquées par défaut pour ne pas noyer la chronologie */ S.evCur = null;
  const evShown = e => !!S.evCats[e.cat];
  function tRange() { const C = S.cosmo; return [C.tBang !== null ? C.tBang * 1e9 + 1e5 : C.tStart * 1e9, Math.min(C.tEnd * 1e9, 2e11)]; }
  // âge de l'univers jeune (matière et rayonnement seuls) : formule exacte, et son inverse
  const earlyAge = (C, a) => (2 / (3 * C.h * C.par.Om * C.par.Om)) * ((C.par.Om * a - 2 * C.Or) * Math.sqrt(C.Or + C.par.Om * a) + 2 * Math.pow(C.Or, 1.5));
  function ageOfA(C, a) { if (a < 0.02 && C.par.Om > 0.01) return earlyAge(C, a); let lo = C.tBang, hi = 0; const o = {}; for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (cosmoAt(C, m, o).a < a) lo = m; else hi = m; } return (lo + hi) / 2 - C.tBang; }
  function aOfAge(C, age) { let lo = 1e-8, hi = 0.09; for (let i = 0; i < 50; i++) { const m = Math.sqrt(lo * hi); if (earlyAge(C, m) < age) lo = m; else hi = m; } return Math.sqrt(lo * hi); }
  function cosmoCross(g) { const C = S.cosmo, o = {}, t0 = (C.tBang !== null ? C.tBang : C.tStart) + 0.05, t1 = Math.min(C.tEnd, 80); let pt = t0, pv = g(cosmoAt(C, t0, o).a);
    for (let i = 1; i <= 800; i++) { const t = t0 + (t1 - t0) * i / 800, v = g(cosmoAt(C, t, o).a); if (pv < 0 && v >= 0) { let a = pt, b = t; for (let k = 0; k < 40; k++) { const m = (a + b) / 2; if (g(cosmoAt(C, m, o).a) < 0) a = m; else b = m; } return (a + b) / 2 * 1e9; } pt = t; pv = v; } return null; }
  function evResolve(raw) { const C = S.cosmo, tb = C.tBang !== null ? C.tBang * 1e9 : null, lim = tRange(), out = [];
    for (const r of raw) { const w = r[0], o = r[8] || {}; let t, iso = null;
      if (typeof w === 'number') t = w; else if (typeof w === 'string') { iso = w; t = (isoJd(w) - JD_NOW) / 365.25; } else if (tb === null) continue; else if (w.z !== undefined) t = tb + ageOfA(C, 1 / (1 + w.z)) * 1e9; else t = tb + w.a;
      if (!isFinite(t) || t > lim[1]) continue;
      out.push({ t: Math.max(t, lim[0]), tr: t, iso, cat: r[1], imp: r[2], n: r[3], d: r[4], c: r[5], s: r[6], v: r[7] || '', lab: o.lab || null, sp: o.sp, lead: o.lead || 0, lr: o.lr, sim: o.sim, now: !!o.now, age: tb !== null ? t - tb : null, el: null }); }
    out.sort((a, b) => a.t - b.t || a.tr - b.tr); return out; }
  function evWhen(e) { if (e.now) return 'Maintenant'; if (e.lab) return e.lab; if (e.iso) { const wt = e.iso.indexOf('T') > 0; return fmtJd(isoJd(e.iso), wt) + (wt ? NBSP + 'TU' : ''); }
    if (e.age !== null && e.age < 1.5e9) return fmtYears(Math.max(e.age, 0)) + ' après le Big Bang'; return e.tr < 0 ? 'Il y a ' + fmtYears(-e.tr) : 'Dans ' + fmtYears(e.tr); }
  function evEra(e) { const t = e.t; if (e.age !== null && e.age < 1.2e9) return 'Univers jeune'; if (t < -4.6e9) return 'Avant le Soleil'; if (t < -5.4e8) return 'Système solaire et Terre primitive'; if (t < -6.7e7) return 'La vie complexe'; if (t < -1.2e4) return 'Mammifères, puis humains';
    if (t < jyr(1600)) return 'Antiquité et Moyen Âge'; if (t < jyr(1957)) return 'L’ère du télescope'; if (t <= 1e-6) return 'L’ère spatiale'; if (t < 1000) return 'Prochaines années et siècles'; if (t < 1e8) return 'Avenir des étoiles voisines'; return 'Avenir lointain'; }
  function evSpeed(e) { if (e.iso) return e.iso.indexOf('T') > 0 ? H3 : 5 * D1; if (e.age !== null && e.age < 5e6) return 8e4; if (e.age !== null && e.age < 1.2e9) return 1e7; return clamp(Math.abs(e.tr) / 2000, 1, 5e7); }      // la date affichée change d'environ 0,05 % par seconde
  function goNameW(n) { const X = findIndex(), q = fold(n); let best = -1, br = 9; for (let i = 0; i < X.length; i++) { const t = X[i][0], p = t.indexOf(q); if (p < 0) continue; const r = t === q ? 0 : p === 0 ? 1 : t[p - 1] === ' ' ? 2 : 9; if (r < br || (r === br && r < 9 && t.length < X[best][0].length)) { br = r; best = i; } } if (best >= 0 && br < 9) { X[best][3](); return true; } return false; }
  function evView(e) { const v = e.v || ''; select(null);
    if (v[0] === '#') { const p = v.slice(1).split('|'); flyTo({ name: PLN[p[0]] || p[0], sub: '', radM: 1.19e6, get: () => cenOf(p[0]), rows: () => [] }, +p[1]); return; }      // un astre suivi sans fiche propre
    if (v[0] === '@') { const p = v.slice(1).split('|'); if (goNameW(p[0])) { if (p[1]) goTo(+p[1], { noHist: true }); return; } goStop(STOPS[1]); return; }
    if (e.lr) { goTo(e.lr, { focus: 'sun' }); return; } if (v === 'i') { goTo(Math.log10(2.6 * AU), { focus: 'sun' }); return; }
    const k = { e: 0, s: 1, o: 2, n: 3, g: 4, l: 5, c: 6, w: 7, u: 8 }[v]; goStop(STOPS[k === undefined ? 1 : k]); }
  function evObj(e) { return { isEvent: true, ev: e, name: e.n, sub: evWhen(e) + ' · ' + EVCAT[e.cat], get: () => [NaN, NaN, NaN], go: () => evGo(e), rows: () => { const r = []; if (e.d) r.push(['Ce qui se passe', e.d]); r.push(['Certitude', EVCONF[e.c]], ['Source', e.s]);
      const sim = e.sim || (e.iso && Math.abs(e.t) < 3000 ? 'Planètes et Lune à leur position calculée pour cette date.' : (e.cat === 'T' || e.cat === 'S') && Math.abs(e.t) > 3000 ? 'À cette époque, la position des planètes n’est qu’indicative.' : ''); if (sim) r.push(['Dans la simulation', sim]); return r; } }; }
  function evMark(e) { for (const q of EVL) if (q.el) q.el.classList.toggle('cur', q === e); if (openKey === 'chrono') evScroll(); }
  function evGo(e) { const keep = openKey; evtEl.hidden = true; S.hit = null; S.evCur = e;
    if (e.now) { S.ty = 0; S.lastTy = 0; S.T1 = S.T2 = 0; S.beltYears = 0; } else { setTime(e.t - (e.lead || 0)); S.lastTy = S.ty; }
    S.dir = 1; $('b-dir').setAttribute('aria-pressed', false); S.playing = true; syncPlay(); evView(e); setSpeed((e.sp || evSpeed(e)) * YEAR_S); select(evObj(e)); evMark(e);
    if (innerWidth < 700) { if (openKey) openPanel(null); } else if (keep && openKey !== keep) openPanel(keep); }
  function evStep(dir) { const c = S.evCur, at = !!c && S.ty >= c.t - (c.lead || 0) - 1e-9 && S.ty <= c.t + (c.sp || evSpeed(c)) * 45, t = at ? c.t : S.ty, eps = Math.max(1e-9, Math.abs(t) * 1e-12), ic = at ? EVL.indexOf(c) : -1; let best = null;
    for (let i = 0; i < EVL.length; i++) { const e = EVL[i]; if (!evShown(e) || i === ic) continue; const ok = dir > 0 ? (e.t > t + eps || (ic >= 0 && e.t >= t - eps && i > ic)) : (e.t < t - eps || (ic >= 0 && e.t <= t + eps && i < ic)); if (!ok) continue; if (!best || (dir > 0 ? e.t < best.t : e.t >= best.t)) best = e; }
    if (best) evGo(best); }
  function evList() { const ol = $('events'); ol.textContent = ''; let era = null;
    for (const e of EVL) { e.el = null; if (!evShown(e)) continue; const er = evEra(e); if (er !== era) { era = er; const h = document.createElement('li'); h.className = 'eh'; h.textContent = er; ol.appendChild(h); }
      const li = document.createElement('li'), b = document.createElement('button'), w = document.createElement('b'), d = document.createElement('span'); b.type = 'button'; b.className = 'ev' + (e.imp === 1 ? ' maj' : ''); w.textContent = evWhen(e); d.textContent = e.n; b.append(w, d); b.addEventListener('click', () => evGo(e)); li.appendChild(b); ol.appendChild(li); e.el = b; }
    if (S.evCur) { const c = EVL.find(q => q.n === S.evCur.n && q.cat === S.evCur.cat); S.evCur = c || null; if (c) evMark(c); } }
  function evScroll() { let nx = null; for (const e of EVL) if (e.el && e.t >= S.ty - 1e-9) { nx = e; break; } const el = (S.evCur && S.evCur.el) || (nx && nx.el), ol = $('events'); if (el) ol.scrollTop = el.offsetTop - ol.clientHeight / 2 + el.offsetHeight / 2; }
  const evtEl = $('evt'); let evtE = null, evtT = 0;
  function evToast(e) { evtE = e; evtT = performance.now(); evtEl.textContent = ''; const b = document.createElement('b'), s = document.createElement('small'); b.textContent = e.n; s.textContent = evWhen(e) + ' · toucher pour y assister'; evtEl.append(b, s); evtEl.hidden = false; }
  evtEl.addEventListener('click', () => { const e = evtE; evtEl.hidden = true; evtE = null; if (e) evGo(e); });
  function evCross(a, b) { if (a === b || !EVL.length) return; const lo = Math.min(a, b), hi = Math.max(a, b); let i0 = 0, i1 = EVL.length, best = null, n = 0; while (i0 < i1) { const m = (i0 + i1) >> 1; if (EVL[m].t <= lo) i0 = m + 1; else i1 = m; }
    for (let i = i0; i < EVL.length && EVL[i].t <= hi; i++) { const e = EVL[i]; if (!evShown(e) || e.now) continue; n++; if (!best || e.imp < best.imp) best = e; }
    if (!best || (S.sel && S.sel.ev === best)) return; if (n > 2 && best.imp > 1) return; if (evtE && !evtEl.hidden && performance.now() - evtT < 1500 && best.imp >= evtE.imp) return; evToast(best); }
  /* Ondes gravitationnelles détectées (GWOSC, catalogues GWTC) : une ligne par détection, valeurs et intervalles tels que publiés.
     Certitude : « Certain » si la probabilité d'origine astrophysique publiée est d'au moins 0,99 (ou non publiée, détections
     des premiers catalogues), « Probable » en dessous. La vue montre la Terre, où le signal est enregistré. */
  const GW_SUR = 0.99;
  function gwEvents(dyn) { const G = DATA.GW || [], src = 'GWOSC (LIGO, Virgo, KAGRA), catalogue ';
    const ms = x => sig(x, 2), rng = (q, f) => q[1] !== null && q[2] !== null ? ' (entre ' + f(q[1]) + ' et ' + f(q[2]) + ')' : '';
    const pct = p => p >= 0.995 ? 'plus de 99' + NBSP + '%' : Math.round(p * 100) + NBSP + '%';
    for (const g of G) { const sure = g.pa === null || g.pa >= GW_SUR; let n, d;
      if (g.m1 && g.m2) { n = 'Fusion de ' + ms(g.m1[0]) + ' et ' + ms(g.m2[0]) + ' masses solaires';
        d = g.n + ' : fusion de deux objets compacts, l’un de ' + ms(g.m1[0]) + NBSP + 'masses solaires' + rng(g.m1, ms) + ', l’autre de ' + ms(g.m2[0]) + rng(g.m2, ms) + '.'
          + (g.dl ? ' Distance tirée de l’affaiblissement du signal (distance de luminosité, ce n’est pas le trajet de la lumière) : ' + fmtDist(g.dl[0] * MPC) + rng(g.dl, x => fmtDist(x * MPC)) + '.' : ''); }
      else { n = 'Onde gravitationnelle ' + g.n; d = 'Détection publiée. Masses et distance pas encore disponibles dans l’interface de GWOSC.'; }
      if (!sure) d += ' Probabilité d’origine astrophysique : ' + pct(g.pa) + '.';
      dyn.push([g.t.slice(0, 16), 'O', 3, n, d, sure ? 'C' : 'P', src + g.cat, 'e', { sim: 'Détection réelle. Sa position sur le ciel n’est pas affichée : les zones de localisation ne sont pas encore chargées.' }]); } }
  function buildEvents() { const O = S.orbit, C = S.cosmo, p = O.peri[0], L10 = Math.log10, dyn = []; if (!OO.el) oortInit();
    dyn.push([0, 'H', 1, 'Aujourd’hui', 'L’instant présent, à l’ouverture de la page.', 'C', 'Horloge de l’appareil', 's', { now: true, sp: 20 / 365.25 }]);
    dyn.push([EV_AC[0], 'G', 2, 'Alpha du Centaure au plus près du Soleil', 'Le système d’étoiles le plus proche passe à ' + sig(EV_AC[1], 2) + ' années-lumière, puis s’éloigne.', 'C', 'Calculé ici d’après la position et la vitesse mesurées (Hipparcos, Gaia)', 'n', { sp: 2500, lead: 9000 }]);
    dyn.push([1e5, 'G', 2, 'Bételgeuse explose en supernova', 'Elle brillera autant que la demi-Lune pendant des mois. La date réelle est inconnue : c’est un ordre de grandeur.', 'S', 'Joyce et al. 2020 : dans environ 100 000 ans', '', { lr: L10(900 * LY), sp: 4000, lead: 14000 }]);
    dyn.push([EV_GL[0], 'G', 1, 'L’étoile Gliese 710 traverse le nuage d’Oort', 'Elle passe à ' + sig(EV_GL[1], 2) + ' année-lumière du Soleil. ' + (() => { const g = OO.enc.find(q => /710/.test(q.name)); return g ? (g.pub ? 'Soit ' + passAU(g.pub.d) + ', entre ' + passAU(g.pub.d5) + ' et ' + passAU(g.pub.d95) + ' selon les incertitudes de mesure. ' : '') + 'Dans le nuage simulé (' + nf(G.oort.N, 0) + ' comètes), son attraction change l’orbite de ' + nf(g.hit, 0) + ' d’entre elles, en éjecte ' + g.ej + ' et en envoie ' + g.inn + ' vers les planètes : une étoile de passage dérange le nuage, elle ne le vide pas.' : 'Elle bouscule des comètes lointaines.'; })(), 'C', 'Calculé ici d’après Gaia DR3 ; Bailer-Jones et al. 2018 ; Berski et Dybczyński 2016', 'o', { sp: 15000, lead: 70000, sim: 'Chaque comète du modèle suit sa propre orbite autour du Soleil ; le coup de vitesse donné par l’étoile est calculé pour chacune. Les comètes les plus déviées s’éclairent. Le nuage lui-même reste hypothétique : sa forme est un modèle.' }]);
    OO.enc.forEach(e => { const o = e.pub; if (!o || /710|Proxima/.test(e.name)) return; const past = o.t < 0, sp = clamp(1.2e6 / o.vk, 2000, 20000);
      dyn.push([o.t, 'G', o.d < 0.5 ? 2 : 3, o.title || 'L’étoile ' + e.name + (o.d < 0.5 ? ' frôle le système solaire' : ' passe près du système solaire'), (past ? 'Elle est passée' : 'Elle passera') + ' à ' + sig(o.d * 3.2616, 2) + ' année' + (o.d * 3.2616 >= 2 ? 's' : '') + '-lumière du Soleil (' + passAU(o.d) + ' ; entre ' + passAU(o.d5) + ' et ' + passAU(o.d95) + ' selon les incertitudes de mesure), à ' + sig(o.vk, 3) + NBSP + 'km/s. ' + (e.hit > 0 ? 'Dans le nuage simulé, son attraction change l’orbite de ' + nf(e.hit, 0) + ' comètes, en éjecte ' + e.ej + ' et en envoie ' + e.inn + ' vers les planètes.' : 'Elle passe trop loin pour déranger sensiblement le nuage simulé.'), 'P', o.src || 'Bailer-Jones 2022 (Gaia DR3)', 'o', { sp, lead: 5 * sp, sim: 'L’instant, la distance et la vitesse du passage sont ceux publiés. Le côté par lequel l’étoile passe est déduit de son mouvement actuel en ligne droite : il est moins sûr.' + (Math.abs(o.t) > 3e6 ? ' Au-delà de 3 millions d’années, les autres étoiles suivent leur orbite dans la Galaxie ; celle-ci reste tracée en ligne droite pour respecter le passage publié.' : '') }]); });
    (DATA.PASS_DUB || []).forEach(q => { const sp = clamp(1.2e6 / q.vk, 2000, 20000), wd = q.g === '5544743925212648320', fut = q.t > 0;
      dyn.push([q.t, 'G', 3, 'Passage douteux de l’étoile ' + q.n, wd ? 'Gaia mesurait pour cette naine blanche une vitesse de 374' + NBSP + 'km/s, qui l’aurait amenée à ' + passAU(q.d) + ' du Soleil dans 29' + NBSP + '000 ans. Un nouveau spectre a montré que cette vitesse était fausse : ce passage n’aura pas lieu.'
        : 'D’après les mesures de Gaia, cette étoile ' + (fut ? 'passerait' : 'serait passée') + ' à ' + passAU(q.d) + ' du Soleil (entre ' + passAU(q.d5) + ' et ' + passAU(q.d95) + '), à ' + sig(q.vk, 3) + NBSP + 'km/s. ' + (q.f.indexOf('b') >= 0 ? 'Elle fait probablement partie d’une étoile double large, ce qui fausse la trajectoire calculée.' : 'L’auteur de l’étude juge ce passage douteux : vitesse ou position peu fiables.'),
        'V', wd ? 'Bailer-Jones 2022 ; Landstreet et al. 2023' : 'Bailer-Jones 2022 (Gaia DR3)', 'o', { sp, lead: 5 * sp, sim: 'Passage non simulé : l’étoile n’est pas déplacée et les comètes ne sont pas déviées.' }]); });
    dyn.push([1.1e9, 'T', 1, 'La Terre perd ses océans', 'Quand le Soleil brille assez fort, l’eau s’évapore et s’échappe peu à peu vers l’espace : vers +10 % d’éclat, dans environ 1,1 milliard d’années, selon Kasting 1988 ; selon Wolf et Toon 2015, le climat bascule vers +12,5 % et la perte d’eau devient importante vers +19 %, donc plus tard. La date réelle est inconnue.', 'S', 'Estimations : Kasting 1988 ; Wolf et Toon 2015 (JGR Atmospheres 120, 5775)', '', { lr: L10(2.6 * AU), sp: 2e7 }]);
    { const q = LMCO.peri[0]; if (LMCO.tMerge) dyn.push([LMCO.tMerge * 1e9, 'G', 1, 'Le Grand Nuage de Magellan est absorbé par la Voie lactée', 'Scénario calculé ici ; il dépend beaucoup de la masse du Nuage.', 'S', 'Orbite calculée d’après Kallivayalil et al. 2013 ; Cautun et al. 2019', '', { lr: L10(150 * KPC), sp: 8e7, lead: 5e8 }]);
      else if (q) dyn.push([q[0] * 1e9, 'G', 2, 'Le Grand Nuage de Magellan repasse au plus près', 'À ' + fmtDist(Number((q[1] * KPC).toPrecision(2))) + ' de la Voie lactée.', 'S', 'Orbite calculée d’après Kallivayalil et al. 2013', '', { lr: L10(150 * KPC), sp: 8e7, lead: 3e8 }]); }
    if (p) dyn.push([p[0] * 1e9, 'G', 1, 'Andromède passe au plus près', 'À ' + fmtDist(Number((p[1] * KPC).toPrecision(2))) + (S.tOn !== null ? ' : les deux galaxies se déforment.' : '.') + ' Le résultat dépend de la vitesse de côté d’Andromède, mal connue.', 'S', 'Orbite calculée ici ; mesures : van der Marel et al. 2012, Salomon et al. 2021', '', { lr: L10(S.tOn !== null ? 300 * KPC : 1100 * KPC), sp: 1.2e8, lead: 6e8 }]);
    dyn.push([(10.00 - SUN_NOW) * 1e9, 'S', 1, 'Le Soleil commence à enfler', 'Il a brûlé l’hydrogène de son cœur et quitte sa longue période stable.', 'P', 'Modèle d’évolution du Soleil (Schröder et Smith 2008)', '', { lr: L10(3 * AU), sp: 3e7 }]);
    dyn.push([T_DIV * 1e9, 'S', 1, 'Sort de la Terre inconnu', 'Jusqu’ici, la Terre s’éloignait du Soleil qui perd sa masse. À partir d’ici, les marées resserrent son orbite dans le calcul : engloutie selon Schröder et Smith 2008 et Rasio et al. 1996, elle pourrait survivre selon Rybicki et Denis 2001. La Terre et la Lune ne sont plus dessinées.', 'S', 'Schröder et Smith 2008 ; Rasio et al. 1996 ; Rybicki et Denis 2001', '', { lr: L10(2.6 * AU), sp: 1.5e6, lead: 6e6 }]);
    dyn.push([ENG.mercury * 1e9, 'S', 1, 'Le Soleil géant rouge engloutit Mercure', 'Son orbite, élargie par la perte de masse du Soleil, se resserre sous l’effet des marées et du frottement : Mercure descend en spirale dans le Soleil. Vénus suit ' + fmtYears((ENG.venus - ENG.mercury) * 1e9) + ' plus tard. Calculé ici avec la méthode de Schröder et Smith 2008. Le sort de la Terre est inconnu.', 'P', 'Schröder et Smith 2008 (MNRAS 386, 155) ; Soleil géant d’après le modèle MIST (Choi et al. 2016) ; calcul de la page', '', { lr: L10(2.6 * AU), sp: 1.5e6, lead: 6e6 }]);      /* 1,5 Ma par seconde : la spirale de Vénus (1,7 Ma) dure plus de 60 images */
    dyn.push([(12.30 - SUN_NOW) * 1e9, 'S', 1, 'Le Soleil devient une naine blanche', 'Il n’en reste qu’un cœur de carbone et d’oxygène, grand comme la Terre, qui refroidit lentement.', 'P', 'Schröder et Smith 2008', 's', { sp: 2e7 }]);
    if (O.tMerge) dyn.push([O.tMerge * 1e9, 'G', 1, 'La Voie lactée et Andromède fusionnent', 'Scénario calculé ici. Les études récentes donnent environ une chance sur deux de fusion d’ici 10 milliards d’années.', 'S', 'Sawala et al. 2025 (Nature Astronomy)', '', { lr: L10(220 * KPC), sp: 1.2e8, lead: 5e8 }]);
    dyn.push([6e10, 'U', 2, 'Les autres galaxies sortent de vue', 'L’énergie noire a emporté presque toutes les galaxies hors du Groupe local au-delà de l’horizon.', 'S', 'Krauss et Scherrer 2007 ; calcul du modèle de la page', 'w', { sp: 3e9, lead: 5.5e10 }]);
    { const ta = cosmoCross(a => C.acc(a)), td = cosmoCross(a => C.par.OL * Math.pow(a, -3 * (1 + C.par.w)) - C.par.Om / (a * a * a));
      if (ta !== null) dyn.push([ta, 'U', 1, 'L’expansion se met à accélérer', 'La matière s’est assez diluée pour que l’énergie noire l’emporte sur la gravité : l’expansion, qui ralentissait, accélère.', 'P', 'Date calculée avec le modèle cosmologique de la page ; découverte : Riess et al. 1998, Perlmutter et al. 1999', 'w']);
      if (td !== null) dyn.push([td, 'U', 2, 'L’énergie noire devient majoritaire', 'Sa densité dépasse celle de la matière.', 'P', 'Date calculée avec le modèle cosmologique de la page', 'w']); }
    gwEvents(dyn);
    EVL = evResolve(EV_RAW.concat(dyn)); evList();
    $('s-vt').value = S.vt; $('o-vt').textContent = nf(Math.round(S.vt), 0) + NBSP + 'km/s';
    $('vt-hint').textContent = 'Les mesures publiées donnent de 34 à 76 km/s, avec une incertitude d’une trentaine de km/s. ' + (p ? 'Avec ' + nf(Math.round(S.vt), 0) + ' km/s : au plus près dans ' + fmtYears(p[0] * 1e9) + ', à ' + fmtDist(Number((p[1] * KPC).toPrecision(2))) + '. ' : '') + (O.tMerge ? 'Fusion dans ' + fmtYears(O.tMerge * 1e9) + '.' : 'Pas de fusion avant 14 milliards d’années.') + ' Les études récentes donnent entre une chance sur deux et neuf sur dix de fusion d’ici 10 milliards d’années.';
  }
  // saisie d'une date : « 20/07/1969 », « 4 juillet 1054 », « 1054 », « −66 Ma », « il y a 4,5 milliards d'années », « dans 5 Ga »
  function parseWhen(s0) { const s = String(s0 || '').trim().toLowerCase().replace(/[\u2212\u2013\u2014]/g, '-').replace(/[\u00a0\u202f]/g, ' ').normalize('NFD').replace(/[\u0300-\u036f]/g, ''); if (!s) return null; if (/^(auj|maint|now)/.test(s)) return 0;
    const num = x => parseFloat(String(x).replace(/\s/g, '').replace(',', '.')); let m = s.match(/^(il y a|dans|\+|-)?\s*(\d[\d\s.,]*?)\s*(ga|gyr|md|milliards?|ma|myr|m|millions?|ka|kyr|mille|milliers?|siecles?|ans?|annees?)\b(.*)$/);
    if (m) { const u = m[3], k = /^(ga|gyr|md|milliard)/.test(u) ? 1e9 : /^(ma|myr|m$|million)/.test(u) ? 1e6 : /^(ka|kyr|mille|millier)/.test(u) ? 1e3 : /^siecle/.test(u) ? 100 : 1, v = num(m[2]) * k; if (!isFinite(v)) return null; return m[1] === 'dans' || m[1] === '+' || /futur|plus tard/.test(m[4]) ? v : -v; }
    const MO = ['janv', 'fevr', 'mars', 'avr', 'mai', 'juin', 'juil', 'aout', 'sept', 'oct', 'nov', 'dec'], bc = /av\.? ?j|avant j|\bbc\b/.test(s), mon = w => MO.findIndex(q => w.indexOf(q) === 0 || (w.length >= 3 && q.indexOf(w) === 0)); let y = null, mo = 7, d = 1;
    if ((m = s.match(/^(\d{1,2})[\/.](\d{1,2})[\/.](-?\d{1,6})/))) { d = +m[1]; mo = +m[2]; y = +m[3]; }
    else if ((m = s.match(/^(-?\d{1,6})-(\d{1,2})-(\d{1,2})/))) { y = +m[1]; mo = +m[2]; d = +m[3]; }
    else if ((m = s.match(/^(\d{1,2})(?:er)? ([a-z]+)\.? (-?\d{1,6})/))) { const i = mon(m[2]); if (i < 0) return null; d = +m[1]; mo = i + 1; y = +m[3]; }
    else if ((m = s.match(/^([a-z]+)\.? (-?\d{1,6})/))) { const i = mon(m[1]); if (i < 0) return null; mo = i + 1; y = +m[2]; d = 15; }
    else if ((m = s.match(/^(-?\d{1,6})\b/))) y = +m[1];
    if (y === null || !isFinite(y) || mo < 1 || mo > 12 || d < 1 || d > 31) return null; if (bc) y = 1 - Math.abs(y);
    const h = s.match(/(\d{1,2}) ?h ?(\d{2})?/), fr = h ? (+h[1] + (+h[2] || 0) / 60) / 24 : 0.5, jul = y < 1582 || (y === 1582 && (mo < 10 || (mo === 10 && d < 15)));
    return (jdFromCal(y, mo, d, jul) + fr - JD_NOW) / 365.25; }
  { const box = $('ev-cats'); for (const k in EVCAT) { const b = document.createElement('button'); b.type = 'button'; b.className = 'btn'; b.setAttribute('aria-pressed', String(!!S.evCats[k])); b.textContent = EVCAT[k]; b.addEventListener('click', () => { S.evCats[k] = !S.evCats[k]; b.setAttribute('aria-pressed', S.evCats[k]); evList(); }); box.appendChild(b); }
    const sp = $('t-speeds'); for (const q of [['temps réel', 1], ['1 heure', 3600], ['1 jour', DAY_S], ['1 mois', YEAR_S / 12], ['1 an', YEAR_S], ['100 ans', 100 * YEAR_S], ['10 000 ans', 1e4 * YEAR_S], ['1 million d’années', 1e6 * YEAR_S], ['100 millions', 1e8 * YEAR_S], ['1 milliard', 1e9 * YEAR_S]]) { const b = document.createElement('button'); b.type = 'button'; b.className = 'btn'; b.textContent = q[0]; b.addEventListener('click', () => { setSpeed(q[1]); if (!S.playing) { S.playing = true; syncPlay(); } }); sp.appendChild(b); }
    const go = () => { const t = parseWhen($('t-date').value), msg = $('t-msg'); if (t === null) { msg.textContent = 'Date non comprise. Exemples : 20/07/1969, 4 juillet 1054, −66 Ma, dans 5 milliards d’années.'; return; }
      S.hit = null; S.evCur = null; const r = setTime(t); S.lastTy = S.ty; S.playing = false; syncPlay(); msg.textContent = r === 'start' ? 'Avant le début du calcul : placé au plus tôt possible.' : r === 'end' ? 'Après la fin du calcul : placé au plus tard possible.' : 'Temps arrêté à cette date. Le bouton lecture le relance.'; if (innerWidth < 700 && !r) openPanel(null); };
    $('t-go').addEventListener('click', go); $('t-date').addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Enter') go(); });
    $('t-prev').addEventListener('click', () => evStep(-1)); $('t-next').addEventListener('click', () => evStep(1)); }
  { const ck = $('c-sky'); if (ck) ck.addEventListener('change', e => { S.skyOn = e.target.checked; }); }
  /* ---- frise du temps : en haut, toute l'histoire d'un coup d'œil ; en dessous, une règle détaillée que l'on fait glisser ---- */
  const tapeEl = $('tape'), tcv = $('tape-cv'), tcx = tcv.getContext('2d');
  const ovF = t => Math.sign(t) * Math.log10(1 + Math.abs(t)), ovInv = f => Math.sign(f) * (Math.pow(10, Math.abs(f)) - 1);
  const tapeW = () => clamp(S.speed / YEAR_S * 14, 2.5 / 8766, 2e10);      // demi-largeur de la règle : ce qui défile en 14 secondes à la vitesse choisie
  const TSTEPS = [1 / 8766, 3 / 8766, 6 / 8766, 1 / 365.25, 2 / 365.25, 5 / 365.25, 10 / 365.25, 1 / 12, 0.25, 1, 2, 5, 10, 20, 50, 100, 200, 500];
  function tapeStep(W) { const raw = 2 * W / 9; for (const s of TSTEPS) if (s >= raw) return s; let s = 1000; for (;;) { for (const m of [1, 2, 5]) if (s * m >= raw) return s * m; s *= 10; } }
  const shortY = (a, st) => { const n = st ? clamp(Math.ceil(Math.log10(Math.max(a / st, 1))) + 1, 3, 8) : 3; return a < 1e6 ? nf(Math.round(a), 0) + NBSP + (a < 2 ? 'an' : 'ans') : a < 1e9 ? sig(a / 1e6, n) + NBSP + 'M ans' : sig(a / 1e9, n) + NBSP + 'Md ans'; };      // assez de chiffres pour distinguer deux graduations voisines
  const MABR = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'], CATCOL = { U: '#b79cff', G: '#7fb6ff', S: '#ffc66b', T: '#7fd9a0', H: '#ff8f8f' };
  function tapeTicks(t0, W, step) { const C = S.cosmo, out = [], a = t0 - W, b = t0 + W, tb = C.tBang !== null ? C.tBang * 1e9 : null;
    if (Math.abs(t0) < 6000 && step < 600) { const jdA = JD_NOW + a * 365.25, jdB = JD_NOW + b * 365.25;
      if (step >= 1) { const ya = calFromJd(jdA).y, yb = calFromJd(jdB).y; for (let y = Math.floor(ya / step) * step; y <= yb + step; y += step) out.push([jyr(y), y > 0 ? String(y) : (1 - y) + NBSP + 'av. J.-C.']); }
      else if (step >= 1 / 12 - 1e-9) { const c = calFromJd(jdA), q = step > 0.2 ? 3 : 1; let y = c.y, m = c.m; for (let k = 0; k < 400; k++) { const jd = jdFromCal(y, m, 1, y < 1582 || (y === 1582 && m <= 10)); if (jd > jdB) break; if ((m - 1) % q === 0) out.push([(jd - JD_NOW) / 365.25, m === 1 ? String(y > 0 ? y : 1 - y) : MABR[m - 1]]); if (++m > 12) { m = 1; y++; } } }
      else if (step >= 1 / 365.25 - 1e-9) { const sd = Math.round(step * 365.25); for (let k = Math.ceil((jdA - 0.5) / sd); k * sd + 0.5 <= jdB; k++) { const jd = k * sd + 0.5, c = calFromJd(jd + 0.01); out.push([(jd - JD_NOW) / 365.25, c.d + NBSP + MABR[c.m - 1]]); } }
      else { const sh = step * 365.25; for (let k = Math.ceil((jdA - 0.5) / sh); k * sh + 0.5 <= jdB; k++) { const jd = k * sh + 0.5, d = new Date((jd - 2440587.5) * 86400000); out.push([(jd - JD_NOW) / 365.25, d.getHours() + NBSP + 'h']); } }
      return [out, '']; }
    if (tb !== null && t0 - tb < 1.5e9 && W < (t0 - tb) * 3 + 1e5) { for (let k = Math.max(0, Math.ceil((a - tb) / step)); tb + k * step <= b; k++) out.push([tb + k * step, k === 0 ? 'Big Bang' : shortY(k * step, step)]); return [out, 'âge de l’univers']; }
    for (let k = Math.ceil(a / step); k * step <= b; k++) { const t = k * step; out.push([t, k === 0 ? 'aujourd’hui' : (t < 0 ? '−' : '+') + shortY(Math.abs(t), step)]); } return [out, '']; }
  function drawTape() { if (!evtEl.hidden && performance.now() - evtT > 7000) evtEl.hidden = true; const w = tapeEl.clientWidth, h = tapeEl.clientHeight; if (!w || !h) return; const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (tcv.width !== Math.round(w * dpr) || tcv.height !== Math.round(h * dpr)) { tcv.width = Math.round(w * dpr); tcv.height = Math.round(h * dpr); }
    const cs = getComputedStyle(tapeEl), ink = cs.color, x = tcx, lim = tRange(), lo = lim[0], hi = lim[1], W = tapeW(), t0 = S.ty, X = t => w / 2 + (t - t0) / W * (w / 2), OH = 9, f0 = ovF(lo), f1 = ovF(hi), OX = t => (ovF(t) - f0) / (f1 - f0) * w;
    x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, w, h); x.fillStyle = ink;
    x.globalAlpha = 0.13; x.fillRect(0, 0, w, OH); x.globalAlpha = 0.45; for (let k = 1; k <= 11; k++) for (const s of [-1, 1]) { const t = s * Math.pow(10, k); if (t > lo && t < hi) x.fillRect(Math.round(OX(t)), k % 3 === 0 ? 0 : OH - 4, 1, k % 3 === 0 ? OH : 4); }
    x.globalAlpha = 0.85; x.fillRect(Math.round(OX(0)) - 1, 0, 2, OH); x.globalAlpha = 1; x.fillStyle = '#ffb347'; x.fillRect(clamp(OX(t0), 2, w - 2) - 2, 0, 4, OH); x.fillStyle = ink;
    x.globalAlpha = 0.16; if (X(lo) > 0) x.fillRect(0, OH, Math.min(X(lo), w), h - OH); if (X(hi) < w) x.fillRect(Math.max(X(hi), 0), OH, w - Math.max(X(hi), 0), h - OH);
    const tk = tapeTicks(t0, W, tapeStep(W)); x.font = '11px ' + cs.fontFamily; x.textAlign = 'center'; x.textBaseline = 'alphabetic'; let lastR = -1e9;
    for (const q of tk[0]) { const px = X(q[0]); if (px < -40 || px > w + 40) continue; x.globalAlpha = 0.5; x.fillRect(Math.round(px), h - 19, 1, 6); const tw = x.measureText(q[1]).width; if (px - tw / 2 > lastR + 8 && px - tw / 2 > 2 && px + tw / 2 < w - 2) { x.globalAlpha = 0.85; x.fillText(q[1], px, h - 3); lastR = px + tw / 2; } }
    if (tk[1]) { x.globalAlpha = 0.55; x.textAlign = 'right'; x.font = '10px ' + cs.fontFamily; x.fillText(tk[1], w - 6, OH + 11); }
    x.globalAlpha = 1; for (const e of EVL) { if (!evShown(e) || e.now) continue; const px = X(e.t); if (px < -6 || px > w + 6) continue; x.fillStyle = CATCOL[e.cat]; x.beginPath(); x.arc(px, OH + 10, e.imp === 1 ? 4.2 : e.imp === 2 ? 3 : 2.2, 0, TAU); x.fill(); }
    x.fillStyle = '#ffb347'; x.fillRect(Math.round(w / 2) - 1, OH, 2, h - OH - 14); x.beginPath(); x.moveTo(w / 2 - 5, OH); x.lineTo(w / 2 + 5, OH); x.lineTo(w / 2, OH + 6); x.closePath(); x.fill(); }
  { let drag = null; const pos = e => { const r = tapeEl.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top, r.width]; }, jumpT = t => { S.hit = null; setTime(t); S.lastTy = S.ty; };
    const ovSet = (x, w) => { const lim = tRange(), f0 = ovF(lim[0]), f1 = ovF(lim[1]); jumpT(ovInv(f0 + clamp(x / w, 0, 1) * (f1 - f0))); };
    tapeEl.addEventListener('pointerdown', e => { const p = pos(e); try { tapeEl.setPointerCapture(e.pointerId); } catch (err) {} drag = { x: p[0], t0: S.ty, W: tapeW(), ov: p[1] < 12, moved: 0, w: p[2] }; scrubbing = true; S.evCur = null; if (drag.ov) ovSet(p[0], p[2]); e.preventDefault(); });
    tapeEl.addEventListener('pointermove', e => { if (!drag) return; const p = pos(e); drag.moved = Math.max(drag.moved, Math.abs(p[0] - drag.x)); if (drag.ov) ovSet(p[0], p[2]); else if (drag.moved > 3) jumpT(drag.t0 - (p[0] - drag.x) / (p[2] / 2) * drag.W); });
    const up = () => { if (!drag) return; const d = drag; drag = null; scrubbing = false; if (d.ov || d.moved > 3) return; let best = null, bd = 14; for (const ev of EVL) { if (!evShown(ev) || ev.now) continue; const px = d.w / 2 + (ev.t - d.t0) / d.W * (d.w / 2), dd = Math.abs(px - d.x); if (dd < bd) { bd = dd; best = ev; } } if (best) evGo(best); else jumpT(d.t0 + (d.x - d.w / 2) / (d.w / 2) * d.W); };
    tapeEl.addEventListener('pointerup', up); tapeEl.addEventListener('pointercancel', up);
    tapeEl.addEventListener('wheel', e => { e.preventDefault(); e.stopPropagation(); jumpT(S.ty + (e.deltaY || e.deltaX) / 400 * tapeW()); }, { passive: false });
    tapeEl.addEventListener('keydown', e => { const k = e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0; if (!k) return; e.preventDefault(); e.stopPropagation(); jumpT(S.ty + k * tapeW() * (e.shiftKey ? 0.5 : 0.05)); });
    if (window.ResizeObserver) new ResizeObserver(() => document.documentElement.style.setProperty('--bar-h', Math.round($('time').offsetHeight) + 'px')).observe($('time')); }
  /* ---- galaxies naines du Groupe local : chacune suit l'orbite calculée d'après sa vitesse mesurée (Local Volume Database, Pace 2024),
     sous l'attraction de la Voie lactée, d'Andromède et du Grand Nuage de Magellan. Sans déplacement mesuré dans le ciel, une galaxie reste en place, ou suit Andromède si elle en est satellite. ---- */
  const LGO = { list: [], sh: new Float32Array(104 * 3), run: 0, t0: 0, dt: 0.02, n: 0, ready: false };
  /* R18 suite : galaxie sans déplacement mesuré dans le ciel mais avec sa vitesse mesurée le long de la ligne de visée (McConnachie 2012).
     Supposition : elle ne bouge ni de côté ni en tournant autour de la Voie lactée, seulement en s'en rapprochant ou en s'en éloignant (part de côté prise nulle,
     dans le repère du centre de la Voie lactée). La vitesse mesurée fixe alors toute la vitesse ; on l'écrit comme vue du Soleil, comme DATA.LGV.
     Exclues : les satellites d'Andromède (ils la suivent), les galaxies à moins de 50 kpc (pour elles la part de côté domine : supposition trop forte). */
  const LGR = { v: null, vg: {} };
  function lgRadial() { if (LGR.v) return LGR.v; const V = DATA.LGV || {}, X = DATA.LG_X || [], cen = G.lg.centers, out = {};
    cen.forEach((c, i) => { const vl = X[i] && X[i][1]; if (V[i] || c.own || c.m0 || c.grp || vl === null || vl === undefined || !isFinite(vl)) return;
      const q = c.c0, h = [q[0] + gcRelKpc0[0], q[1] + gcRelKpc0[1], q[2] + gcRelKpc0[2]], tr = v => [M[0][0] * v[0] + M[1][0] * v[1] + M[2][0] * v[2], M[0][1] * v[0] + M[1][1] * v[1] + M[2][1] * v[2], M[0][2] * v[0] + M[1][2] * v[1] + M[2][2] * v[2]],
        hg = tr(h), rg = tr(q), dh = Math.hypot(hg[0], hg[1], hg[2]), dr = Math.hypot(rg[0], rg[1], rg[2]); if (!(dr >= 50)) return;
      const vgsr = vl + (hg[0] * SUN_UVW[0] + hg[1] * SUN_UVW[1] + hg[2] * SUN_UVW[2]) / dh;      // vitesse mesurée ramenée au centre de la Voie lactée
      LGR.vg[i] = vgsr; out[i] = [vgsr * rg[0] / dr - SUN_UVW[0], vgsr * rg[1] / dr - SUN_UVW[1], vgsr * rg[2] / dr - SUN_UVW[2], null, vl]; });
    return (LGR.v = out); }
  function lgStart() { const V = DATA.LGV; if (!V || !S.orbit) return; const run = ++LGO.run, O = S.orbit, cen = G.lg.centers, T0 = Math.max(O.t0, -8), T1 = Math.min(O.t0 + (O.n - 1) * O.dt, 12), DT = 0.02, H = 0.004, n = Math.round((T1 - T0) / DT) + 1, ids = Object.keys(V).map(Number).filter(i => cen[i] && !cen[i].own && !cen[i].m0), VR = lgRadial();
    for (const i of Object.keys(VR).map(Number)) ids.push(i);
    LGO.list = []; LGO.t0 = T0; LGO.dt = DT; LGO.n = n; LGO.ready = false; const m3 = [0, 0, 0], lm = [0, 0, 0], a = [0, 0, 0], K2 = G_KPC * 1.0459, LT1 = LMCO.t0 + (LMCO.n - 1) * LMCO.dt;
    const acc = (r, t, o) => { const d = Math.max(Math.hypot(r[0], r[1], r[2]), 1), g = -K2 * mwMass(d) / (d * d * d); o[0] = g * r[0]; o[1] = g * r[1]; o[2] = g * r[2];
      andromedaAt(O, t, m3); const D = Math.hypot(m3[0], m3[1], m3[2]);
      if (D > 5) { const x = r[0] - m3[0], y = r[1] - m3[1], z = r[2] - m3[2], d2 = Math.max(Math.hypot(x, y, z), 3), g2 = K2 * M31_MASS_RATIO * mwMass(d2) / (d2 * d2 * d2), gm = K2 * M31_MASS_RATIO * mwMass(D) / (D * D * D); o[0] -= g2 * x + gm * m3[0]; o[1] -= g2 * y + gm * m3[1]; o[2] -= g2 * z + gm * m3[2]; }      // attraction d'Andromède sur la naine, moins celle qu'elle exerce sur la Voie lactée (on calcule autour de la Voie lactée)
      else { o[0] += g * r[0] * M31_MASS_RATIO; o[1] += g * r[1] * M31_MASS_RATIO; o[2] += g * r[2] * M31_MASS_RATIO; }                                                                                                                                                                          // galaxies fusionnées : leurs masses s'ajoutent
      if (t > LMCO.t0 && t < LT1) { andromedaAt(LMCO, t, lm); const DL = Math.hypot(lm[0], lm[1], lm[2]); if (DL > 2) { const x = r[0] - lm[0], y = r[1] - lm[1], z = r[2] - lm[2], dl = Math.max(Math.hypot(x, y, z), 2), gl = K2 * lmcMass(dl) / (dl * dl * dl), gL = K2 * lmcMass(DL) / (DL * DL * DL); o[0] -= gl * x + gL * lm[0]; o[1] -= gl * y + gL * lm[1]; o[2] -= gl * z + gL * lm[2]; } }
      return o; };
    const one = k => { if (run !== LGO.run) return; if (k >= ids.length) { LGO.ready = true; return; } const i = ids[k], c = cen[i], v0 = V[i] || VR[i], q = c.c0, r0 = [M[0][0] * q[0] + M[1][0] * q[1] + M[2][0] * q[2], M[0][1] * q[0] + M[1][1] * q[1] + M[2][1] * q[2], M[0][2] * q[0] + M[1][2] * q[1] + M[2][2] * q[2]], tab = new Float32Array(n * 3), dist = new Float32Array(n);
      for (const dir of [1, -1]) { if (dir < 0 && T0 >= 0) continue; const r = r0.slice(), v = [(v0[0] + SUN_UVW[0]) * KMS_KPC_GYR, (v0[1] + SUN_UVW[1]) * KMS_KPC_GYR, (v0[2] + SUN_UVW[2]) * KMS_KPC_GYR], h = H * dir, steps = Math.round((dir > 0 ? T1 : -T0) / H); let t = 0;
        for (let s = 0; s <= steps; s++) { if (s % 5 === 0) { const idx = Math.round((t - T0) / DT); if (idx >= 0 && idx < n) { const dx = r[0] - r0[0], dy = r[1] - r0[1], dz = r[2] - r0[2]; tab[idx * 3] = M[0][0] * dx + M[0][1] * dy + M[0][2] * dz; tab[idx * 3 + 1] = M[1][0] * dx + M[1][1] * dy + M[1][2] * dz; tab[idx * 3 + 2] = M[2][0] * dx + M[2][1] * dy + M[2][2] * dz; dist[idx] = Math.hypot(r[0], r[1], r[2]); } }
          acc(r, t, a); v[0] += a[0] * h / 2; v[1] += a[1] * h / 2; v[2] += a[2] * h / 2; r[0] += v[0] * h; r[1] += v[1] * h; r[2] += v[2] * h; t += h; acc(r, t, a); v[0] += a[0] * h / 2; v[1] += a[1] * h / 2; v[2] += a[2] * h / 2; } }
      LGO.list.push({ i, c, tab, dist }); setTimeout(() => one(k + 1), 0); };
    one(0); }
  function lgApply(tG) { const L = LGO.list; if (!L.length) return; const x = clamp((tG - LGO.t0) / LGO.dt, 0, LGO.n - 1.001), k = x | 0, f = x - k, sh = LGO.sh;
    for (const s of L) { const T = s.tab, j = k * 3, dx = lerp(T[j], T[j + 3], f), dy = lerp(T[j + 1], T[j + 4], f), dz = lerp(T[j + 2], T[j + 5], f), c = s.c, o = (s.i + 1) * 3; c.c[0] = c.c0[0] + dx; c.c[1] = c.c0[1] + dy; c.c[2] = c.c0[2] + dz; sh[o] = dx; sh[o + 1] = dy; sh[o + 2] = dz; }
    F.lgSh = sh; }
  function lgTurn(gi, r) { const sp = G.lg.spin[gi], c = G.lg.centers[gi]; if (!c) return; if (c.own) { r.push(['Rotation sur elle-même', 'Tourne à sa vitesse mesurée, environ 250 km/s (Corbelli et al. 2010), simplifiée en une vitesse constante, autour de son axe mesuré ; le dessin des bras est un schéma · mesuré pour la vitesse']); return; }
    if (sp) { r.push(['Rotation sur elle-même', sp.vTxt + ' : un tour en ' + nf(Math.round(sp.turn[1] / 10) * 10, 0) + ' millions d’années à ' + sp.turn[0] + NBSP + 'kpc du centre']); r.push(['Sens de rotation', sp.sense + ' · mesuré']); r.push(['Rotation dans la simulation', 'Vitesse, axe et sens réels. Le dessin des bras est un schéma : il tourne d’un bloc.']); r.push(['Source de la rotation', sp.src]); }
    else r.push(['Rotation sur elle-même', 'Non montrée : cette galaxie naine est dessinée comme un nuage sans structure · inconnu']); }
  function lgMove(gi, r) { const lv = DATA.LGV && DATA.LGV[gi], c = G.lg.centers[gi]; if (!c) return;
    if (c.own) { r.push(['Mouvement dans la simulation', 'Orbite calculée d’après sa vitesse mesurée, sous l’attraction des deux galaxies · scénario']); return; }
    if (c.m0) { r.push(['Mouvement dans la simulation', MAG.c.indexOf(c) === 0 ? 'Orbite calculée d’après sa vitesse mesurée (Kallivayalil et al. 2013) · scénario pour l’avenir lointain' : 'Suit le Grand Nuage, dont il est compagnon : sa propre orbite n’est pas calculée · calculé avec le Grand Nuage']); return; }
    if (lv) { r.push(['Vitesse par rapport à la Voie lactée', nf(Math.round(Math.hypot(lv[0] + SUN_UVW[0], lv[1] + SUN_UVW[1], lv[2] + SUN_UVW[2])), 0) + NBSP + 'km/s (± ' + lv[3] + ' sur la part mesurée dans le ciel)']); r.push(['Mouvement dans la simulation', 'Orbite calculée d’après cette vitesse, sous l’attraction de la Voie lactée, d’Andromède et du Grand Nuage · Probable']); r.push(['Source de la vitesse', (DATA.LGV_SRC && DATA.LGV_SRC[gi]) || 'Local Volume Database (Pace 2024)']); if (c.g.s > 5) r.push(['Limite du calcul', 'Le freinage par la matière noire d’Andromède n’est pas pris en compte : pour une galaxie aussi massive, l’éloignement après le passage est probablement exagéré']); }
    else if (lgRadial()[gi]) { const vg = LGR.vg[gi]; r.push(['Vitesse par rapport au centre de la Voie lactée', (vg < 0 ? 'se rapproche' : 's’éloigne') + ' à ' + nf(Math.abs(Math.round(vg)), 0) + NBSP + 'km/s : la vitesse mesurée vue du Soleil, moins le mouvement du Soleil dans la Voie lactée · calculé']);
      r.push(['Mouvement dans la simulation', 'Orbite calculée d’après cette vitesse, sous l’attraction de la Voie lactée, d’Andromède et du Grand Nuage · scénario']);
      r.push(['Part de côté du mouvement', 'Non mesurée : supposée nulle, la galaxie va tout droit vers la Voie lactée ou s’en éloigne · supposé']); r.push(['Source de la vitesse', 'McConnachie 2012 (vitesse dans l’axe de notre regard)']);
      r.push(['Limite du calcul', 'L’expansion de l’univers et les galaxies au-delà du Groupe local ne sont pas prises en compte : pour une galaxie lointaine, la trajectoire après quelques milliards d’années est incertaine']); }
    else r.push(['Mouvement dans la simulation', c.grp ? 'Suit Andromède, dont elle est satellite : sa propre orbite n’est pas calculée, faute de déplacement mesuré dans le ciel · calculé avec Andromède' : 'Déplacement dans le ciel non mesuré, ou trop incertain : galaxie laissée en place · inconnu']); }
  /* ---- nuage d'Oort vivant : chaque comète du modèle a son orbite autour du Soleil, et chaque étoile du catalogue qui passe à moins de 2 années-lumière la dévie ----
     Le nuage reste hypothétique (personne ne l'a observé directement) : sa forme est un modèle. Ce qui est calculé, c'est sa réponse à la gravité du Soleil et des étoiles de passage. */
  const OO = { el: null, segs: null, enc: [], t: 1e99, st: new Float64Array(6), kv: [0, 0, 0] };
  function oortInit() { const N = G.oort.N, pos = G.oort.pos, rng = makeRng(77), el = new Array(N), st = OO.st, kv = OO.kv, LYAU = LY / AU, K = Rr.K, enc = [], PB = {}; (Rr.passers || []).forEach(o => { PB[o.idx] = o; });
    for (let i = 0; i < N; i++) { const r = [pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]], rr = Math.hypot(r[0], r[1], r[2]) || 1, vc = Math.sqrt(MU_SUN / rr) * Math.sqrt(0.25 + 1.4 * rng()), d = rng.dir(); if (rr < 20000) d[2] *= 0.35 + 0.65 * smoothstep(3000, 20000, rr); const n = vnorm(d);
      el[i] = orbFromState(r, [n[0] * vc, n[1] * vc, n[2] * vc], 0, MU_SUN); }      // vitesse tirée au hasard, toujours en dessous de la vitesse de libération : la comète est liée au Soleil
    for (let i = 0; i < K.N; i++) { const j = i * 3, vx = K.ve[j], vy = K.ve[j + 1], vz = K.ve[j + 2], v2 = vx * vx + vy * vy + vz * vz; if (!(v2 > 0)) continue; const ts = -(K.p0[j] * vx + K.p0[j + 1] * vy + K.p0[j + 2] * vz) / v2; if (!(Math.abs(ts) <= (K.lin && K.lin[i] ? 1.3e7 : 3e6))) continue;
      const bx = K.p0[j] + vx * ts, by = K.p0[j + 1] + vy * ts, bz = K.p0[j + 2] + vz * ts, dd = Math.hypot(bx, by, bz); if (!(dd > 1e-4 && dd < 3.4)) continue; const V = Math.sqrt(v2);
      enc.push({ i, t: ts, d: dd, bS: [bx * LYAU, by * LYAU, bz * LYAU], u: [vx / V, vy / V, vz / V], V: V * LYAU, M: clamp(Rr.star.mass[i] || 0.5, 0.08, 6), kms: V / KMS_LY_YR, name: DATA.STAR_NAMES[i] || (Rr.star.hip[i] ? 'HIP ' + Rr.star.hip[i] : 'sans nom'), ej: 0, inn: 0, hit: 0, pub: PB[i], far: dd * LYAU > 1.4e5 }); }      // far : l'étoile ne pénètre pas dans le nuage, son effet est négligeable
    enc.sort((a, b) => a.t - b.t); const spec = [], hk = new Float32Array(N), ht = new Float64Array(N), note = (i, tc) => { const k = Math.hypot(kv[0], kv[1], kv[2]) / (Math.hypot(st[3], st[4], st[5]) || 1); if (k > hk[i]) { hk[i] = k; ht[i] = tc; } }; const segs = new Array(N).fill(null), fut = enc.filter(e => e.t >= 0), past = enc.filter(e => e.t < 0).reverse();
    const kick = (cur, e) => { orbState(cur, e.t, st); const tc = e.t + starKick(st, e, kv); orbState(cur, tc, st); starKick(st, e, kv); return tc; }, big = () => Math.hypot(kv[0], kv[1], kv[2]) > 0.004 * Math.hypot(st[3], st[4], st[5]);
    for (let i = 0; i < N; i++) { let cur = el[i], list = null;
      for (const e of fut) { if (e.far) continue; const tc = kick(cur, e); if (!big()) continue; const nx = orbFromState([st[0], st[1], st[2]], [st[3] + kv[0], st[4] + kv[1], st[5] + kv[2]], tc, MU_SUN); e.hit++; note(i, tc); if (nx.hyp && !cur.hyp) { e.ej++; spec.push([i, tc, 'comète éjectée']); } if (!nx.hyp && nx.q < 40 && cur.q >= 40) { e.inn++; spec.push([i, tc, 'comète en chute vers les planètes']); } (list = list || [{ from: -Infinity, el: el[i] }]).push({ from: tc, el: nx }); cur = nx; }
      cur = el[i];
      for (const e of past) { if (e.far) continue; const tc = kick(cur, e); if (!big()) continue; const pv = orbFromState([st[0], st[1], st[2]], [st[3] - kv[0], st[4] - kv[1], st[5] - kv[2]], tc, MU_SUN); e.hit++; note(i, tc); if (cur.hyp && !pv.hyp) e.ej++; if (!cur.hyp && cur.q < 40 && pv.q >= 40) e.inn++; list = list || [{ from: -Infinity, el: el[i] }]; list[0].from = tc; list.unshift({ from: -Infinity, el: pv }); cur = pv; }
      segs[i] = list; }
    OO.el = el; OO.segs = segs; OO.enc = enc; OO.t = 1e99; OO.hk = hk; OO.ht = ht; OO.look0 = G.oort.look.slice(); OO.mark = new Uint8Array(N); OO.sp = new Float32Array(K.N * 3);
    (Rr.passers || []).forEach(o => { if (DATA.STAR_LABELS.some(l => l.i === o.idx)) return; const i = o.idx, at = () => { starPositions(K, S.ty, S.ty / 1e9, OO.sp, i, i + 1); return [OO.sp[i * 3] * LY, OO.sp[i * 3 + 1] * LY, OO.sp[i * 3 + 2] * LY]; };
      addLabel(o.n, 'star', 3, 13.9, 17.5, at, { gate: () => { const p = at(); return Math.hypot(p[0], p[1], p[2]) < 7 * LY ? 1 : 0; } }); });      // le nom de l'étoile apparaît quand elle approche du Soleil
    for (const q of spec.slice(0, 16)) { const i = q[0]; OO.mark[i] = 1; addLabel(q[2], '', 3, 13.6, 17.0, () => [pos[i * 3] * AU, pos[i * 3 + 1] * AU, pos[i * 3 + 2] * AU], { gate: () => (S.ty >= q[1] && S.ty < q[1] + 4e6 ? 1 : 0) }); } }
  OO.near = t => { let b = null; for (const e of OO.enc) if (e.hit > 0 && Math.abs(t - e.t) < 1.2e5 && (!b || e.d < b.d)) b = e; return b; };
  function updateOort() { if (S.logR < 13.3 || S.logR > 17.3 || !OO.el) return; const t = S.ty; if (Math.abs(t - OO.t) < 1) return; OO.t = t; const N = G.oort.N, pos = G.oort.pos, segs = OO.segs, el = OO.el, look = G.oort.look, l0 = OO.look0, hk = OO.hk, ht = OO.ht;
    for (let i = 0; i < N; i++) { const L = segs[i]; let o = el[i]; if (L) for (let k = L.length - 1; k >= 0; k--) if (t >= L[k].from) { o = L[k].el; break; } orbPos(o, t, pos, i * 3);
      let g = 0; if (hk[i] > 0.03 && t >= ht[i]) g = clamp(hk[i] * 3, 0, 1) * (o.hyp ? 1 : Math.exp(-(t - ht[i]) / 6e5)); if (OO.mark[i] && t >= ht[i]) g = 1.6; look[i * 2] = l0[i * 2] * (1 + 1.3 * g); look[i * 2 + 1] = Math.min(1, l0[i * 2 + 1] * (1 + 5 * g)); }      // les comètes fortement déviées ressortent un temps ; les éjectées restent marquées
    Rr.oortDirty(); }
  /* ---- ce que l'époque change à l'image : lueur du jeune univers, éclipses ---- */
  const R_SUN = 6.957e8, R_EARTH = 6.3781e6, R_MOON = 1.7374e6;
  function eclipseAt(E, M) { const dM = Math.hypot(M[0], M[1], M[2]), u = [M[0] / dM, M[1] / dM, M[2] / dM], w = [E[0] - M[0], E[1] - M[1], E[2] - M[2]], w2 = w[0] * w[0] + w[1] * w[1] + w[2] * w[2], al = w[0] * u[0] + w[1] * u[1] + w[2] * u[2], out = { sol: null, lun: null, u, v: null, gS: 9, gL: 9 };
    if (al > 0) { const pp = Math.sqrt(Math.max(w2 - al * al, 0)), rp = R_MOON + al * (R_SUN + R_MOON) / dM; out.gS = pp / R_EARTH; if (pp < R_EARTH + rp) { let kind = 'partielle'; if (pp < R_EARTH) { const as = al - Math.sqrt(R_EARTH * R_EARTH - pp * pp); kind = R_MOON - as * (R_SUN - R_MOON) / dM > 0 ? 'totale' : 'annulaire'; } out.sol = kind; } }
    const dE = Math.hypot(E[0], E[1], E[2]), v = [E[0] / dE, E[1] / dE, E[2] / dE], al2 = -(w[0] * v[0] + w[1] * v[1] + w[2] * v[2]); out.v = v;
    if (al2 > 0) { const pp = Math.sqrt(Math.max(w2 - al2 * al2, 0)), ru = 1.02 * (R_EARTH - al2 * (R_SUN - R_EARTH) / dE), rp = 1.02 * (R_EARTH + al2 * (R_SUN + R_EARTH) / dE); out.gL = pp / R_EARTH; if (pp < rp + R_MOON) out.lun = pp < ru - R_MOON ? 'totale' : pp < ru + R_MOON ? 'partielle' : 'par la pénombre'; }
    return out; }
  function eclipseScan(jd0, hrs) { let st = null, bS = [9, 0, null], bL = [9, 0, null]; for (let k = -hrs * 60; k <= hrs * 60; k++) { const jd = jd0 + k / 1440; st = solarSystemAt((jd - JD_J2000) / 36525, st); const E = [st.earth[0] * AU, st.earth[1] * AU, st.earth[2] * AU], M = [(st.earth[0] + st.moonGeo[0]) * AU, (st.earth[1] + st.moonGeo[1]) * AU, (st.earth[2] + st.moonGeo[2]) * AU], ec = eclipseAt(E, M); if (ec.gS < bS[0]) bS = [ec.gS, jd, ec.sol]; if (ec.gL < bL[0]) bL = [ec.gL, jd, ec.lun]; } return { sol: bS, lun: bL }; }
  function updateEpoch() { const C = S.cosmo; F.glow = null; F.cmbT = 0; S.ecl = ''; F.shadow = null;
    if (C.tBang !== null && C.par.Om > 0.01) { const age = S.ty / 1e9 - C.tBang; if (age < 0.2) { const T = 2.7255 / aOfAge(C, Math.max(age, 1e-6)); F.cmbT = T; const k = smoothstep(550, 1700, T) * (0.16 + 0.26 * smoothstep(2200, 4200, T)); if (k > 0.002) { const c = tempRgb(clamp(T, 1000, 12000)); F.glow = [c[0] * k, c[1] * k, c[2] * k]; } } }
    if (S.logR < 10.8 && Math.abs(S.ty) < 4000 && !S.solOff) { const E = bodyPosM('earth'), M = bodyPosM('moon'), ec = eclipseAt(E, M); F.shadow = [M, ec.u, E, ec.v]; S.ecl = ec.sol ? 'Éclipse ' + ec.sol + ' de Soleil en cours : l’ombre de la Lune touche la Terre.' : ec.lun ? 'Éclipse de Lune ' + ec.lun + ' en cours : la Lune traverse l’ombre de la Terre.' : ''; } }
  const GEOERA = [[-4.568e9, 'Hadéen'], [-4.031e9, 'Archéen'], [-2.5e9, 'Protérozoïque'], [-5.388e8, 'Cambrien'], [-4.854e8, 'Ordovicien'], [-4.438e8, 'Silurien'], [-4.192e8, 'Dévonien'], [-3.589e8, 'Carbonifère'], [-2.989e8, 'Permien'], [-2.519e8, 'Trias'], [-2.014e8, 'Jurassique'], [-1.45e8, 'Crétacé'], [-6.6e7, 'Paléogène'], [-2.303e7, 'Néogène'], [-2.58e6, 'Pléistocène'], [-1.17e4, 'Holocène']];
  function eraName() { const C = S.cosmo, t = S.ty; if (C.tBang !== null) { const a = t - C.tBang * 1e9; if (a < 3.7e5) return 'plasma opaque'; if (a < 3e6) return 'première lumière'; if (a < 1.8e8) return 'âges sombres'; if (a < 1e9) return 'aube cosmique'; }
    if (t < GEOERA[0][0]) return 'galaxies en construction'; if (t > 1e4) return ''; let n = ''; for (const g of GEOERA) if (t >= g[0]) n = g[1]; return n + ' (Terre)'; }
  $('s-vt').addEventListener('input', e => { S.vt = +e.target.value; orbitDirty = true; });
  for (const m of M31_MEAS) { const b = document.createElement('button'); b.type = 'button'; b.className = 'btn'; b.textContent = m[0] + ' : ' + Math.round(vtOf(m[1])) + ' km/s'; b.addEventListener('click', () => { S.m31V = m[1]; S.vt = vtOf(m[1]); orbitDirty = true; }); $('vt-meas').appendChild(b); }

  /* ---- affichage tête haute ---- */
  const farCentered = () => !!(S.center && S.cpos && S.logR < 16.55 && vlen(S.cpos) > 1.5 * Math.pow(10, S.logR));      // vue centrée sur un objet, le Soleil loin hors champ
  const placeName = () => {
    const R = Math.pow(10, S.logR);
    if (microOn()) return microLevel(S.logR).place;
    if (S.center && S.cpos && (S.logR < 16.55 || S.center.isGal) && vlen(S.cpos) > 1.5 * Math.pow(10, S.logR)) { const n = String(S.center.name || 'cet objet').replace(/^Étoile /, 'l’étoile ').replace(/^Trou noir central de /, ''); return (/^[AEIOUYÉÈaeiouyéè]/.test(n) ? 'Autour d’' : 'Autour de ') + n; }
    if (S.focus !== 'sun' && R < 0.4 * AU) return S.focus === 'earth' && R > 1.2e8 ? 'Terre et Lune' : BODY[S.focus].name;
    if (R < 0.06 * AU) return 'Soleil';
    if (R < 5 * AU) return 'Système solaire interne';
    if (R < 160 * AU) return 'Système solaire';
    if (R < 3000 * AU) return 'Confins du système solaire';
    if (R < 3.6 * LY) return 'Nuage d’Oort';
    if (R < 420 * LY) return 'Étoiles voisines';
    if (R < 6500 * LY) return 'Bras d’Orion';
    if (R < 4.5e5 * LY) return 'Voie lactée';
    if (R < 1.7e7 * LY) return 'Groupe local';
    if (R < 4.5e8 * LY) return 'Superamas voisins';
    if (R < 9e9 * LY) return 'Toile cosmique';
    return 'Univers observable';
  };
  const provText = lr => S.center && S.center.isGal && S.cpos && vlen(S.cpos) > 1.5 * Math.pow(10, S.logR) ? 'Galaxie reconstruite en volume d’après sa photo réelle : forme et bras réels, épaisseur et côté proche supposés.' : farCentered() ? 'Vue centrée sur cet objet, loin du Soleil. Positions réelles.' : lr < 14.7 ? (S.opts.realSize ? 'Positions et tailles réelles.' : 'Positions réelles. Astres grossis pour rester visibles.')
    : lr < 16.9 ? 'Réservoir de comètes supposé : il n’a jamais été observé directement.'
    : lr < 19.4 ? nf(starTotal(), 0) + ' étoiles à leur position mesurée.'
    : lr < 21.75 ? 'Aspect généré, forme guidée par les mesures. Soleil et amas d’étoiles à leur vraie place.'
    : lr < 23.6 ? (S.opts.realSize || Rr.galExag < 1.05 ? 'Galaxies à leur position mesurée. Leur aspect est généré.' : 'Galaxies à leur position mesurée, grossies pour rester visibles. Leur aspect est généré.')
    : S.opts.simWeb ? 'Toile simulée. Les amas nommés sont à leur vraie place.'
    : lr < LOG.MPC + 3.3 ? 'Galaxies réellement observées. Les zones vides ne sont pas encore cartographiées.'
    : 'Quasars observés, fond diffus mesuré par Planck, limites calculées.';
  const EARTH_TXT = 'Sort de la Terre inconnu : engloutie par le Soleil géant selon Schröder et Smith 2008 et Rasio et al. 1996, pourrait survivre selon Rybicki et Denis 2001. À partir du moment où les marées commencent à resserrer son orbite, la Terre et la Lune ne sont plus dessinées.';
  const SYS_END_TXT = 'Inconnu : des étoiles de passage défont le système solaire. Dans les simulations de Zink, Batygin et Adams (2020), l’instabilité se déclenche environ 30 milliards d’années après la mort du Soleil (vers 38 milliards d’années d’ici), puis les éjections s’étalent sur environ 10 milliards d’années ; la dernière planète part en moyenne 100 milliards d’années après la mort du Soleil. L’ordre et les dates de chaque planète ne sont pas connus : plus aucune n’est dessinée.';
  /* R15 : parts d'impulsion mesurées à la finesse affichée (λ = demi-champ), d'après gen/proton_pdf.js */
  function pdfNote() { const P = Rr.micro && Rr.micro.pdfAt ? Rr.micro.pdfAt(Math.pow(10, S.logR)) : null; if (!P) return ''; const m = P.mom, pc = x => Math.round(100 * x) + NBSP + '%';
    if (P.clamp === 'grossier') return 'Zoomez : à partir d’une finesse de 1,5 × 10⁻¹⁶ m, les mesures disent comment l’impulsion du proton se partage entre ses quarks, des paires de quarks et les gluons. À une finesse plus grossière, cette description ne s’applique pas.';
    return 'Le proton vu à cette finesse : ' + pc(m.uv + m.dv) + ' de son impulsion portée par ses trois quarks principaux, ' + pc(m.sea) + ' par des paires quark-antiquark qui apparaissent et disparaissent, ' + pc(m.g) + ' par les gluons qui les lient (mesures CT18NNLO).' + (P.clamp === 'fin' ? ' Au-delà de cette finesse, les valeurs ne sont pas calculées ici : celles de la plus fine sont gardées.' : ''); }
  function noticeText() {
    const C = S.cosmo, lr = S.logR, age = F.age;
    if (S.lost) return S.lostMsg || '';
    if (Rr.lens && Rr.lens.on && Rr.lens.inside) return 'Inconnu : si près de ' + Rr.lens.name + ', à moins d’une fois et demie la taille de son horizon, la lumière n’est pas calculée ici.';      /* S6 */
    if (microOn()) { const nt = microLevel(lr).note; return (typeof nt === 'function' ? nt() : nt) || ''; }
    if (lr < 17.6 && S.ty >= SYS_END * 1e9) return SYS_END_TXT;      /* vue du système solaire : son état passe avant le calcul d'Andromède */
    if (lr < 13.5 && S.ty / 1e9 >= T_DIV) return EARTH_TXT;      /* R6 : panneau du sort de la Terre, dans le système solaire */
    if (S.dyn && Math.abs((S.dynT !== undefined ? S.dynT : S.ty / 1e9) - S.dyn.t) > 0.04) return 'Calcul de la rencontre avec Andromède : ' + Math.round(clamp((S.dyn.t - S.dyn.t0) / Math.max((S.dynT !== undefined ? S.dynT : S.ty / 1e9) - S.dyn.t0, 1e-6), 0, 1) * 100) + NBSP + '%';
    if (S.hit === 'end') return C.endKind === 'crunch' ? 'Big Crunch : dans ce modèle, l’univers s’effondre ici. Remontez le temps pour continuer.' : C.endKind === 'rip' ? 'Big Rip : dans ce modèle, l’expansion déchire tout ici. Remontez le temps pour continuer.' : 'Limite du calcul atteinte. Remontez le temps pour continuer.';
    if (S.hit === 'start') return C.tBang !== null ? 'Vous êtes à 100 000 ans du Big Bang : l’univers est un plasma opaque. Relancez le temps vers le futur.' : 'Début du calcul atteint. Relancez le temps vers le futur.';
    if (F.cmbT > 0 && C.tBang !== null) { const ay = (S.ty / 1e9 - C.tBang) * 1e9, Tt = nf(Number(F.cmbT.toPrecision(2)), 0) + NBSP + 'K';
      if (ay < 3.7e5) return 'Univers opaque : un plasma à ' + Tt + ' remplit tout l’espace, la lumière n’y circule pas encore.'; if (ay < 3e6) return 'L’univers vient de devenir transparent. Il baigne dans une lueur à ' + Tt + ', qui rougit puis glisse vers l’infrarouge.'; if (ay < 1.8e8) return 'Âges sombres : aucune étoile ne brille encore. Le rayonnement du Big Bang est à ' + Tt + '.'; }
    if (S.ecl && lr < 10.8) return S.ecl;
    if (lr > 13.5 && lr < 17.2) { const e = OO.near(S.ty); if (e) return 'L’étoile ' + e.name + ' passe à ' + nf(Math.round(e.d * LY / AU / 100) * 100, 0) + NBSP + 'UA du Soleil. Son attraction dévie les comètes proches de sa route : sur ' + nf(G.oort.N, 0) + ' comètes simulées, ' + nf(e.hit, 0) + ' changent d’orbite, ' + e.ej + ' sont éjectées et ' + e.inn + ' plongent vers les planètes.'; }
    if (lr < 17.6) { if (S.ty < SS_BORN) return 'À cette époque, le Soleil n’est pas encore né.'; if (S.ty < -4.45e9) return 'Le système solaire est en formation : les planètes grossissent dans un disque de gaz et de poussière. Elles sont montrées sur leurs orbites actuelles, faute de pouvoir reconstituer leurs positions.' + (S.ty < -4.51e9 ? ' La Lune n’existe pas encore.' : ''); if (S.ty > (10.00 - SUN_NOW) * 1e9) return 'À cette époque, le Soleil est une ' + F.sun.phase + ' : ' + sig(F.sun.R, 3) + ' fois son rayon actuel. Les orbites s’élargissent à mesure qu’il perd de la masse.'; if ((lr < 10.9 ? S.moonOff : S.solOff) && S.playing) return 'Le temps défile trop vite pour suivre les orbites : ' + (lr < 10.9 ? 'les lunes tournent' : 'les planètes tournent') + ' ici au ralenti. En pause, tout reprend sa vraie place.'; if (Math.abs(S.ty) > 3050) return 'À plus de 3 000 ans d’aujourd’hui, la position des planètes n’est plus qu’indicative.'; if (Math.abs(S.ty) > 60 && lr > 10.6 && lr < 14.7) return 'À plus de quelques décennies d’aujourd’hui, astéroïdes et objets lointains ne sont plus qu’indicatifs. Les planètes restent exactes.'; }
    else if (lr < 23.6) { if (age < 1) return 'À cette époque, la Voie lactée n’est pas encore formée.'; }
    else if (age < 0.2) return 'Âges sombres : aucune galaxie ne brille encore.';
    return '';
  }
  let lastPlace = '', lastNotice = null, lastCard = null;
  function hud() {
    const R = Math.pow(10, S.logR) * F.aFac, C = S.cosmo;
    const pn = placeName(); if (pn !== lastPlace) { $('place').textContent = lastPlace = pn; }
    { const ml = microOn() && S.logR < 3.2 ? microLevel(S.logR).id : ''; if (ml !== lastMl) { lastMl = ml; if (!S.sel) renderCard(); } }
    $('field').textContent = 'Champ large de ' + fmtDist(2 * R);
    $('prov').textContent = provText(S.logR) + (lcOn && S.logR > 22.5 ? ' Galaxies des relevés placées où leur lumière est partie ; fond diffus et horizons à leur distance d’aujourd’hui.' : '') + (Rr.dustOn ? ' Étoiles assombries par la poussière mesurée entre elles et la vue.' : '') + (Rr.lens.on ? (Rr.lens.inside ? ' Trop près de ' + Rr.lens.name + ' : non calculé ici.' : ' Lumière déviée par ' + Rr.lens.name + ' : calculée (sans rotation, sans disque).') : '');
    const nt = noticeText(); if (nt !== lastNotice) { lastNotice = nt; $('notice').textContent = nt; $('notice').hidden = !nt; }
    renderCard();


    const pxPerM = (Rr.halfMin / Rr.dpr) / R, raw = 110 / pxPerM, km = raw / 1e3, au = raw / AU, ly = raw / LY;
    const unit = raw < 1e3 ? Math.pow(10, Math.floor(Math.log10(raw))) : km < 1e6 ? 1e3 : au < 0.05 ? 1e9 : au < 5000 ? AU : ly < 1e6 ? LY : ly < 1e9 ? LY * 1e6 : LY * 1e9, x = raw / unit, n = Math.pow(10, Math.floor(Math.log10(x))), mm = x / n, nice = (mm < 1.5 ? 1 : mm < 3.5 ? 2 : mm < 7.5 ? 5 : 10) * n * unit;
    $('scale-bar').style.width = (nice * pxPerM).toFixed(1) + 'px'; $('scale-len').textContent = fmtDistShort(nice, 1); $('scale-light').textContent = 'la lumière met ' + fmtLightTime(nice);
    const a = Math.abs(S.ty);
    $('date').textContent = a < 4000 ? (JD_NOW + S.ty * 365.25 >= 2299160.5 ? fmtDate(NOW_MS + S.ty * YEAR_S * 1000, S.speed < 2.5 * DAY_S || !S.playing) : fmtJd(JD_NOW + S.ty * 365.25, false)) : (S.ty > 0 ? 'Dans ' : 'Il y a ') + fmtYears(a);
    { const er = eraName(); $('age').textContent = (C.tBang !== null ? 'Âge de l’univers : ' + fmtYears((S.ty / 1e9 - C.tBang) * 1e9) : 'Univers sans Big Bang dans ce modèle') + (er ? ' · ' + er : ''); }
    let near = -1, nd = 0.4; STOPS.forEach((st, i) => { const d = Math.abs(st.logR - S.logR); if (d < nd) { nd = d; near = i; } }); stopEls.forEach((el, i) => el.classList.toggle('on', i === near));
    if (openKey === 'cosmo') { drawChart(); refreshCosmo(); }
  }

  // Un même objet, une seule place : le trou noir central d'une galaxie proche est ramené à la position de sa galaxie (les deux catalogues donnent des distances un peu différentes).
  { const B = Rr.BHM.pos, N = Rr.pick.nPos, cand = []; for (let j = 0; j < N.length / 3; j++) cand.push([N[j * 3], N[j * 3 + 1], N[j * 3 + 2]]); for (const c of G.lg.centers) cand.push([c.c[0] / 1000, c.c[1] / 1000, c.c[2] / 1000]);
    for (let i = 0; i < Rr.BHM.N; i++) { const x = B[i * 3], y = B[i * 3 + 1], z = B[i * 3 + 2], d = Math.hypot(x, y, z); if (!(d > 0) || d > 14) continue; let best = null, bc = Math.cos(0.15 * DEG);
      for (const q of cand) { const dq = Math.hypot(q[0], q[1], q[2]); if (!(dq > 0) || dq / d < 0.6 || dq / d > 1.6) continue; const cs = (x * q[0] + y * q[1] + z * q[2]) / (d * dq); if (cs > bc) { bc = cs; best = q; } }
      if (best) { B[i * 3] = best[0]; B[i * 3 + 1] = best[1]; B[i * 3 + 2] = best[2]; } } Rr.bhmDirty(); }
  /* ---- étoiles vues de près ----
     Le nuage d'étoiles est dessiné en simple précision : à quelques unités astronomiques d'une étoile lointaine, sa position saute de plusieurs millions de km.
     Quand la vue suit un objet et s'en approche, les étoiles situées à moins de 0,02 année-lumière sont donc retirées du nuage et redessinées une à une, placées en double précision, à leur taille réelle. */
  const starRadM = (MV, bv) => { const T = bvTemp(bv), Lb = Math.pow(10, 0.4 * (4.83 - MV)) * Math.pow(10, -0.4 * (bcV(T) - bcV(5772))); return 6.957e8 * clamp(Math.sqrt(Lb) * Math.pow(5772 / T, 2), 0.008, 1800); };
  function findStarsNear(c, rad) { const cx = c[0] / LY, cy = c[1] / LY, cz = c[2] / LY, out = [], r2 = rad * rad;
    for (const st of [{ N: Rr.star.N, pos: Rr.starPos, mag: Rr.star.mag, bv: Rr.star.bv }, Rr.star2]) { const sp = st.pos; for (let i = 0; i < st.N; i++) { const dx = sp[i * 3] - cx; if (dx > rad || dx < -rad) continue; const dy = sp[i * 3 + 1] - cy, dz = sp[i * 3 + 2] - cz; if (dx * dx + dy * dy + dz * dz < r2) out.push({ get: () => [sp[i * 3] * LY, sp[i * 3 + 1] * LY, sp[i * 3 + 2] * LY], mag: st.mag[i], bv: st.bv[i] }); } }
    for (const T of Rr.tiles) if (T.kind === 'star') { const sp = T.pos, vl = T.vel, kv = S.ty * 2 * KMS_LY_YR; for (let i = 0; i < T.n; i++) { const j = i * 3, dx = sp[j] + vl[j] * kv - cx; if (dx > rad || dx < -rad) continue; const dy = sp[j + 1] + vl[j + 1] * kv - cy, dz = sp[j + 2] + vl[j + 2] * kv - cz;
        if (dx * dx + dy * dy + dz * dz < r2) out.push({ get: () => { const k = S.ty * 2 * KMS_LY_YR; return [(sp[j] + vl[j] * k) * LY, (sp[j + 1] + vl[j + 1] * k) * LY, (sp[j + 2] + vl[j + 2] * k) * LY]; }, mag: T.mag[i], bv: T.ci[i] / 80 - 0.5 }); } }
    out.sort((a, b) => a.mag - b.mag); return out.slice(0, 8).map(q => { q.radM = starRadM(q.mag, q.bv); q.col = bvToRgb(q.bv); return q; }); }
  function updateNear() { const o = S.center; F.nearStars = null; F.nearK = 0; F.nearR = 0; if (!o || S.logR > 14.7) return; const c = o.get(); if (!(vlen(c) > 2e15)) return;
    if (S.nearFor !== o) { S.nearFor = o; S.nearList = findStarsNear(c, 0.02); const me = S.nearList.find(q => { const p = q.get(); return Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]) < 3e9; }); o.radM = me ? me.radM : 0; }
    if (!S.nearList || !S.nearList.length) return; F.nearK = fadeOut(S.logR, 14.1, 14.5) * ease(S.ck); F.nearR = F.nearK > 0.5 ? 0.02 : 0; F.nearStars = S.nearList.map(q => ({ pos: q.get(), radM: q.radM, col: q.col })); }
  /* ---- photos réelles de galaxies (relevés Legacy Survey et DSS) ---- */
  const PHOTO_MANIFEST = /*__PHOTOS__*/['641db3b8d46d6ec795123aa11aad2ceb', '872d4f4c0784995193befc9fe42b671d', '7bbc549f93f44b56c1dc408d48a1c5fe'];
  const PH = [], PHL = { req: false }; { const pho = DATA.PHOTOS, pole = [0, Math.sin(23.4392911 * DEG), Math.cos(23.4392911 * DEG)];
    for (let qi = 0; qi < (pho ? pho.list.length : 0); qi++) { const q = pho.list[qi], kind = q[0], i = q[1]; let get = null, c = null;
      if (kind === 'lg') { c = G.lg.centers.find(c => c.g.n === DATA.LOCAL[i].n); if (c) get = () => add3(F.gcRel, c.c, KPC); }
      else if (kind === 'near') get = () => add3(F.gcRel, [Rr.pick.nPos[i * 3], Rr.pick.nPos[i * 3 + 1], Rr.pick.nPos[i * 3 + 2]], MPC * F.cos.a);
      else get = () => add3(F.gcRel, [Rr.BHM.pos[i * 3], Rr.BHM.pos[i * 3 + 1], Rr.BHM.pos[i * 3 + 2]], MPC * F.cos.a);
      if (!get) continue; const n = pho.cells[q[2]], cell = pho.px[q[2]] / 2048; PH.push({ get, c, atlas: q[2], uv: [(q[3] % n) * cell, 1 - (Math.floor(q[3] / n) + 1) * cell, cell], tanH: Math.tan(q[4] / 60 * DEG / 2), floor: (DATA.PH3 || [])[qi] ? clamp((DATA.PH3[qi][6] || 0) + 0.04, q[5] ? 0.16 : 0.07, 0.7) : (q[5] ? 0.3 : 0.1), half: 0, e: null, n: null, l: null, pole, id: qi, g3: (DATA.PH3 || [])[qi] || null, gray: !!q[5] }); } }
  function photoInit(p) { const c = p.get(), d = vlen(c) || 1, r = [c[0] / d, c[1] / d, c[2] / d]; p.half = d * p.tanH; p.e = vnorm(vcross(p.pole, r)); p.n = vcross(r, p.e); p.l = r; }      // est et nord sur le ciel, vus du Soleil
  function photoNear(o) { if (!PH.length || !o || !o.get || !F.gcRel) return null; const q = o.get(); let best = null, bd = 1e99; for (const p of PH) { if (!p.half) photoInit(p); const c = p.get(), d = Math.hypot(c[0] - q[0], c[1] - q[1], c[2] - q[2]); if (d < Math.max(0.3 * p.half, 6e19) && d < bd) { bd = d; best = p; } } return best; }
  function updatePhotos() { F.photos = null; F.photoHide = null; F.m31Hide = 0; if (!PH.length || S.logR < 18.6 || Math.abs(S.ty) > 2e7) return;
    if (!PHL.req) { PHL.req = true; Rr.loadPhotos((window.__PHOTOS || PHOTO_MANIFEST).map(u => (/[./]/.test(u) ? u : '/_blob/' + u))); }
    const R = Math.pow(10, S.logR), tg = F.tg, L = [], age = fadeOut(Math.abs(S.ty), 5e6, 2e7);
    for (const p of PH) { if (p.c && p.c.gone) continue; if (!p.half) photoInit(p); const sz = p.half / R; if (sz < 0.03 || sz > 60) continue; const c = p.get(), d = Math.hypot(c[0] - tg[0], c[1] - tg[1], c[2] - tg[2]); if (d - p.half > 2.4 * R) continue;
      L.push({ c, e: p.e, n: p.n, l: p.l, id: p.id, g3: p.g3, gray: p.gray, tier: Q.gal > 150000 ? 2 : Q.gal > 80000 ? 1 : 0, half: p.half, atlas: p.atlas, uv: p.uv, floor: p.floor, sz, op: smoothstep(0.03, 0.1, sz) * fadeOut(sz, 25, 60) * age, src: p }); }
    L.sort((a, b) => b.sz - a.sz); F.photos = L.slice(0, 14); F.photoHide = null; F.m31Hide = 0;
    for (const q of F.photos) { const c = q.src.c; if (!c || q.op < 0.05) continue; if (c.own) F.m31Hide = Math.max(F.m31Hide, q.op); else if (!F.photoHide || q.op > F.photoHide.k) F.photoHide = { c: c.m0 || c.c0 || c.c, k: Math.min(1, q.op) }; } }
  /* ---- recherche par nom : un index construit à la première utilisation ---- */
  let FIDX = null; const fold = t => String(t).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9+*]+/g, ' ').trim();
  function jump(o, lr) { pushHist(); select(o); flyTo(o, o.lr || lr); openPanel(null); }
  function findIndex() { if (FIDX) return FIDX; const X = [], add = (name, kind, go) => { if (name) X.push([fold(name), name, kind, go]); }, lrOf = o => clamp(Math.log10(Math.hypot(o.orbit.P[0], o.orbit.P[1], o.orbit.P[2]) * AU * 2.4), 11.2, 14.6);
    for (const k in BODY) add(BODY[k].name, k === 'sun' ? 'étoile' : k === 'moon' ? 'lune de la Terre' : 'planète', () => { select(null); focusBody(k); openPanel(null); });
    KO.forEach((m, k) => m.kind !== 'exo' && add(m.kind === 'sstar' ? 'Étoile ' + m.n : m.n, m.kind === 'moon' ? 'lune de ' + PLN[m.p] : m.kind === 'sstar' ? 'près du trou noir central' : 'sonde spatiale', () => jump(selMoon(k), m.kind === 'probe' ? 13.5 : clamp(Math.log10(m.aAU * AU * 2.4), 6.6, 15.6))));
    Object.keys(DATA.STAR_NAMES).forEach(k => add(DATA.STAR_NAMES[k], 'étoile', () => jump(selStar(+k), 16.4)));
    for (const tag of ['AST', 'TNO']) NM[tag].forEach((t, i) => { const q = t.split('~'); if (i < Rr[tag].count) add(q[0] ? q[0] + ' (' + q[1] + ')' : q[1], tag === 'AST' ? 'astéroïde' : 'objet lointain', () => { const o = orbPlus(selBody(tag, i)); jump(o, lrOf(o)); }); });
    COMN.forEach((n, i) => add(n, 'comète', () => { const o = orbPlus(selComet(i)); jump(o, lrOf(o)); }));
    for (const T of Rr.tiles) if (T.kind === 'ast' && TL.astN) for (let i = 0; i < T.n; i++) { const q = (TL.astN[i] || '').split('~'); if (q[0]) add(q[0] + ' (' + q[1] + ')', 'astéroïde', () => { const o = selAstT(T, i); jump(o, lrOf(o)); }); }
    EXON.forEach((n, i) => add(n, 'étoile à planètes', () => jump(selExo(i), 16.6)));
    PSRN.forEach((n, i) => add('PSR ' + n, 'pulsar', () => jump(selPsr(i), 18.9)));
    DATA.BHS.names.forEach((n, i) => add(n, 'trou noir', () => jump(selBHS(i), 18.9))); DATA.BHM.names.forEach((n, i) => add(n, 'trou noir supermassif', () => jump(selBHM(i), 23.3))); add('Sagittarius A*', 'trou noir central', () => jump(selSgrA(), 19.9));
    NM.clu.forEach((n, i) => add(n, 'amas d’étoiles', () => jump(selCluster(i), 18.9)));
    for (const c of G.lg.centers) add(c.g.n, 'galaxie du Groupe local', () => jump(selLG(c), 21.6)); NM.near.forEach((n, i) => add(n, 'galaxie proche', () => jump(selNear(i), 22.6)));
    return (FIDX = X); }
  const QUICK = [['Échelles', STOPS.map((st, k) => [st.name, 's' + k])], ['Système solaire', ['Soleil', 'Mercure', 'Vénus', 'Terre', 'Lune', 'Mars', 'Jupiter', 'Saturne', 'Uranus', 'Neptune', 'Pluton', 'Cérès', '1P/Halley', 'Voyager 1'].map(n => [n, n])],
    ['Étoiles', ['Alpha du Centaure', 'Sirius', 'Véga', 'Bételgeuse', 'TRAPPIST-1'].map(n => [n, n])], ['Galaxie et au-delà', ['Sagittarius A*', 'Étoile S2', 'Cygnus X-1', 'Grand Nuage de Magellan', 'Andromède', 'M87'].map(n => [n, n])]];
  const quickHTML = () => QUICK.map(g => '<h3>' + g[0] + '</h3><div class="chips">' + g[1].map(c => '<button type="button" data-g="' + c[1] + '">' + (c[0] === '1P/Halley' ? 'Comète de Halley' : c[0]) + '</button>').join('') + '</div>').join('');
  function goName(n) { const X = findIndex(), q = fold(n); let best = -1; for (let i = 0; i < X.length; i++) { const t = X[i][0]; if (t === q) { best = i; break; } if (t.indexOf(q) === 0 && (best < 0 || t.length < X[best][0].length)) best = i; } if (best >= 0) X[best][3](); return best >= 0; }
  function findRun(txt) { const q = fold(txt), box = $('find-res'); if (q.length < 2) { box.innerHTML = quickHTML(); return []; } const X = findIndex(), a = [], b = [];
    for (let i = 0; i < X.length && a.length < 12; i++) { const p = X[i][0].indexOf(q); if (p === 0 || (p > 0 && X[i][0][p - 1] === ' ')) a.push(i); else if (p > 0 && b.length < 12) b.push(i); }
    a.sort((x, y) => X[x][0].length - X[y][0].length); const res = a.concat(b).slice(0, 12); box.innerHTML = res.length ? res.map(i => '<button type="button" data-i="' + i + '">' + X[i][1].replace(/</g, '&lt;') + '<small>' + X[i][2] + '</small></button>').join('') : '<p class="hint">Rien trouvé à ce nom.</p>'; return res; }
  $('find-q').addEventListener('input', e => findRun(e.target.value));
  $('find-res').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; const g = b.dataset.g; if (g && /^s\d$/.test(g)) { pushHist(); select(null); const st = STOPS[+g[1]]; goTo(st.logR, { az: st.az, el: st.el, focus: st.focus || 'sun', speed: st.speed, noHist: true }); openPanel(null); } else if (g) goName(g); else FIDX[+b.dataset.i][3](); });
  $('b-find').addEventListener('click', () => { loadAstNames(); findRun($('find-q').value); if (matchMedia('(pointer:fine)').matches) setTimeout(() => { if (!$('p-find').hidden) $('find-q').focus(); }, 60); });
  /* ---- données en flux : étoiles et galaxies supplémentaires, téléchargées par morceaux après le démarrage ----
     Le fichier arrive en continu ; chaque morceau est décodé puis affiché aussitôt, quelques millisecondes par image au plus.
     Les étoiles sont rangées de la plus brillante à la plus faible : si l'appareil peine, on n'affiche que le début de la liste. */
  const TILE_MANIFEST = /*__TILES__*/[{ kind: 'ast', id: '02679a4195f9f4142a2a12ddcad32982', n: 123530, mb: 4.6, names: '37ecb71973bf22d6d05e33f12ebf5653' }, { kind: 'star', id: 'c8120218b39b4317da101cd71ff778d5', n: 1300000, mb: 19.1 }, { kind: 'gal', id: 'd140e2dfab0788aa99836e05d2bd9533', n: 928536, mb: 7.4 }, { kind: 'star', id: '6abab13f612fe4c2a29bfc02393fe2be', n: 610619, mb: 9.0 }, { kind: 'star', id: '51832b93367a59bbe12cbbdd9106c771', n: 1300000, mb: 19.1 }, { kind: 'gal', id: '457a5f01d92639aea7bb7611d72d8866', n: 1975045, mb: 15.8 }, { kind: 'star', id: '8c1fe22a32703cb3f187dbcd3882571c', n: 733631, mb: 10.8 }, { kind: 'star', id: '745dae6e8c58e90ba6865c98cd46f17d', n: 1300000, mb: 19.1 }, { kind: 'gal', id: '1f6acc40b62fd335851c42c74f069703', n: 2206662, mb: 17.7 }, { kind: 'star', id: '12e1f505b64651754d1026bfb29471ee', n: 650394, mb: 9.5 }];
  const TL = { list: (window.__TILES_URL ? [] : window.__TILES || TILE_MANIFEST).map(m => Object.assign({ state: 'wait', got: 0 }, m)), ema: 16, frac: window.__NOADAPT ? 1 : 0.22, fracG: window.__NOADAPT ? 1 : 0.3, busy: false, on: tier >= 2 || !!window.__TILES_ON, err: 0, tick: 0, max: window.__TILES_ON ? 99 : (navigator.deviceMemory || 8) >= 8 ? 7 : (navigator.deviceMemory || 8) >= 4 ? 5 : 3 };
  if (window.__TILES_URL) fetch(window.__TILES_URL).then(r => r.json()).then(L => { TL.list = L.map(m => Object.assign({ state: 'wait', got: 0 }, m)); }).catch(() => {});      // site autonome : la liste des fichiers est à côté de la page
  function starTotal() { let n = Rr.star.N + Rr.star2.N; for (const T of Rr.tiles) if (T.kind === 'star') n += T.n; return n; }
  const nextFrame = () => new Promise(r => requestAnimationFrame(r));
  async function loadTile(m) {
    m.state = 'load'; const res = await fetch(m.url || ('/_blob/' + m.id)); if (!res.ok) throw new Error('HTTP ' + res.status);
    const T = m.kind === 'star' ? Rr.addStarTile(m.n) : m.kind === 'ast' ? Rr.addAstTile(m.n) : Rr.addGalTile(m.n), rd = res.body && res.body.getReader ? res.body.getReader() : null, td = new TextDecoder(), rec = T.rec; m.T = T; let txt = '', carry = new Uint8Array(0);
    const feed = async by => { let b = by; if (carry.length) { b = new Uint8Array(carry.length + by.length); b.set(carry); b.set(by, carry.length); }      // au plus 18 000 objets par image : jamais plus de quelques millisecondes d'affilée
      let off = 0; while (b.length - off >= rec && T.n < T.cap) { const nr = Math.min(Math.floor((b.length - off) / rec), 18000, T.cap - T.n); T.append(b, off, nr); off += nr * rec; m.got = T.n; await nextFrame(); }
      carry = b.slice(off); };
    const eat = async final => { while (txt.length >= 4 && (final || txt.length >= 65536)) { const k = Math.min(txt.length - txt.length % 4, 262144), bin = atob(txt.slice(0, k)); txt = txt.slice(k); const b = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) b[i] = bin.charCodeAt(i); await feed(b); } };
    if (m.bin) { if (!rd) await feed(new Uint8Array(await res.arrayBuffer())); else for (;;) { const { done, value } = await rd.read(); if (done) break; await feed(value); } }       // fichier binaire (site autonome)
    else { if (!rd) txt = (await res.text()).replace(/\s/g, ''); else for (;;) { const { done, value } = await rd.read(); if (done) break; txt += td.decode(value, { stream: true }).replace(/\s/g, ''); await eat(false); } await eat(true); }
    if (m.kind === 'star') await Rr.buildCells(T, nextFrame);
    m.state = 'done';
  }
  function tileStatus() {
    const el = $('tile-status'), bt = $('b-tiles'); if (!TL.list.length) { el.textContent = 'Aucune donnée supplémentaire n’est attachée à cette page.'; bt.hidden = true; return; }
    const sum = (kind, k) => TL.list.reduce((a, m) => a + (!kind || m.kind === kind ? (m[k] || 0) : 0), 0), mb = Math.round(sum(null, 'mb')), fin = TL.list.every(m => m.state === 'done' || m.state === 'err'), key = TL.on ? 'got' : 'n';
    el.textContent = (TL.cut && !TL.on ? 'Les données détaillées ont été coupées : la carte graphique n’a pas suivi. ' : '') + (TL.on ? (fin ? 'Chargé : ' : 'Chargement en cours : ') : 'Disponible : ') + nf(sum('star', key), 0) + ' étoiles, ' + nf(sum('gal', key), 0) + ' galaxies et quasars et ' + nf(sum('ast', key), 0) + ' astéroïdes en plus' + (TL.on ? '.' : ' (' + mb + ' Mo à télécharger).')
      + (TL.err ? ' Un téléchargement a échoué.' : '') + (TL.on && TL.frac < 0.97 ? ' Pour rester fluide, ' + Math.round(TL.frac * 100) + ' % des étoiles supplémentaires sont affichées, les plus brillantes.' : '');
    bt.hidden = TL.on && !TL.list.some((m, k) => m.state === 'wait' && k >= TL.max); bt.textContent = (TL.on ? 'Charger encore plus de données (' : 'Charger les données détaillées (') + Math.round(TL.list.reduce((a, m, k) => a + (m.state === 'wait' && (!TL.on || k >= TL.max) ? m.mb || 0 : 0), 0)) + ' Mo)';
    $('n-stars').textContent = nf(starTotal(), 0); let ng = DATA.SURV_N[0] + DATA.SURV_N[1] + DATA.SURV_N[2]; for (const T of Rr.tiles) if (T.kind === 'gal') ng += T.n; $('n-surv').textContent = nf(ng, 0);
  }
  $('b-tiles').addEventListener('click', () => { if (!TL.cut) TL.max = 99; else if (TL.on) TL.max += 2; TL.on = true; tileStatus(); });
  $('card-more').addEventListener('click', () => { S.more = !S.more; renderCard(); });
  $('n-back').addEventListener('click', goBack); $('n-home').addEventListener('click', goHome); $('n-out').addEventListener('click', () => stepZoom(1)); $('n-in').addEventListener('click', () => stepZoom(-1)); syncNav();
  { let seen = false; try { seen = !!localStorage.getItem('univers-aide'); } catch (e) {}      // rappel des gestes, une seule fois
    if (!seen && !window.__NOADAPT) { const h = $('hint'), off = () => { h.hidden = true; try { localStorage.setItem('univers-aide', '1'); } catch (e) {} }; setTimeout(() => { h.hidden = false; }, 1500); setTimeout(off, 15000); h.addEventListener('click', off); canvas.addEventListener('pointerdown', () => setTimeout(off, 3000), { once: true }); } }
  function tilesTick(dtMs) {
    TL.ema += (Math.min(dtMs, 100) - TL.ema) * 0.05; const adapt = !window.__NOADAPT, gov = f => TL.ema > 27 ? Math.max(0.12, f * 0.985) : TL.ema < 18 ? Math.min(1, f * 1.004 + 0.001) : f;
    if (adapt && Rr.vis) { if (Rr.vis.stars > 0.3 && Math.abs(S.ty) < 3e6) TL.frac = gov(TL.frac); if (Rr.vis.surv > 0.3) TL.fracG = gov(TL.fracG); }
    for (const m of TL.list) if (m.T) m.T.draw = Math.floor(m.T.n * (m.kind === 'star' ? TL.frac : m.kind === 'ast' ? 1 : TL.fracG));
    Rr.mcut = 13.2 + 3.75 * Math.log10(TL.frac);      // si l'appareil peine, on coupe d'abord les étoiles les plus faibles
    if (TL.on && !TL.busy && frames > 90 && (TL.ema < 24 || !adapt) && document.visibilityState === 'visible') { const m = TL.list.find((m, k) => m.state === 'wait' && k < TL.max);
      if (m) { TL.busy = true; loadTile(m).catch(e => { m.state = 'err'; m.error = String(e && e.message || e); TL.err++; }).then(() => { TL.busy = false; tileStatus(); }); } }
    if (++TL.tick % 30 === 0) tileStatus();
  }
  /* ---- reprise après un décrochage de la carte graphique ----
     Quand le navigateur retire le contexte graphique (mémoire pleine, pilote relancé), l'image se fige ou devient noire.
     On mémorise alors où l'on était, on recharge la page, et on repart au même endroit, sans les données détaillées. */
  const REPRISE = 'univers-reprise'; let lostOnce = false;
  function onLost(e) { if (e && e.preventDefault) e.preventDefault(); if (lostOnce) return; lostOnce = true; let n = 0;
    try { const old = JSON.parse(sessionStorage.getItem(REPRISE) || 'null'); if (old && Date.now() - old.t < 180000) n = old.n || 0;
      sessionStorage.setItem(REPRISE, JSON.stringify({ t: Date.now(), n: n + 1, lr: S.anim ? S.anim.l1 : S.logR, az: S.az, el: S.el, ty: S.ty, focus: S.focus, center: S.center && S.center.name ? S.center.name : null, tiles: TL.list.filter(m => m.state !== 'wait').length })); } catch (err) {}
    S.lostMsg = n >= 2 ? 'L’affichage s’est interrompu plusieurs fois : la carte graphique ne suit pas. Recharge la page.' : 'La carte graphique a décroché : l’affichage reprend dans un instant…'; S.lost = true; const nt = $('notice'); nt.hidden = false; nt.textContent = S.lostMsg;
    if (n < 2) setTimeout(() => { try { location.reload(); } catch (err) {} }, 700); }
  canvas.addEventListener('webglcontextlost', onLost, false);
  { let rs = null; try { rs = JSON.parse(sessionStorage.getItem(REPRISE) || 'null'); } catch (err) {}
    if (rs && Date.now() - rs.t < 60000) { S.logR = clamp(rs.lr, LMIN, LMAX); S.az = rs.az; S.el = rs.el; S.anim = null; if (rs.focus && rs.focus !== 'sun' && BODY[rs.focus]) setFocus(rs.focus, 0.01); if (isFinite(rs.ty)) S.hit = setTime(rs.ty); S.resumed = true;
      if (rs.center) setTimeout(() => { const back = () => { S.anim = null; S.logR = clamp(rs.lr, LMIN, LMAX); S.az = rs.az; S.el = rs.el; };      // on retrouve l'objet suivi par son nom
        try { const ok = goName(rs.center.replace(/^Trou noir central de /, '')); if (ok && S.center && S.center.name === rs.center) { back(); S.ck = 1; } else { select(null); back(); } } catch (err) { back(); } }, 0);
      if (rs.tiles) { TL.on = false; TL.cut = true; TL.max = Math.max(1, Math.floor(rs.tiles / 2)); } } }
  /* ---- taille, qualité adaptative ---- */
  let dprScale = 1, slow = 0, fast = 0;
  function resize() {
    const w = Math.max(innerWidth, 2), h = Math.max(innerHeight, 2), base = Math.min(window.devicePixelRatio || 1, S.lite ? 1 : Q.dpr);
    Rr.bloom = Q.bloom && !S.lite && dprScale > 0.55;
    const ss = window.__SS || ((window.devicePixelRatio || 1) < 1.3 && Q.dpr >= 2 && !S.lite && !window.__NOADAPT ? 1.5 : 1);      // écran peu dense : on calcule l'image plus finement, pour lisser les bords
    Rr.resize(w, h, Math.max(0.6, base * ss * dprScale));
    document.documentElement.style.setProperty('--bar-h', $('time').offsetHeight + 'px');
    hudBox = { w: $('top').offsetWidth, h: $('top').offsetHeight + 6, bar: $('time').offsetHeight + 12 };
  }
  addEventListener('resize', resize); resize();

  /* ---- boucle ---- */
  let last = performance.now(), hudT = 0, frames = 0;
  function step(now) {
    const wall = now / 1000, dt = Math.min(0.1, Math.max(0.001, (now - last) / 1000)); last = now;
    if (S.anim) { const A = S.anim, k = clamp((wall - A.t0) / A.dur, 0, 1), e = ease(k); S.logR = lerp(A.l0, A.l1, e); S.az = lerp(A.a0, A.a1, e); S.el = lerp(A.e0, A.e1, e); if (k >= 1) S.anim = null; }
    S.logR = clampZoom(S.logR);
    let stepY = 0;
    if (S.playing && !scrubbing) { const before = S.ty, hit = setTime(S.ty + S.dir * S.speed * dt / YEAR_S); stepY = Math.abs(S.ty - before); evCross(before, S.ty); if (hit) { S.playing = false; S.hit = hit; syncPlay(); } }
    S.dmMix += clamp((S.opts.dm ? 1 : 0) - S.dmMix, -dt * 1.4, dt * 1.4);
    S.beltYears += clamp(S.ty - S.lastTy, -0.02, 0.02); S.lastTy = S.ty;
    { // Horloges d'affichage des orbites. Quand le temps défile trop vite pour qu'une orbite soit suivie à l'écran, l'astre continue de tourner aussi vite que l'image
      // peut le montrer, au lieu de sauter au hasard d'un bout à l'autre de son orbite. En pause ou à vitesse modérée, tout reprend sa vraie place.
      const dS = S.ty - (S.prevTy === undefined ? S.ty : S.prevTy), jumped = Math.abs(Math.abs(dS) - stepY) > 1e-7 + 1e-9 * Math.abs(S.ty); S.prevTy = S.ty;
      const capS = clamp(0.0134 * Math.pow(Math.pow(10, S.logR) / AU, 0.4), 0.0012, 0.08), lag = (off, cap) => (jumped || stepY <= cap ? 0 : off - Math.sign(dS) * (stepY - cap));
      S.solOff = lag(S.solOff || 0, capS); S.moonOff = lag(S.moonOff || 0, 0.02 / 365.25); S.sOff = lag(S.sOff || 0, 0.05); S.capS = capS; }
    sol = solarSystemAt(T_NOW + (S.ty + S.solOff) / 100, sol);
    const C = S.cosmo, cs = cosmoAt(C, S.ty / 1e9, F.cos);
    const tG = S.ty / 1e9, ss = sunState(tG, SS); F.sun = ss; F.sunCol = tempRgb(ss.T); F.orb = 1 / ss.M; F.orbP = F.orbP || {}; for (const k in TIDE_P) F.orbP[k] = tideAt(TIDE_P[k], tG); F.orbP.earth = tideAt(TIDE_E, Math.min(tG, T_DIV)); F.eng.mercury = tG >= ENG.mercury; F.eng.venus = tG >= ENG.venus; F.eng.earth = tG >= ENG.earth; for (const k of SYS_PL) F.eng[k] = tG >= SYS_END; F.sysK = tG < SYS_END ? 1 : 0;      /* petits corps et nuage d'Oort : coupure nette avec le système solaire (R7), plus de fondu */ F.ringsGone = tG > FATE.rings;
    F.ty = S.ty; F.tMyr = S.ty / 1e6; F.tEff = S.T1 + S.T2 * (oSunNo / oSunDM); orbRequest(Rr.K, F.tEff, S.T2 === 0, Math.abs(S.ty) > 2e6); if (S.playing) F.flash = Math.max(3e-7, 1.3 * S.speed / YEAR_S / 1e6); else if (!F.flash) F.flash = 3e-7;
    if (orbitDirty) { orbitDirty = false; if (!S.m31V) S.m31V = M31_MEAS[0][1]; const O = S.orbit = andromedaOrbit(S.cosmo, S.vt, S.m31V); andromedaAt(O, 0, m31r0); lgStart(); S.dyn = null; S.tOn = null;
      for (let i = Math.round(-O.t0 / O.dt); i < O.n; i++) if (Math.hypot(O.r[i * 3], O.r[i * 3 + 1], O.r[i * 3 + 2]) < 150) { S.tOn = Math.max(0.02, O.t0 + i * O.dt - 0.35); break; }
      buildEvents(); }
    { andromedaAt(S.orbit, tG, m31r); const sh = mulM(M, [m31r[0] - m31r0[0], m31r[1] - m31r0[1], m31r[2] - m31r0[2]]); F.lgShift = sh;
      for (const c of G.lg.centers) if (c.grp) { c.c[0] = c.c0[0] + sh[0]; c.c[1] = c.c0[1] + sh[1]; c.c[2] = c.c0[2] + sh[2]; }
      lgApply(tG);
    }
    { andromedaAt(LMCO, tG, MAG.r); const sh = mulM(M, [MAG.r[0] - MAG.r0[0], MAG.r[1] - MAG.r0[1], MAG.r[2] - MAG.r0[2]]); F.lgShift2 = sh; F.lmcGone = LMCO.tMerge ? smoothstep(LMCO.tMerge, LMCO.tMerge + 0.25, tG) : 0;
      for (const c of MAG.c) { c.c[0] = c.m0[0] + sh[0]; c.c[1] = c.m0[1] + sh[1]; c.c[2] = c.m0[2] + sh[2]; c.gone = F.lmcGone > 0.6; } }
    sunGalAt(Rr.K, F.tEff, sunGal);
    if (S.tOn !== null && tG >= S.tOn) {            // rencontre rapprochée : les étoiles des deux galaxies sont simulées une à une
      if (!S.dyn) { if (!G.m31dyn) G.m31dyn = Q.dyn31 + 70 > G.m31.N ? genDiskGalaxy(23, Q.dyn31 + 70, 24) : G.m31; S.dyn = dynInit(G.gal, Q.gal, G.m31dyn, S.orbit, S.tOn, sunGalAt(Rr.K, S.tOn, [0, 0, 0]), Rr.m31Rot, Q.dynN, Q.dyn31, G.m31.N - 70); Rr.setDyn(S.dyn); }
      { const tD = Math.min(tG, (S.orbit.tMerge || S.tOn + 6) + 3), t0p = performance.now(); let n = 0; S.dynT = tD;      // une fois les galaxies fusionnées et calmées, inutile de calculer plus loin
        do dynAdvance(S.dyn, S.orbit, tD, Math.abs(tD - S.dyn.t) > 0.06 ? Q.dynSteps * 3 : Q.dynSteps, DTAB); while (Math.abs(tD - S.dyn.t) > 0.06 && performance.now() - t0p < 14 && ++n < 60); }
      sunGal[0] = S.dyn.x[0]; sunGal[1] = S.dyn.x[1]; sunGal[2] = S.dyn.x[2]; F.dyn = S.dyn; F.mergeK = 1;
    } else { S.dyn = null; F.dyn = null; F.mergeK = 0; S.dynT = undefined; }

    const g = mulM(M, [-sunGal[0], -sunGal[1], -sunGal[2]]); F.gcRel[0] = g[0] * KPC; F.gcRel[1] = g[1] * KPC; F.gcRel[2] = g[2] * KPC;
    const R = Math.pow(10, S.logR), fb = bodyPosM(S.focus);
    let fo = fb; if (S.fa) { const k = ease(clamp((wall - S.fa.t0) / S.fa.dur, 0, 1)); fo = [lerp(S.fa.from[0], fb[0], k), lerp(S.fa.from[1], fb[1], k), lerp(S.fa.from[2], fb[2], k)]; if (k >= 1) S.fa = null; }
    if (S.focus === 'earth' && !S.center && S.logR < 7.25 && Rr.camPos) { const c = Rr.camPos, n = Math.hypot(c.x, c.y, c.z) || 1, re = BODY.earth.r * 1e3 * (1 - smoothstep(6.4, 7.2, S.logR)); fo = [fo[0] + c.x / n * re, fo[1] + c.y / n * re, fo[2] + c.z / n * re]; }
    S.curFo = fo;
    const wF = fadeOut(S.logR, 13.4, 14.4), wG = smoothstep(2, 50, R / (1000 * LY));
    for (let i = 0; i < 3; i++) F.tg[i] = fo[i] * wF + F.gcRel[i] * wG;
    F.selPos = S.sel && S.sel !== S.center ? S.sel.get() : null;      /* l'objet sélectionné et suivi porte le repère de R2 (updateFollow) au lieu de l'anneau 3D */ if (F.selPos && !isFinite(F.selPos[0])) F.selPos = null;
    const ck0 = S.ck; S.ck = clamp(S.ck + (S.center ? dt : -dt) / 0.9, 0, 1); if (S.center) S.cpos = S.center.get();
    if (S.ck > 0 && S.cpos) { const k = ease(S.ck); for (let i = 0; i < 3; i++) F.tg[i] = lerp(F.tg[i], S.cpos[i], k); }
    if (S.zoff && (microOn() || (S.focus !== 'sun' && S.logR < 14.4))) zoffReset();      /* revenu près d'un astre suivi ou dans l'infiniment petit : le zoom se recentre sur lui (en glissant) */
    if (S.zoff && !S.center) for (let i = 0; i < 3; i++) F.tg[i] += S.zoff[i];      /* R3 : décalage du zoom vers un point */
    /* nouveau centre alors que la vue est encore (même en partie) tirée vers l'ancien : glissement en 0,9 s au lieu d'un saut.
       Couvre le passage direct A → B, A → (fiche fermée) → B en moins de 0,9 s, et le retour en arrière (goBack). */
    if (S.center !== S.cWas) { if (S.center && S.lastTg && (S.cWas || ck0 > 0)) S.cbl = { from: S.lastTg, t0: wall }; S.cWas = S.center; }
    if (S.cbl) { const k = ease(clamp((wall - S.cbl.t0) / (reduced ? 0.001 : 0.9), 0, 1)); for (let i = 0; i < 3; i++) F.tg[i] = lerp(S.cbl.from[i], F.tg[i], k); if (k >= 1) S.cbl = null; }
    S.lastTg = [F.tg[0], F.tg[1], F.tg[2]];
    F.aFac = S.opts.comoving ? Math.pow(cs.a, smoothstep(22.6, 23.6, S.logR)) : 1;
    { const Rm = Math.max(R, 150); F.R = Rm; F.logR = Math.max(S.logR, Math.log10(150)); F.s = Rr.viewUnits / (Rm * F.aFac); F.lrT = S.logR; F.sT = Rr.viewUnits / R; } /* le décor astronomique se fige à 150 m du sol ; l'infiniment petit utilise l'échelle vraie (lrT, sT) */ F.az = S.az; F.el = S.el; F.frameMix = smoothstep(17.8, 19.9, S.logR);
    F.T1 = S.T1; F.T2 = S.T2; F.dmMix = S.dmMix; F.Dn = Math.min(cs.D / D_FID, 1.75); F.age = C.tBang !== null ? S.ty / 1e9 - C.tBang : 99;
    F.sunAlive = S.ty >= SS_BORN ? 1 : 0;      /* R7 : coupure nette à la naissance du système solaire, plus de fondu */ F.jd = JD_NOW + S.ty * 365.25; F.jdM = JD_NOW + (S.ty + (S.moonOff || 0)) * 365.25; F.jdS = JD_NOW + (S.ty + (S.sOff || 0)) * 365.25; F.sol = sol; updateMoons(); updateConst(); F.constOn = S.constOn; F.skyOn = S.skyOn !== false && !S.lite; updatePhotos(); updateNear(); updateEpoch(); updateOort(); F.days = (JD_NOW - JD_J2000) + (S.ty + (S.solOff || 0)) * 365.25; F.stepYears = Math.min(stepY, S.capS || stepY); F.beltYears = S.beltYears; F.wall = wall;
    if (surveyDirty) { surveyDirty = false; Rr.setSurvey(surveyLut(S.cosmo)); }
    Rr.update(F); Rr.lensUpdate(F); updateLabels(); updateFollow(); Rr.render(wall, 1.0);
    $('thumb').style.bottom = railF(S.logR) * 100 + '%'; drawTape();
    if (now - hudT > 110) { hudT = now; hud(); }
    tilesTick(dt * 1000);
    // résolution adaptative : on baisse la finesse si l'appareil peine, on la remonte s'il a de la marge
    frames++;
    if (frames > 40 && !window.__NOADAPT) { if (dt > 0.036) slow++; else slow = Math.max(0, slow - 1); if (dt < 0.019) fast++; else fast = 0;
      if (slow > 45 && dprScale > 0.5) { dprScale = Math.max(0.5, dprScale - 0.15); slow = 0; resize(); }
      else if (fast > 600 && dprScale < 1) { dprScale = Math.min(1, dprScale + 0.1); fast = 0; resize(); } }
    requestAnimationFrame(step);
  }
  setSpeed(S.speed); syncPlay(); syncSliders();
  /* R9 : conditions de départ du calcul de la fusion, dans le repère galactocentrique d'andromedaOrbit (kpc, km/s), exportées par
     pipeline/fusion/exporter_conditions.py. Mêmes formules que lgStart (position r0 = Mᵀ·c0, vitesse V + SUN_UVW) et lmcOrbit. */
  function fusionCI() { const V = DATA.LGV || {}, cen = G.lg.centers, dw = [];
    for (const k of Object.keys(V)) { const i = +k, c = cen[i]; if (!c || c.own || c.m0) continue; const q = c.c0, v0 = V[k];
      dw.push({ i, name: c.g.n, pos: [M[0][0] * q[0] + M[1][0] * q[1] + M[2][0] * q[2], M[0][1] * q[0] + M[1][1] * q[1] + M[2][1] * q[2], M[0][2] * q[0] + M[1][2] * q[1] + M[2][2] * q[2]], vel: [v0[0] + SUN_UVW[0], v0[1] + SUN_UVW[1], v0[2] + SUN_UVW[2]] }); }
    const sun = sunGalAt(Rr.K, 0, [0, 0, 0]);
    return { m31: { pos: DATA.M31.pos, vel: M31_MEAS[0][1], vel_name: M31_MEAS[0][0], spin: DATA.M31.spin, meas: M31_MEAS }, lmc: DATA.LMC, lmc_spin: (LG_SPIN.find(q => /Grand Nuage/.test(q.key)) || {}).L, m33_spin: (LG_SPIN.find(q => /Triangle/.test(q.key)) || {}).L,
      dwarfs: dw, sun: { pos: sun, vel: SUN_UVW }, M_GAL2ECL: M, note: 'Axes LG_SPIN dans le repère équatorial (voir 30_gen.js) ; le reste dans le repère galactocentrique d’andromedaOrbit.' }; }
  window.__U = { lgRadial, LGR, gcRelKpc0, selLG, selSurv, fusionCI, zoomAt, zoffReset, centerOn, bodyPosM, selStar2, selNear, TL, onLost, OO, selStar, LGO, SYS_END, T_DIV, cenOf, moonPosOf: k => [kPos[k * 3], kPos[k * 3 + 1], kPos[k * 3 + 2]], evGo, evStep, parseWhen, eclipseScan, PTR, tapeW, get EVL() { return EVL; }, goName, goBack, goHome, stepZoom, goThere, NAVH, findRun, get FIDX() { return FIDX; }, get moonPos() { return kPos; }, get MOONL() { return KO; }, get G() { return G; }, S, F, STOPS, pickAt, select, G, goStop, goTo, setTime, setSpeed, rebuild, openPanel, focusBody, Rr, Q, tier, frame: () => frames };
  if (!reduced) { S.logR = Math.log10(3.4 * AU); S.el = 0.42; }
  requestAnimationFrame(now => { last = now; step(now); requestAnimationFrame(() => { $('loader').classList.add('out'); setTimeout(() => $('loader').remove(), 1000); if (!reduced && !S.resumed) { S.anim = { t0: performance.now() / 1000 + 0.3, dur: 5.5, l0: S.logR, l1: STOPS[1].logR, a0: S.az, a1: S.az + 0.5, e0: S.el, e1: 0.6 }; } showRail(); }); });
})();
