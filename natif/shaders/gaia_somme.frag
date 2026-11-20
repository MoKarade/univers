#version 450
#extension GL_ARB_gpu_shader_int64 : require
/* Somme par pixel des étoiles Gaia (gaia_points.comp) versée dans l'image en grande dynamique, par addition comme les autres
   couches. */
layout(std430, set = 0, binding = 0) readonly buffer Somme { uint64_t somme[]; };
layout(push_constant) uniform P { uint largeur; } pc;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
void main() {
    uint px = uint(gl_FragCoord.y) * pc.largeur + uint(gl_FragCoord.x);
    const float k = 1.0 / 16777216.0;      /* 2^-24 : pas de la somme */
    o = vec4(float(somme[3u * px]) * k, float(somme[3u * px + 1u]) * k, float(somme[3u * px + 2u]) * k, 1.0);
}
