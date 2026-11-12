#version 450
#extension GL_GOOGLE_include_directive : require
#include "orbite_galactique.glsl"
/* Étoiles Gaia DR3 (gaia.h) : lues directement dans des tampons de stockage. Même éclat et même tache que les étoiles
   du catalogue principal (etoiles.vert) : magnitude absolue G mesurée, loi en 1/d², position relative à la caméra
   soustraite en deux temps. Vitesse lue seulement si le temps a bougé depuis les mesures (J2016,0) ; par.w : milliards d'années depuis ces mesures. */
layout(std430, set = 0, binding = 0) readonly buffer Stars { uvec4 star[]; };          /* x, y, z (al), puis magnitude (demi-flottant) | couleur << 16 | drapeaux << 24 */
layout(std430, set = 0, binding = 1) readonly buffer Vel { uvec2 vel[]; };             /* vx, vy, vz en pas de 0,05 km/s (entiers 16 bits) */
layout(std430, set = 0, binding = 2) readonly buffer Col { vec4 colorOf[]; };          /* 256 pas de BP-RP -> couleur du corps noir */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;   /* par : exposition, hauteur en pixels, temps en al par (km/s), temps en Ga */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
void main() {
    uvec4 r = star[gl_VertexIndex];
    vec3 pos = uintBitsToFloat(r.xyz), move = vec3(0.0);
    if (pc.par.z != 0.0) {
        uvec2 q = vel[gl_VertexIndex];
        vec3 v = vec3(float(int(q.x << 16) >> 16), float(int(q.x) >> 16), float(int(q.y << 16) >> 16)) * 0.05;
        /* ligne droite mesurée, raccordée sans seuil à l'orbite calculée autour de la Galaxie (orbite_galactique.glsl) ;
           sans vitesse radiale mesurée (drapeau), elle compte pour nulle : l'étoile ne s'éloigne ni ne s'approche du Soleil
           au départ [supposé, dit à l'écran] */
        move = pc.par.w == 0.0 ? v * pc.par.z : ogDeplacement(pos, v, pc.par.z, pc.par.w);
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
