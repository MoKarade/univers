#version 450
/* Passage de l'image en grande dynamique vers l'image finale : compression de Reinhard (c / (1 + c)), puis
   courbe sRGB (CEI 61966-2-1). L'image finale garde des valeurs prêtes pour l'écran : l'interface s'y ajoute telle quelle. */
layout(set = 0, binding = 0) uniform sampler2D hdr;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
vec3 srgb(vec3 c) {
    return mix(12.92 * c, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}
void main() {
    vec3 c = texture(hdr, uv).rgb;
    o = vec4(srgb(c / (1.0 + c)), 1.0);
}
