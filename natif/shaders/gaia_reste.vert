#version 450
/* Lumière cumulée des étoiles Gaia trop faibles pour être dessinées une à une (gaia.h, addRest) : un point par feuille,
   au centre de lumière, étalé sur la taille de la feuille à l'écran. Même loi d'éclat que les étoiles (gaia.vert). */
layout(location = 0) in vec4 inPos;     /* position relative à la caméra (al) ; w : magnitude absolue de la lumière sautée */
layout(location = 1) in vec4 inCol;     /* couleur ; w : taille de la feuille à l'écran (pixels) */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
void main() {
    float d = max(length(inPos.xyz), 1e-12);
    float m = inPos.w + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0;
    float flux = pc.par.x * pow(10.0, -0.4 * m);
    float size = max(clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0, inCol.w);
    vCol = inCol.rgb * flux / (size * size);      /* même énergie quelle que soit la taille */
    gl_Position = pc.viewProj * vec4(inPos.xyz, 1.0);
    gl_PointSize = size;
}
