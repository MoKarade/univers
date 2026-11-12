#version 450
/* Sources d'un catalogue de la bande (ciel_bandes.h) : un cercle par source, à sa direction mesurée (équatorial ICRS),
   vue depuis le Soleil comme la carte. Taille selon la grandeur mesurée (flux), rapportée à la médiane du catalogue :
   +3 pixels par facteur 10 (ou taille fixe quand la grandeur n'est pas un flux). En champ large, seules les plus
   brillantes sont dessinées (environ 1 000 par catalogue à l'écran, ciel_bandes.h) ; la légende dit le seuil. Couleur selon la nature donnée par l'équipe du catalogue. */
layout(std140, set = 0, binding = 0) uniform U {
    vec4 right, up, fwd, scale, grid, eqRight, eqUp, eqFwd, proj, fine;
    vec4 cut;      /* par catalogue (m.z) : grandeur relative en dessous de laquelle la source n'est pas dessinée (champ large) */
} u;
struct Src { vec4 d; uvec4 m; };
layout(std430, set = 0, binding = 2) readonly buffer S { Src s[]; } src;
layout(location = 0) out vec3 vCol;
const vec3 COL[8] = vec3[8](vec3(0.85), vec3(0.30, 0.90, 1.00), vec3(0.45, 1.00, 0.40), vec3(1.00, 0.45, 0.65), vec3(0.55, 0.60, 1.00),
                            vec3(1.00, 0.60, 0.20), vec3(1.00, 0.95, 0.30), vec3(0.75, 0.45, 1.00));
void main() {
    Src q = src.s[gl_VertexIndex];
    float z = dot(q.d.xyz, u.eqFwd.xyz);
    bool hidden = q.m.y == 0u && q.d.w < u.cut[min(q.m.z, 3u)];      /* les plus faibles d'abord cachés quand le champ s'élargit */
    if (z <= 0.0 || hidden) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 1.0; vCol = vec3(0.0); return; }
    float x = dot(q.d.xyz, u.eqRight.xyz) / z * u.proj.x;
    float y = -dot(q.d.xyz, u.eqUp.xyz) / z * u.proj.y;
    gl_Position = vec4(x, y, 0.5, 1.0);
    float rel = log(max(q.d.w, 1e-38) / u.proj.w) / log(10.0);
    gl_PointSize = (q.m.y == 1u ? 8.0 : clamp(7.0 + 3.0 * rel, 5.0, 24.0)) * u.grid.w;
    vCol = COL[min(q.m.x, 7u)] * u.scale.w;
}
