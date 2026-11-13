/* Inclus par gaia.vert et gaia_agrege.vert (docs/gaia-rayons.md). Mêmes valeurs dans gaia.h (GaiaFiable), à garder identiques.
   1. Effacement dans le temps : seules les étoiles à orbite fiable (vitesse radiale mesurée, vitesse 3D connue à mieux que
      10 km/s, drapeau 2 de gaia.bin) suivent leur orbite loin d'aujourd'hui. Les autres sources ne sont montrées qu'autour
      du présent mesuré : leur lumière s'efface en exp(-(t / 3 Ma)²). Mesuré : sans vitesse radiale, l'erreur de place grandit
      d'environ 35 pc par million d'années (médiane), et dépasse l'erreur de distance d'aujourd'hui (80 à 180 pc entre 1 et
      4 kpc) en 2 à 5 millions d'années.
   2. Éclat rééquilibré vu de loin (drapeau 4, pipeline/natif/gaia_reequilibre.py) : HYPOTHÈSE, dite à l'écran. Gaia ne
      mesure pas la distance aussi loin dans toutes les directions ; vu de loin, cela dessine des rayons autour du Soleil.
      Chaque source reçoit un décalage d'éclat qui ramène sa case de ciel à la moyenne des cases voisines (15°). Il compte en
      proportion de l'écart caméra-Soleil rapporté à la distance de la source : rien vu du Soleil (le ciel reste celui mesuré),
      tout vu de loin. */
const float GF_TAU_ANS = 3.0e6;
const uint GF_POUSSIERE = 0x40000000u;       /* bit suivant : carte de poussière 3D liée (gaia.h, attachDust) */
const uint GF_MODE_RENDU = 0x80000000u;      /* bit haut de cellBase : vue « meilleur rendu » (Sim::bestLook) ; sinon 100 % mesuré */
float gfEffacement(float tGa) {
    float u = tGa * 1.0e9 / GF_TAU_ANS;
    return exp(-u * u);
}
/* 3. Flou angulaire vu de loin (vue « meilleur rendu » seulement) : chaque source est dessinée décalée en travers de la ligne
      de visée du Soleil, d'un angle tiré au hasard (fixe par source) d'écart type GF_FLOU_DEG. La distance de Gaia est connue à
      5 % près (médiane pondérée par la lumière) ; ce flou de 3° (5 %) donne à chaque source la même incertitude en travers
      qu'en profondeur, et efface les rayons fins (mesuré : 0,046 -> 0,016 dex). */
const float GF_FLOU_DEG = 3.0;
vec2 gfGauss2(uint k) {      /* deux nombres gaussiens fixes (hachage PCG, Jarzynski et Olano 2020 ; Box-Muller) */
    uvec3 v = uvec3(k, k * 747796405u + 2891336453u, k ^ 0x9E3779B9u);
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    vec2 u = (vec2(v.xy) + 0.5) * (1.0 / 4294967296.0);
    float r = sqrt(-2.0 * log(u.x));
    return r * vec2(cos(6.2831853 * u.y), sin(6.2831853 * u.y));
}
vec3 gfFlou(vec3 p, uint k, float poids) {
    float d = length(p);
    if (poids <= 0.0 || d < 1.0) return p;
    vec3 n = p / d;
    vec3 t1 = normalize(cross(n, abs(n.z) < 0.9 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0)));
    vec3 t2 = cross(n, t1);
    vec2 g = gfGauss2(k) * radians(GF_FLOU_DEG) * poids;
    return p + d * (g.x * t1 + g.y * t2);
}
float gfPoidsLoin(vec3 cam, vec3 star) { return clamp(length(cam) / max(length(star), 1.0), 0.0, 1.0); }
