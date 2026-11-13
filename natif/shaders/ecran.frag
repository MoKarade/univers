#version 450
/* Passage de l'image en grande dynamique vers l'image finale : compression de Reinhard (c / (1 + c)), puis
   courbe sRGB (CEI 61966-2-1). L'image finale garde des valeurs prêtes pour l'écran : l'interface s'y ajoute telle quelle. */
layout(set = 0, binding = 0) uniform sampler2D hdr;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
layout(push_constant) uniform Pc { vec4 p; } pc;      /* p.x : 1 = photo (asinh), 0 = œil nu */
vec3 srgb(vec3 c) {
    return mix(12.92 * c, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}
void main() {
    vec3 c = texture(hdr, uv).rgb;
    if (pc.p.x > 0.5) {
        /* photo : étirement asinh de la luminance, comme les images astronomiques (Lupton et al. 2004) : la teinte est gardée,
           les zones faibles ressortent, les fortes saturent doucement */
        float Y = dot(c, vec3(0.2126, 0.7152, 0.0722));
        const float beta = 0.05;
        float f = Y > 0.0 ? asinh(Y / beta) / asinh(1.0 / beta) / Y : 0.0;
        o = vec4(srgb(clamp(c * f, 0.0, 1.0)), 1.0);
    } else o = vec4(srgb(c / (1.0 + c)), 1.0);
}
