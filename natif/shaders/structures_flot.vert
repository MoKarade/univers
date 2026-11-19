#version 450
/* Lignes de courant du champ de vitesses Cosmicflows-4 (structures.bin) : les galaxies s'écoulent vers les attracteurs. */
layout(location = 0) in vec4 inP;      /* x, y, z (al), vitesse (km/s) */
layout(location = 1) in vec2 inS;      /* chemin depuis le départ (Mpc), bassin (1 Laniakea … 6 Shapley) */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;
layout(location = 0) out vec3 vCol;
layout(location = 1) out float vS;
layout(location = 2) out float vV;
void main() {
    vec3 p = inP.xyz - pc.cam.xyz;
    gl_Position = pc.viewProj * vec4(p, 1.0);
    int b = int(inS.y + 0.5);
    /* Laniakea en or ; les bassins voisins plus discrets, chacun sa teinte */
    vCol = b == 1 ? vec3(1.0, 0.72, 0.30) : b == 6 ? vec3(1.0, 0.45, 0.35) : b == 5 ? vec3(0.45, 0.90, 0.60) : vec3(0.65, 0.65, 0.80);
    vCol *= b == 1 ? 1.0 : 0.45;
    vS = inS.x;
    vV = inP.w;
    vCol *= 1.0 / (1.0 + pow(length(p) / (3.0 * pc.cam.w), 2.0));      /* estompé loin de l'échelle regardée */
}
