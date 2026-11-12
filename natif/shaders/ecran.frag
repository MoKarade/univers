#version 450
/* Passage de l'image en grande dynamique vers l'écran : compression de Reinhard (c / (1 + c)), puis le bandeau
   de texte (aide et position) en bas à gauche. La surface d'écran est en sRGB : la carte applique la courbe. */
layout(set = 0, binding = 0) uniform sampler2D hdr;
layout(set = 0, binding = 1) uniform sampler2D texte;
layout(push_constant) uniform Pc { vec4 dim; } pc;   /* largeur et hauteur de la fenêtre, largeur et hauteur du bandeau, en pixels */
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
void main() {
    vec3 c = texture(hdr, uv).rgb;
    c = c / (1.0 + c);
    vec2 p = gl_FragCoord.xy - vec2(18.0, pc.dim.y - pc.dim.w - 14.0);
    if (p.x >= 0.0 && p.y >= 0.0 && p.x < pc.dim.z && p.y < pc.dim.w) {
        float a = texture(texte, p / pc.dim.zw).r;
        c = mix(c, vec3(0.78), a);
    }
    o = vec4(c, 1.0);
}
