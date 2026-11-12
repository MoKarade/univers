#version 450
layout(location = 0) in vec3 vCol;
layout(location = 0) out vec4 o;
void main() {
    vec2 q = gl_PointCoord * 2.0 - 1.0;
    float r2 = dot(q, q);
    if (r2 > 1.0) discard;                 /* tache ronde : rien hors du disque, même pour un astre très brillant */
    float g = exp(-4.0 * r2);              /* bords doux */
    o = vec4(vCol * g * 5.19, 1.0);        /* 5,19 : la somme de la tache sur le disque vaut 1 (4 / (pi/4 * (1 - e^-4))) */
}
