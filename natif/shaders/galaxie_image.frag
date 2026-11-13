#version 450
/* Lumière de la photo : valeur au carré (la photo garde la racine carrée de la lumière), recalée sur la magnitude
   absolue publiée (par.x), ramenée à l'angle de vue (vSlant). */
layout(set = 0, binding = 0) uniform sampler2D photo;
layout(location = 0) in vec2 vUv;
layout(location = 1) in float vSlant;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 centre; vec4 normal; vec4 par; } pc;
layout(location = 0) out vec4 o;
void main() {
    vec3 c = texture(photo, vUv).rgb;
    o = vec4(c * c * (pc.par.x * vSlant), 0.0);
}
