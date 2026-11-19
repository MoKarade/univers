#version 450
/* Surfaces des grandes structures (structures.bin) : frontière de Laniakea, vides cosmiques. Repère, pas de la lumière. */
layout(location = 0) in vec3 inPos;      /* années-lumière, écliptique J2000 */
layout(location = 1) in vec3 inNor;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;   /* par : part montrée, hauteur, horloge, genre */
layout(location = 0) out vec3 vRel;
layout(location = 1) out vec3 vNor;
void main() {
    vRel = inPos - pc.cam.xyz;
    vNor = inNor;
    gl_Position = pc.viewProj * vec4(vRel, 1.0);
}
