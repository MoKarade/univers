#version 450
/* Étoiles : une colonne du fichier par attribut (x, y, z en années-lumière, magnitude absolue), couleur calculée
   au chargement. Position relative à la caméra ; éclat apparent par la loi en 1/d². */
layout(location = 0) in float inX;
layout(location = 1) in float inY;
layout(location = 2) in float inZ;
layout(location = 3) in float inMag;
layout(location = 4) in vec4 inCol;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;   /* par.x : exposition ; par.y : hauteur en pixels */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
void main() {
    vec3 p = vec3(inX, inY, inZ) - pc.cam.xyz;
    float d = max(length(p), 1e-7);
    float m = inMag + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0;      /* magnitude apparente vue de la caméra */
    float flux = pc.par.x * pow(10.0, -0.4 * m);
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = inCol.rgb * flux / (size * size);                             /* même énergie quelle que soit la taille du point */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
