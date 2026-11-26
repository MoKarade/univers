#version 450
/* Astéroïdes : chacun avance sur son orbite mesurée (éléments du JPL), calculée ici par l'équation de Kepler.
   Unité : UA. Position = P (cos E - e) + Q sin E, avec E l'anomalie excentrique. Chaque astéroïde est un point de
   taille d'affichage fixée par sa magnitude absolue H (mesurée) : en vraie lumière il serait invisible. */
layout(location = 0) in float inPx;
layout(location = 1) in float inPy;
layout(location = 2) in float inPz;
layout(location = 3) in float inQx;
layout(location = 4) in float inQy;
layout(location = 5) in float inQz;
layout(location = 6) in float inE;
layout(location = 7) in float inM0;
layout(location = 8) in float inN;
layout(location = 9) in float inH;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;   /* par : éclat, hauteur en pixels, jours depuis l'époque */
layout(location = 0) out vec3 vCol;
void main() {
    float M = mod(inM0 + inN * pc.par.z, 6.2831853);
    float E = M + inE * sin(M) * (1.0 + inE * cos(M));
    for (int k = 0; k < 8; k++) E -= (E - inE * sin(E) - M) / max(1.0 - inE * cos(E), 1e-4);
    vec3 pos = vec3(inPx, inPy, inPz) * (cos(E) - inE) + vec3(inQx, inQy, inQz) * sin(E);
    vec3 p = (pos - pc.camHi.xyz) - pc.camLo.xyz;
    float look = clamp(2.1 - (inH - 11.0) * 0.28, 0.75, 2.1);      /* même règle de taille que la page */
    float size = (1.0 + 0.8 * look) * pc.par.y / 1080.0;
    vCol = vec3(0.61, 0.53, 0.43) * pc.par.x * look / (size * size);   /* teinte de la page (0,80 0,75 0,68 à l'écran), en lumière linéaire */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
