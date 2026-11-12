#version 450
layout(location = 0) in vec3 vCol;
layout(location = 0) out vec4 o;
void main() {
    vec2 q = gl_PointCoord * 2.0 - 1.0;
    float g = exp(-4.0 * dot(q, q));      /* tache ronde, bords doux */
    o = vec4(vCol * g * 5.09, 1.0);       /* 5,09 : la somme de la tache sur ses pixels vaut 1 (4 / (pi/4)) */
}
