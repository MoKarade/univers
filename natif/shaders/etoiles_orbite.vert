#version 450
/* Étoiles sur leur orbite EXACTE autour du centre de la Galaxie (orbites_gpu.h, orbites_pas.comp).
   Mêmes colonnes que etoiles.vert (position et vitesse mesurées, magnitude, couleur), plus deux états calculés sur la
   carte : celui du pas d'avant et celui du pas d'après la date montrée (1 million d'années entre les deux). Entre les
   deux, courbe de Hermite (positions et vitesses aux deux bouts). Raccord sans seuil avec la ligne droite mesurée, exacte
   près d'aujourd'hui. Le monde reste centré sur le Soleil : on retranche son propre état (l'étoile de rang camLo.w).
   par : exposition, hauteur en pixels, temps de la ligne droite (al par km/s), part du pas écoulée (0 à 1) ;
   camHi.w : poids de l'orbite dans le raccord (0 : ligne droite seule). */
layout(location = 0) in float inX;
layout(location = 1) in float inY;
layout(location = 2) in float inZ;
layout(location = 3) in float inMag;
layout(location = 4) in vec4 inCol;
layout(location = 5) in float inVx;
layout(location = 6) in float inVy;
layout(location = 7) in float inVz;
struct Etat { vec4 p; vec4 v; };
layout(std430, set = 0, binding = 0) readonly buffer Avant { Etat e[]; } avant;
layout(std430, set = 0, binding = 1) readonly buffer Apres { Etat e[]; } apres;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
const float KPC_LY = 3261.5637769;
const float PAS_KPC_PAR_KMS = 0.0010227121650456;      /* chemin (kpc) à 1 km/s pendant un pas de 1 million d'années */
/* Repère galactocentrique -> écliptique (colonnes de la matrice M_GAL2ECL de la page), comme orbite_galactique.glsl. */
const mat3 M = mat3(-0.0548756577, -0.993821367, -0.0964766946,
                    0.4941094372, -0.1109908412, 0.8622858559,
                    -0.8676661376, -0.0003515418, 0.4971472117);

vec3 hermite(Etat a, Etat b, float f) {
    float f2 = f * f, f3 = f2 * f;
    return (2.0 * f3 - 3.0 * f2 + 1.0) * a.p.xyz + (f3 - 2.0 * f2 + f) * PAS_KPC_PAR_KMS * a.v.xyz
         + (-2.0 * f3 + 3.0 * f2) * b.p.xyz + (f3 - f2) * PAS_KPC_PAR_KMS * b.v.xyz;
}

void main() {
    vec3 pos = vec3(inX, inY, inZ), vel = vec3(inVx, inVy, inVz);
    vec3 dep = vel * pc.par.z;
    if (pc.camHi.w > 0.0) {
        int soleil = int(pc.camLo.w);
        vec3 rel = hermite(avant.e[gl_VertexIndex], apres.e[gl_VertexIndex], pc.par.w) - hermite(avant.e[soleil], apres.e[soleil], pc.par.w);
        dep = mix(dep, M * rel * KPC_LY - pos, pc.camHi.w);
    }
    vec3 p = ((pos - pc.camHi.xyz) + dep) - pc.camLo.xyz;
    float d = max(length(p), 1e-12);
    float m = inMag + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0;
    float flux = pc.par.x * pow(10.0, -0.4 * m);
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = inCol.rgb * min(flux, 3.0e4) / (size * size);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
