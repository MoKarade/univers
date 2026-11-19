#version 450
/* Tirets qui avancent dans le sens du flot, d'autant plus vite que le flot est rapide : ils montrent le SENS et la vitesse
   relative, pas la vraie vitesse (quelques centaines de km/s : des millions d'années pour franchir un mégaparsec). */
layout(location = 0) in vec3 vCol;
layout(location = 1) in float vS;
layout(location = 2) in float vV;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;
layout(location = 0) out vec4 o;
void main() {
    float ph = fract(vS / 12.0 - pc.par.z * vV / 2000.0);
    float pulse = 0.25 + 0.75 * smoothstep(0.75, 1.0, ph);
    o = vec4(vCol * pc.par.x * 0.035 * pulse, 1.0);
}
