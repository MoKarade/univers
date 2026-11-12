#version 450
/* Un astre vu comme une vraie sphère : pour chaque pixel, on cherche où le rayon de vue touche la sphère, on lit
   la carte de surface à cet endroit (longitude, latitude dans le repère lié à l'astre) et on l'éclaire par le Soleil.
   Tout est exprimé en unités de la distance caméra-centre, pour garder la précision de près comme de loin. */
layout(set = 0, binding = 0) uniform sampler2D carte;
layout(push_constant) uniform Pc {
    vec4 centre;   /* xyz : direction caméra -> centre (unitaire) ; w : rayon / distance */
    vec4 droite;   /* xyz : axe droit de la caméra ; w : tan(demi-champ) x rapport largeur/hauteur */
    vec4 haut;     /* xyz : axe haut ; w : tan(demi-champ) */
    vec4 avant;    /* xyz : axe de visée ; w : taille angulaire d'un pixel */
    vec4 soleil;   /* xyz : direction astre -> Soleil ; w : gain (négatif : l'astre brille par lui-même) */
    vec4 rot0;     /* lignes de la matrice écliptique -> repère de l'astre */
    vec4 rot1;
    vec4 rot2;
} pc;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
const float PI = 3.14159265358979;
void main() {
    vec2 ndc = uv * 2.0 - 1.0;
    vec3 d = normalize(pc.avant.xyz + ndc.x * pc.droite.w * pc.droite.xyz - ndc.y * pc.haut.w * pc.haut.xyz);
    float b = dot(d, pc.centre.xyz);
    vec3 p = pc.centre.xyz - b * d;                 /* du rayon au centre, au plus près */
    float rho = pc.centre.w;
    float miss = length(p);
    float cover = clamp((rho - miss) / pc.avant.w + 0.5, 0.0, 1.0);   /* bord adouci sur un pixel */
    if (b <= 0.0 || cover <= 0.0) discard;
    float s = sqrt(max(rho * rho - miss * miss, 0.0));
    vec3 n = normalize(-p - d * s);                 /* normale à la surface au point touché */
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
        c = albedo * pc.soleil.w * max(dot(n, pc.soleil.xyz), 0.0);   /* surface mate éclairée par le Soleil (loi de Lambert) ; nuit : noir */
    }
    o = vec4(c, cover);
}
