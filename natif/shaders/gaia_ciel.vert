#version 450
/* Sources Gaia DR3 sans distance mesurée (gaia_ciel.h) : direction mesurée, dessinée à l'infini (w = 0), éclat d'après
   la magnitude G mesurée depuis la Terre ; même loi d'éclat et même tache que les étoiles Gaia (gaia.vert). */
layout(std430, set = 0, binding = 0) readonly buffer Stars { uint s[]; };      /* 6 mots par étoile (gaia_tuiles.py) */
layout(std430, set = 0, binding = 1) readonly buffer Col { vec4 colorOf[]; };  /* 256 pas de BP-RP -> couleur (gaia.h) */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 par; } pc;               /* par : exposition, hauteur en pixels */
layout(location = 0) out vec3 vCol;
void main() {
    uint b = uint(gl_VertexIndex) * 6u;
    vec3 dir = vec3(uintBitsToFloat(s[b]), uintBitsToFloat(s[b + 1u]), uintBitsToFloat(s[b + 2u]));
    uint gc = s[b + 3u];
    float g = float(gc & 65535u) * 0.001;
    int c = int(gc) >> 16;      /* BP-RP en millièmes ; -32768 = non mesuré */
    uint pas = c == -32768 ? 255u : uint(clamp(int(floor((float(c) * 0.001 + 0.6) / 0.03)), 0, 254));
    float flux = pc.par.x * pow(10.0, -0.4 * g);
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = colorOf[pas].rgb * min(flux, 3.0e4) / (size * size);
    gl_Position = pc.viewProj * vec4(dir, 0.0);
    gl_PointSize = size;
}
