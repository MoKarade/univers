#version 450
/* La matière autour d'une étoile (cycle_nebuleuse.h) : couches sphériques à émissivité et extinction constantes dans
   chaque anneau. Pour chaque pixel, la longueur exacte du rayon de vue dans chaque anneau (cordes d'une sphère), du
   point de vue de la caméra vers l'avant (la caméra peut être dans la nébuleuse). Mode 0 : extinction par la poussière
   (multiplie ce qui est derrière par exp(-τ)) ; mode 1 : lumière émise (ajoutée). */
layout(std430, set = 0, binding = 0) readonly buffer Profils { float v[]; } prof;
layout(push_constant) uniform Pc {
    vec4 centre;   /* xyz : direction caméra -> centre (unitaire) ; w : distance (années-lumière) */
    vec4 droite;   /* xyz : axe droit de la caméra ; w : tan(demi-champ) x rapport largeur/hauteur */
    vec4 haut;     /* xyz : axe haut ; w : tan(demi-champ) */
    vec4 avant;    /* xyz : axe de visée ; w : inutilisé */
    vec4 par;      /* x : début du profil dans le tampon ; y : nombre d'anneaux ; z : facteur d'éclat ; w : mode */
} pc;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;

void main() {
    vec2 ndc = uv * 2.0 - 1.0;
    vec3 d = normalize(pc.avant.xyz + ndc.x * pc.droite.w * pc.droite.xyz - ndc.y * pc.haut.w * pc.haut.xyz);
    float D = pc.centre.w;
    float s0 = D * dot(pc.centre.xyz, d);                 /* distance, le long du rayon, du point le plus proche du centre */
    float b = D * length(cross(pc.centre.xyz, d));        /* paramètre d'impact (précis même loin) */
    float b2 = b * b;
    int base = int(pc.par.x + 0.5), n = int(pc.par.y + 0.5);
    int rgbAt = base + n + 1, extAt = rgbAt + 3 * n;
    vec3 em = vec3(0.0);
    float tau = 0.0;
    for (int k = 0; k < n; ++k) {
        float r0 = prof.v[base + k], r1 = prof.v[base + k + 1];
        if (r1 * r1 <= b2) continue;
        float h1 = sqrt(r1 * r1 - b2);
        float h0 = r0 * r0 > b2 ? sqrt(r0 * r0 - b2) : 0.0;
        /* deux morceaux : [s0 - h1, s0 - h0] et [s0 + h0, s0 + h1], gardés devant la caméra (s >= 0) */
        float l = max(0.0, (s0 - h0) - max(s0 - h1, 0.0)) + max(0.0, (s0 + h1) - max(s0 + h0, 0.0));
        if (l <= 0.0) continue;
        em += vec3(prof.v[rgbAt + 3 * k], prof.v[rgbAt + 3 * k + 1], prof.v[rgbAt + 3 * k + 2]) * l;
        tau += prof.v[extAt + k] * l;
    }
    if (pc.par.w < 0.5) o = vec4(vec3(exp(-tau)), 1.0);
    else o = vec4(em * pc.par.z, 1.0);
}
