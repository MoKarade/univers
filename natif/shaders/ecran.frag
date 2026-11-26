#version 450
/* Passage de l'image en grande dynamique vers l'image finale : compression de Reinhard (c / (1 + c)), puis
   courbe sRGB (CEI 61966-2-1). L'image finale garde des valeurs prêtes pour l'écran : l'interface s'y ajoute telle quelle. */
layout(set = 0, binding = 0) uniform sampler2D hdr;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
layout(push_constant) uniform Pc { vec4 p; } pc;      /* p.x : 1 = photo (asinh), 0 = œil nu ; p.y : pose automatique contre la saturation (pose_auto.h, 1 = aucune) */
vec3 srgb(vec3 c) {
    vec3 hi = 1.055 * pow(max(c, vec3(0.0031308)), vec3(1.0 / 2.4)) - 0.055;
    return mix(12.92 * max(c, vec3(0.0)), hi, step(0.0031308, c));
}
void main() {
    /* borne avant tout calcul : une somme de points qui déborde les 16 bits (inf) donnait des pixels noirs (NaN) (audit A2) */
    vec3 c = clamp(texture(hdr, uv).rgb, vec3(0.0), vec3(6.0e4)) * (pc.p.y > 0.0 ? pc.p.y : 1.0);
    /* œil nu : compression de Reinhard (Reinhard et al. 2002), couleur par couleur */
    vec3 nu = c / (1.0 + c);
    /* photo : étirement asinh de la luminance, comme les images astronomiques (Lupton et al. 2004) : la teinte est gardée,
       les zones faibles ressortent, les fortes saturent doucement. pc.p.x (0 à 1) fond les deux : avant, la courbe basculait
       d'un coup quand une galaxie entrait dans l'image (×3 d'éclat mesuré d'un degré de défilement au suivant). */
    if (pc.p.x > 0.0) {
        float Y = dot(c, vec3(0.2126, 0.7152, 0.0722));
        const float beta = 0.05;
        float f = Y > 0.0 ? asinh(Y / beta) / asinh(1.0 / beta) / Y : 0.0;
        nu = mix(nu, clamp(c * f, 0.0, 1.0), clamp(pc.p.x, 0.0, 1.0));
    }
    o = vec4(srgb(nu), 1.0);
}
