#version 450
#extension GL_GOOGLE_include_directive : require
#include "orbite_galactique.glsl"
#include "gaia_acc.glsl"
/* Lumière additionnée des sources Gaia à distance mal mesurée (gaia.h, gaia_agrege.bin). Deux usages, choisis par
   pc.camLo.w :
   0 : cases 3D (morceau de ciel × tranche de parallaxe), placées à leur distance, étalées sur leur taille à l'écran ;
   1 : ciel seul (distance inconnue), dessiné comme vu du Soleil : direction seulement, flux mesuré tel quel.
   Les cases bougent comme les étoiles (gaia.vert) : centre emporté à la vitesse moyenne mesurée de ses sources, ligne
   droite puis orbite (exacte si calculée, sinon épicycles). Les points d'une case restent groupés autour du centre. */
struct Cell { vec4 pm; vec4 rest; vec4 vel; };      /* x, y, z (al), magnitude ; rayon, erreur, couleur (bits), nombre (bits) ; vitesse moyenne (km/s), dispersion */
struct Etat { vec4 p; vec4 v; };
layout(std430, set = 0, binding = 3) readonly buffer Orb { Etat orb[]; };
layout(std430, set = 0, binding = 0) readonly buffer Cells { Cell cell[]; };
layout(std430, set = 0, binding = 2) readonly buffer Col { vec4 colorOf[]; };      /* binding 1 : vitesses des étoiles, inutile ici */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; uint sun; float frac; float exact; uint cellBase; } pc;   /* camHi.w : tan(champ / 2) ; par.w : temps (Ga) */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
const int SPREAD = 8;          /* points par case (gaia.h dessine SPREAD instances) */
const float OVERLAP = 2.5;     /* tache plus large que la case : les cases voisines se recouvrent, pas de trous entre elles */
/* trois nombres pseudo-aléatoires fixes dans [0, 1[ (hachage entier PCG, Jarzynski et Olano 2020) */
vec3 hash3(uvec2 k) {
    uvec3 v = uvec3(k.x, k.y, k.x ^ (k.y * 747796405u));
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    return vec3(v) * (1.0 / 4294967296.0);
}
void main() {
    Cell c = cell[gl_VertexIndex];
    float pxPerRad = pc.par.y / (2.0 * pc.camHi.w);
    vec3 p;
    float flux, ext;
    if (pc.camLo.w == 0.0) {
        /* La case n'a pas de positions d'étoiles, seulement une somme de lumière : sa lumière est répartie en SPREAD points
           tirés uniformément dans le volume de la case (morceau de ciel × tranche d'un dixième de décade en parallaxe).
           Le tirage est fixe (même case, même tirage) et sans alignement : pas de grille ni de coquilles. */
        vec3 h = hash3(uvec2(uint(gl_VertexIndex), uint(gl_InstanceIndex)));
        float s = pow(10.0, (h.x - 0.5) * 0.1);
        vec3 n = normalize(c.pm.xyz);
        vec3 t1 = normalize(cross(n, abs(n.z) < 0.9 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0)));
        vec3 t2 = cross(n, t1);
        float d0 = length(c.pm.xyz) * s;
        vec3 q = (n + (2.0 * h.y - 1.0) * c.rest.x / length(c.pm.xyz) * t1 + (2.0 * h.z - 1.0) * c.rest.x / length(c.pm.xyz) * t2) * d0;
        vec3 dep = vec3(0.0), v = c.vel.xyz;
        if (pc.par.w == 0.0) dep = v * pc.par.z;
        else if (pc.exact > 0.5) {
            float u = pc.par.w * 1.0e9 / OG_RACCORD_ANS, w = 1.0 - exp(-u * u);
            float tEtat = pc.par.w - pc.frac * 1.0e-3, hh = pc.frac * 1.0e-3 * OP_K;
            Etat a = orb[pc.cellBase + uint(gl_VertexIndex)], so = orb[pc.sun];
            vec3 xa = a.p.xyz + hh * a.v.xyz + 0.5 * hh * hh * accGal(a.p.xyz, tEtat);
            vec3 xs = so.p.xyz + hh * so.v.xyz + 0.5 * hh * hh * accGal(so.p.xyz, tEtat);
            dep = mix(v * pc.par.z, OG_M * (xa - xs) * OG_KPC_LY - c.pm.xyz, w);
        } else dep = ogDeplacement(c.pm.xyz, v, pc.par.z, pc.par.w);
        p = ((q - pc.camHi.xyz) + dep) - pc.camLo.xyz;
        float d = max(length(p), 1e-12);
        flux = pc.par.x * pow(10.0, -0.4 * (c.pm.w + 2.5 * log(float(SPREAD)) / log(10.0) + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0));
        /* tache : assez large pour que les points d'une case se recouvrent (côté de la case, ou épaisseur partagée entre les points) */
        /* l'épaisseur ne compte que vue de côté : projetée sur l'écran (sinus de l'angle entre le rayon de vue et la direction du Soleil) */
        float r = max(OVERLAP * c.rest.x * s, 0.23 * d0 / float(SPREAD) * length(cross(n, p / d)));
        ext = r / d * pxPerRad;
    } else {
        p = c.pm.xyz;                          /* direction seule */
        flux = pc.par.x * pow(10.0, -0.4 * c.pm.w);
        ext = 2.0 * OVERLAP * c.rest.x * pxPerRad;      /* vu du Soleil, pixels du ciel jointifs : recouvrement plus large */
    }
    float size = clamp(max(1.5 * pc.par.y / 1080.0, ext), 1.0, 512.0);
    vCol = colorOf[floatBitsToUint(c.rest.z) & 255u].rgb * flux / (size * size);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
