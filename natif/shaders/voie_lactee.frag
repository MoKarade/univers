#version 450
/* Lueur de la Voie lactée (voie_lactee.h) : un rayon par pixel à travers la grille galactique (kpc).
   À chaque pas : lumière qui manque aux étoiles dessinées (grille) + bulbe + barre (calculés ici, tournés de l'angle du
   moment), atténuée par la poussière déjà traversée (A_V par pc ; transmission 10^(-0,4 A_V)). */
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
layout(std140, set = 0, binding = 0) uniform U {
    vec4 camGrid, right, up, fwd, color, grid, sunZ, bulge, bar, bar2, frame;
} u;
layout(set = 0, binding = 1) uniform sampler3D big;     /* r : lumière manquante (L_sol/pc³) ; g : poussière (A_V/pc) */
layout(set = 0, binding = 2) uniform sampler3D local;   /* poussière mesurée autour du Soleil (A_V/pc), cases de sunZ.y pc */
const int STEPS = 192;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + u.frame.z * 0.618) * 43758.5453); }

/* bulbe en cacahuète (exponentielle ellipsoïdale) et barre longue, dans le repère de la barre */
float barLight(vec3 p) {
    vec2 q = vec2(dot(p.xy, u.bar2.yz), dot(p.xy, vec2(-u.bar2.z, u.bar2.y)));
    float s = length(vec3(q.x / u.bulge.y, q.y / u.bulge.z, p.z / u.bulge.w));
    float j = u.bulge.x * exp(-s);
    /* barre longue : uniforme le long du grand axe jusqu'à la demi-longueur (bord adouci sur 0,25 kpc), largeur 0,5 kpc
       [supposée], hauteurs mesurées (mince et très mince) */
    float along = 1.0 / (1.0 + exp((abs(q.x) - u.bar.y) / 0.25));
    float across = exp(-abs(q.y) / 0.5);
    float vert = (1.0 - u.bar2.x) * exp(-abs(p.z) / u.bar.z) / (2.0 * u.bar.z * 1e3) + u.bar2.x * exp(-abs(p.z) / u.bar.w) / (2.0 * u.bar.w * 1e3);
    j += u.bar.x * along * across * vert / (2.0 * u.bar.y * 1e3 * 2.0 * 0.5 * 1e3);
    return j;
}

void main() {
    vec2 ndc = uv * 2.0 - 1.0;
    vec3 dir = u.fwd.xyz + ndc.x * u.right.xyz - ndc.y * u.up.xyz;
    float solid = 1.0 / pow(dot(dir, dir), 1.5);      /* angle solide du pixel, rapporté à celui du centre */
    dir = normalize(dir);
    vec3 lo = vec3(-u.grid.x, -u.grid.x, -u.grid.y), hi = -lo;
    vec3 inv = 1.0 / dir;
    vec3 t0 = (lo - u.camGrid.xyz) * inv, t1 = (hi - u.camGrid.xyz) * inv;
    vec3 tmin = min(t0, t1), tmax = max(t0, t1);
    float a = max(max(max(tmin.x, tmin.y), tmin.z), 0.0), b = min(min(tmax.x, tmax.y), tmax.z);
    if (b <= a) { o = vec4(0.0); return; }
    float dt = (b - a) / float(STEPS);
    float t = a + dt * hash(gl_FragCoord.xy);
    vec3 sun = vec3(u.grid.z, u.grid.w, u.sunZ.x);
    vec3 localHalf = vec3(u.sunZ.z, u.sunZ.w, u.bar2.w) * u.sunZ.y * 0.5e-3;
    float light = 0.0, av = 0.0;
    float dpc = dt * 1e3;
    for (int i = 0; i < STEPS; ++i, t += dt) {
        vec3 p = u.camGrid.xyz + dir * t;
        vec2 cell = texture(big, (p - lo) / (hi - lo)).rg;
        vec3 l = (p - sun) / localHalf * 0.5 + 0.5;      /* dans la carte mesurée : son détail remplace la moyenne de la case */
        float dust = all(greaterThanEqual(l, vec3(0.0))) && all(lessThanEqual(l, vec3(1.0))) && length(p - sun) < 1.24 ? texture(local, l).r : cell.g;      /* carte mesurée jusqu'à 1,24 kpc */
        /* bord de la grille (carré de ±16 kpc) : la lueur s'éteint en cercle entre 13 et 16 kpc du centre au lieu de
           s'arrêter net sur un carré visible de loin [supposé ; bord du disque d'étoiles mesuré vers 13,9 kpc,
           Minniti et al. 2011, ApJ 733, L43, à vérifier] */
        float edge = 1.0 - smoothstep(0.8125 * u.grid.x, u.grid.x, length(p.xy));
        float j = cell.r * edge + barLight(p);
        light += j * pow(10.0, -0.4 * (av + 0.5 * dust * dpc)) * dpc;
        av += dust * dpc;
    }
    o = vec4(u.color.rgb * (u.color.w * solid * light), 1.0);
}
