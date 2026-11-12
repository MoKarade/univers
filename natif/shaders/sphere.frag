#version 450
/* Un astre vu comme une vraie sphère : pour chaque pixel, on cherche où le rayon de vue touche la sphère, on lit
   la carte de surface à cet endroit (longitude, latitude dans le repère lié à l'astre) et on l'éclaire par le Soleil.
   Tout est exprimé en unités de la distance caméra-centre, pour garder la précision de près comme de loin.
   Anneaux (Saturne) : disque plat dans le plan de l'équateur ; l'ombre de la planète tombe sur les anneaux et
   l'ombre des anneaux sur la planète. */
layout(set = 0, binding = 0) uniform sampler2D carte;
layout(set = 0, binding = 1) uniform sampler2D anneau;
layout(push_constant) uniform Pc {
    vec4 centre;   /* xyz : direction caméra -> centre (unitaire) ; w : rayon / distance */
    vec4 droite;   /* xyz : axe droit de la caméra ; w : tan(demi-champ) x rapport largeur/hauteur */
    vec4 haut;     /* xyz : axe haut ; w : tan(demi-champ) */
    vec4 avant;    /* xyz : axe de visée ; w : taille angulaire d'un pixel */
    vec4 soleil;   /* xyz : direction astre -> Soleil ; w : gain (négatif : l'astre brille par lui-même) */
    vec4 rot0;     /* lignes de la matrice écliptique -> repère de l'astre ; w : bord intérieur des anneaux (en rayons ; 0 : pas d'anneaux) */
    vec4 rot1;     /* w : bord extérieur des anneaux (en rayons) */
    vec4 rot2;     /* xyz : pôle nord de l'astre */
} pc;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
const float PI = 3.14159265358979;

/* Opacité des anneaux à la distance r du centre (en rayons de la planète), 0 hors des anneaux. */
float ringAlpha(float r, out vec3 colour) {
    colour = vec3(0.0);
    if (pc.rot0.w <= 0.0 || r <= pc.rot0.w || r >= pc.rot1.w) return 0.0;
    vec4 t = texture(anneau, vec2((r - pc.rot0.w) / (pc.rot1.w - pc.rot0.w), 0.5));
    colour = t.rgb;
    return t.a;
}

void main() {
    vec2 ndc = uv * 2.0 - 1.0;
    vec3 d = normalize(pc.avant.xyz + ndc.x * pc.droite.w * pc.droite.xyz - ndc.y * pc.haut.w * pc.haut.xyz);
    vec3 C = pc.centre.xyz, N = pc.rot2.xyz, S = pc.soleil.xyz;
    float rho = pc.centre.w;
    float b = dot(d, C);
    vec3 p = C - b * d;                             /* du rayon au centre, au plus près */
    float miss = length(p);
    float cover = b > 0.0 ? clamp((rho - miss) / pc.avant.w + 0.5, 0.0, 1.0) : 0.0;   /* bord adouci sur un pixel */
    vec4 res = vec4(0.0);
    float tSphere = 1e30;
    if (cover > 0.0) {
        float s = sqrt(max(rho * rho - miss * miss, 0.0));
        tSphere = b - s;
        vec3 hp = -p - d * s;                       /* point touché, compté depuis le centre */
        vec3 n = normalize(hp);
        vec3 nb = vec3(dot(pc.rot0.xyz, n), dot(pc.rot1.xyz, n), dot(pc.rot2.xyz, n));
        float lon = atan(nb.y, nb.x), lat = asin(clamp(nb.z, -1.0, 1.0));
        /* longitude 0 au milieu de la carte, est vers la droite. La longitude saute de +180° à -180° au méridien
           opposé : pour choisir le bon niveau de détail, on prend la variation de la longitude comptée de 0 à 360°
           là où elle est la plus douce (sinon une couture apparaît). La carte lue est la même dans les deux cas. */
        float u1 = lon / (2.0 * PI) + 0.5, u2 = fract(u1 + 0.5);
        vec2 tc = vec2(u1, 0.5 - lat / PI);
        float dux = abs(dFdx(u1)) <= abs(dFdx(u2)) ? dFdx(u1) : dFdx(u2);
        float duy = abs(dFdy(u1)) <= abs(dFdy(u2)) ? dFdy(u1) : dFdy(u2);
        vec3 albedo = textureGrad(carte, tc, vec2(dux, dFdx(tc.y)), vec2(duy, dFdy(tc.y))).rgb;
        vec3 c;
        if (pc.soleil.w < 0.0) {
            float mu = max(dot(n, -d), 0.0);
            c = albedo * (-pc.soleil.w) * (1.0 - 0.6 * (1.0 - mu));      /* assombrissement du bord du Soleil, coefficient 0,6 dans le visible */
        } else {
            float light = max(dot(n, S), 0.0);                            /* surface mate éclairée par le Soleil (loi de Lambert) ; nuit : noir */
            float sn = dot(S, N);
            if (pc.rot0.w > 0.0 && abs(sn) > 1e-5) {                      /* ombre des anneaux sur la planète */
                float tr = -dot(hp, N) / sn;
                if (tr > 0.0) {
                    vec3 rc;
                    light *= 1.0 - ringAlpha(length(hp + S * tr) / rho, rc);
                }
            }
            c = albedo * pc.soleil.w * light;
        }
        res = vec4(c, cover);
    }
    float dn = dot(d, N);
    if (pc.rot0.w > 0.0 && abs(dn) > 1e-6) {
        float t = dot(C, N) / dn;                   /* où le rayon de vue traverse le plan des anneaux */
        if (t > 0.0) {
            vec3 h = d * t - C;
            vec3 rc;
            float a = ringAlpha(length(h) / rho, rc);
            if (a > 0.0) {
                float bs = dot(h, S);
                bool shadow = bs < 0.0 && length(h - bs * S) < rho;       /* ombre de la planète sur les anneaux */
                rc *= shadow ? 0.0 : pc.soleil.w;
                vec3 under = res.rgb * res.a;
                if (t < tSphere) res = vec4(rc * a + under * (1.0 - a), a + res.a * (1.0 - a));      /* anneaux devant la planète */
                else res = vec4(under + rc * a * (1.0 - res.a), res.a + a * (1.0 - res.a));          /* anneaux derrière */
                res.rgb /= max(res.a, 1e-5);
            }
        }
    }
    if (res.a <= 0.0) discard;
    o = res;
}
