#version 450
/* Étoiles : une colonne du fichier par attribut (x, y, z en années-lumière, magnitude absolue, vitesse en km/s),
   couleur calculée au chargement. Mouvement en ligne droite à la vitesse mesurée. Position relative à la caméra,
   soustraite en deux temps (partie principale, puis reste) pour garder la précision loin du Soleil.
   Éclat apparent par la loi en 1/d². */
layout(location = 0) in float inX;
layout(location = 1) in float inY;
layout(location = 2) in float inZ;
layout(location = 3) in float inMag;
layout(location = 4) in vec4 inCol;
layout(location = 5) in float inVx;
layout(location = 6) in float inVy;
layout(location = 7) in float inVz;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;   /* par : exposition, hauteur en pixels, temps, flux fixe (> 0 : fusion) */
layout(location = 0) out vec3 vCol;
const float K_EXP = 1.328771238;      /* 0,4 / log10(2) */
const float LY_PER_PC_SQ = 10.637798; /* 3,261563777² */
void main() {
    vec3 p = ((vec3(inX, inY, inZ) - pc.camHi.xyz) + vec3(inVx, inVy, inVz) * pc.par.z) - pc.camLo.xyz;
    float flux = pc.par.w > 0.0
        ? pc.par.w
        : pc.par.x * exp2(-K_EXP * (inMag - 5.0)) * (LY_PER_PC_SQ / max(dot(p, p), 1e-24));
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = inCol.rgb * min(flux, 3.0e4) / (size * size);                 /* même énergie quelle que soit la taille du point */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
