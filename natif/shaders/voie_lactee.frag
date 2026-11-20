#version 450
/* Lueur de la Voie lactée (voie_lactee.h) : un rayon par pixel à travers la grille galactique (kpc).
   À chaque pas : lumière qui manque aux étoiles dessinées (grille) + bulbe + barre (calculés ici, tournés de l'angle du
   moment), atténuée par la poussière déjà traversée (A_V par pc ; transmission 10^(-0,4 A_V)). */
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
layout(std140, set = 0, binding = 0) uniform U {
    vec4 camGrid, right, up, fwd, color, grid, sunZ, bulge, bar, bar2, frame;
    vec4 colorBulge, colorYoung, colorHii;      /* couleurs : bulbe et barre (vieux), bras (jeunes), régions HII (Hα) */
} u;
layout(set = 0, binding = 1) uniform sampler3D big;     /* r : lumière manquante, vieilles étoiles (L_sol/pc³) ; g : poussière (A_V/pc) ;
                                                           b : jeunes étoiles des bras ; a : régions HII (v2 seulement) */
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
    if (u.frame.w > 0.5) {      /* poussière seule (carte mesurée locale) : transmission, multipliée à l'image (voie_lactee.h) */
        vec3 sunL = vec3(u.grid.z, u.grid.w, u.sunZ.x);
        vec3 half_ = vec3(u.sunZ.z, u.sunZ.w, u.bar2.w) * u.sunZ.y * 0.5e-3;
        vec3 l0 = sunL - half_, l1 = sunL + half_;
        vec3 s0 = (l0 - u.camGrid.xyz) * inv, s1 = (l1 - u.camGrid.xyz) * inv;
        vec3 smin = min(s0, s1), smax = max(s0, s1);
        float la = max(max(max(smin.x, smin.y), smin.z), 0.0), lb = min(min(smax.x, smax.y), smax.z);
        if (lb <= la) { o = vec4(1.0); return; }
        float ds = (lb - la) / float(STEPS);
        float s = la + ds * hash(gl_FragCoord.xy);
        float avd = 0.0;
        for (int i = 0; i < STEPS; ++i, s += ds) {
            vec3 p = u.camGrid.xyz + dir * s;
            vec3 l = (p - sunL) / half_ * 0.5 + 0.5;
            if (length(p - sunL) < 1.24) avd += texture(local, l).r * ds * 1e3;      /* A_V par pc × pc */
        }
        float t = mix(1.0, pow(10.0, -0.4 * avd), u.color.w);
        o = vec4(t, t, t, 1.0);
        return;
    }
    if (b <= a) { o = vec4(0.0); return; }
    float dt = (b - a) / float(STEPS);
    float t = a + dt * hash(gl_FragCoord.xy);
    vec3 sun = vec3(u.grid.z, u.grid.w, u.sunZ.x);
    vec3 localHalf = vec3(u.sunZ.z, u.sunZ.w, u.bar2.w) * u.sunZ.y * 0.5e-3;
    vec3 light = vec3(0.0);
    float av = 0.0;
    float dpc = dt * 1e3;
    for (int i = 0; i < STEPS; ++i, t += dt) {
        vec3 p = u.camGrid.xyz + dir * t;
        vec4 cell = texture(big, (p - lo) / (hi - lo));
        if (u.colorBulge.w < 3.0) cell.ba = vec2(0.0);      /* grille v1 : une seule lumière */
        vec3 l = (p - sun) / localHalf * 0.5 + 0.5;      /* dans la carte mesurée : son détail remplace la moyenne de la case */
        bool inLocal = all(greaterThanEqual(l, vec3(0.0))) && all(lessThanEqual(l, vec3(1.0))) && length(p - sun) < 1.24;      /* carte mesurée jusqu'à 1,24 kpc */
        float dust = inLocal ? texture(local, l).r : cell.g;
        /* bord de la grille (carré de ±16 kpc) : la lueur s'éteint en cercle entre 13 et 16 kpc du centre au lieu de
           s'arrêter net sur un carré visible de loin [supposé ; bord du disque d'étoiles mesuré vers 13,9 kpc,
           Minniti et al. 2011, ApJ 733, L43, à vérifier] */
        float edge = 1.0 - smoothstep(0.8125 * u.grid.x, u.grid.x, length(p.xy));
        vec3 j = (u.color.rgb * cell.r + u.colorYoung.rgb * cell.b + u.colorHii.rgb * cell.a) * edge + u.colorBulge.rgb * barLight(p);
        light += j * pow(10.0, -0.4 * (av + 0.5 * dust * dpc)) * dpc;
        av += dust * dpc;
    }
    /* Compression de la lueur sur sa luminance, qui garde la teinte : sans elle, le bulbe et la barre passent au blanc
       (compression couleur par couleur de l'écran) et le disque devient une tache uniforme. ln(1 + Y) : l'étendue du centre
       aux bords reste lisible, comme une photo étirée [choix d'affichage]. */
    vec3 c = light * (u.color.w * solid);
    float Y = dot(c, vec3(0.2126, 0.7152, 0.0722));
    o = vec4(Y > 0.0 ? c * (log(1.0 + Y) / Y) : vec3(0.0), 1.0);
}
