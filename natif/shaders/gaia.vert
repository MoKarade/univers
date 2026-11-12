#version 450
#extension GL_GOOGLE_include_directive : require
#include "orbite_galactique.glsl"
/* Étoiles Gaia DR3 (gaia.h) : lues directement dans des tampons de stockage. Même éclat et même tache que les étoiles
   du catalogue principal (etoiles.vert) : magnitude absolue G mesurée, loi en 1/d², position relative à la caméra
   soustraite en deux temps. Vitesse lue seulement si le temps a bougé depuis les mesures (J2016,0) ; par.w : milliards d'années depuis ces mesures. */
layout(std430, set = 0, binding = 0) readonly buffer Stars { uvec4 star[]; };          /* x, y, z (al), puis magnitude (demi-flottant) | couleur << 16 | drapeaux << 24 */
layout(std430, set = 0, binding = 1) readonly buffer Vel { uvec2 vel[]; };             /* vx, vy, vz en pas de 0,05 km/s (entiers 16 bits) */
layout(std430, set = 0, binding = 2) readonly buffer Col { vec4 colorOf[]; };          /* 256 pas de BP-RP -> couleur du corps noir */
struct Etat { vec4 p; vec4 v; };
layout(std430, set = 0, binding = 3) readonly buffer Orb { Etat orb[]; };        /* orbites exactes (gaia_orbites.h, orbites_pas.comp), le Soleil en dernier */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; uint sun; float frac; float exact; float pad; } pc;   /* par : exposition, hauteur en pixels, temps en al par (km/s), temps en Ga */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
/* Accélération du potentiel de la Galaxie (bulbe, disque, halo, barre tournante) : COPIE de acc() de orbites_pas.comp
   (fil natif), à garder identique. Unités : kpc, km/s, milliards d'années. */
const float OP_G = 4.30091e-6, OP_MB = 0.5e10, OP_AB = 0.5, OP_MD = 6.8e10, OP_AD = 3.0, OP_BD = 0.28, OP_RS = 16.0;
const float OP_GMH = 2410361.25417129, OP_K = 1.0227121650456, OP_RB = 5.0, OP_ABAR = 777.79646, OP_BAR0 = 2.65290046, OP_BARW = 39.8857744;
vec3 accGal(vec3 x, float t) {
    float R2 = x.x * x.x + x.y * x.y, r = sqrt(R2 + x.z * x.z) + 1e-12, xs = r / OP_RS;
    float ar = -OP_G * OP_MB / ((r + OP_AB) * (r + OP_AB)) - OP_GMH * (log(1.0 + xs) - xs / (1.0 + xs)) / (r * r);
    float B = sqrt(x.z * x.z + OP_BD * OP_BD), D2 = R2 + (OP_AD + B) * (OP_AD + B), D3 = D2 * sqrt(D2), gm = OP_G * OP_MD;
    vec3 a = vec3(ar * x.x / r - gm * x.x / D3, ar * x.y / r - gm * x.y / D3, ar * x.z / r - gm * x.z * (OP_AD + B) / (B * D3));
    if (R2 > 1e-8) {
        float R = sqrt(R2), c = x.x / R, s = x.y / R, psi = atan(x.y, x.x) - (OP_BAR0 - OP_BARW * t);
        float c2 = cos(2.0 * psi), s2 = sin(2.0 * psi), q = R / OP_RB;
        float U = R < OP_RB ? q * q * q - 2.0 : -1.0 / (q * q * q);
        float dU = R < OP_RB ? 3.0 * q * q / OP_RB : 3.0 / (q * q * q * q * OP_RB);
        float aR = -OP_ABAR * c2 * dU, aP = 2.0 * OP_ABAR * s2 * U / R;
        a.x += aR * c - aP * s;
        a.y += aR * s + aP * c;
    }
    return a;
}
void main() {
    uvec4 r = star[gl_VertexIndex];
    vec3 pos = uintBitsToFloat(r.xyz), move = vec3(0.0);
    if (pc.par.z != 0.0) {
        uvec2 q = vel[gl_VertexIndex];
        vec3 v = vec3(float(int(q.x << 16) >> 16), float(int(q.x) >> 16), float(int(q.y << 16) >> 16)) * 0.05;
        /* ligne droite mesurée, raccordée sans seuil à l'orbite calculée autour de la Galaxie (orbite_galactique.glsl) ;
           sans vitesse radiale mesurée (drapeau), elle compte pour nulle : l'étoile ne s'éloigne ni ne s'approche du Soleil
           au départ [supposé, dit à l'écran] */
        if (pc.par.w == 0.0) move = v * pc.par.z;
        else if (pc.exact > 0.5) {
            /* orbite exacte : état calculé au dernier pas d'un million d'années, prolongé au second ordre jusqu'à la date ;
               raccord sans seuil avec la ligne droite mesurée, comme etoiles_orbite.vert */
            float u = pc.par.w * 1.0e9 / OG_RACCORD_ANS, w = 1.0 - exp(-u * u);
            float tEtat = pc.par.w - pc.frac * 1.0e-3, h = pc.frac * 1.0e-3 * OP_K;
            Etat a = orb[gl_VertexIndex], s = orb[pc.sun];
            vec3 xa = a.p.xyz + h * a.v.xyz + 0.5 * h * h * accGal(a.p.xyz, tEtat);
            vec3 xs = s.p.xyz + h * s.v.xyz + 0.5 * h * h * accGal(s.p.xyz, tEtat);
            move = mix(v * pc.par.z, OG_M * (xa - xs) * OG_KPC_LY - pos, w);
        } else move = ogDeplacement(pos, v, pc.par.z, pc.par.w);      /* épicycles, le temps que le calcul exact rattrape */
    }
    vec3 p = ((pos - pc.camHi.xyz) + move) - pc.camLo.xyz;
    float d = max(length(p), 1e-12);
    float m = unpackHalf2x16(r.w).x + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0;
    float flux = pc.par.x * pow(10.0, -0.4 * m);
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = colorOf[(r.w >> 16) & 255u].rgb * min(flux, 3.0e4) / (size * size);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
