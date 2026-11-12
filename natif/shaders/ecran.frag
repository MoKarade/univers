#version 450
/* Passage de l'image en grande dynamique vers l'écran : compression de Reinhard (c / (1 + c)).
   La surface d'écran est en sRGB : la carte applique elle-même la courbe sRGB à la sortie. */
layout(set = 0, binding = 0) uniform sampler2D hdr;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
void main() {
    vec3 c = texture(hdr, uv).rgb;
    o = vec4(c / (1.0 + c), 1.0);
}
