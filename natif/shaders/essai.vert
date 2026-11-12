#version 450
/* Essai N0 : un triangle, sans tampon de sommets. */
vec2 P[3] = vec2[](vec2(0.0, -0.6), vec2(0.6, 0.6), vec2(-0.6, 0.6));
void main() { gl_Position = vec4(P[gl_VertexIndex], 0.0, 1.0); }
