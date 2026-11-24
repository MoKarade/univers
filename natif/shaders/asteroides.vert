#version 450
/* Astéroïdes : chacun avance sur son orbite mesurée (éléments du JPL), calculée ici par l'équation de Kepler.
   Unité : UA. Position = P (cos E - e) + Q sin E, avec E l'anomalie excentrique. Éclat : sa vraie lumière (audit A6),
   magnitude apparente m = H + 5 log10(r Δ) (H mesurée par le JPL ; r : distance au Soleil, Δ : à la caméra, en UA),
   sans la phase [approximation assumée], sous la même pose et la même règle de taille que les étoiles (etoiles.vert). */
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
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;   /* par : pose des étoiles × fondu en temps, hauteur en pixels, jours depuis l'époque */
layout(location = 0) out vec3 vCol;
void main() {
    float M = mod(inM0 + inN * pc.par.z, 6.2831853);
    float E = M + inE * sin(M) * (1.0 + inE * cos(M));
    for (int k = 0; k < 8; k++) E -= (E - inE * sin(E) - M) / (1.0 - inE * cos(E));
    vec3 pos = vec3(inPx, inPy, inPz) * (cos(E) - inE) + vec3(inQx, inQy, inQz) * sin(E);
    vec3 p = (pos - pc.camHi.xyz) - pc.camLo.xyz;
    float r = max(length(pos), 1e-6), delta = max(length(p), 1e-9);
    float m = inH + 5.0 * log(r * delta) / log(10.0);
    float flux = pc.par.x * pow(10.0, -0.4 * m);
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = vec3(0.61, 0.53, 0.43) / 0.61 * min(flux, 3.0e4) / (size * size);   /* teinte de la page, en lumière linéaire ; même énergie quelle que soit la taille */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
