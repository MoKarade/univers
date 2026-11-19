#version 450
layout(location = 0) in vec3 vCol;
layout(location = 0) out vec4 o;
void main() { o = vec4(vCol, 1.0); }
