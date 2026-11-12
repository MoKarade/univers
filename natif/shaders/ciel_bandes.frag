#version 450
/* Le ciel dans une autre longueur d'onde (ciel_bandes.h) : pour chaque pixel de l'écran, la direction regardée est
   tournée dans le repère du relevé (galactique ou équatorial), convertie en numéro de pixel HEALPix emboîté
   (Górski et al. 2005 ; même calcul que pipeline/natif/ciel_bandes.py, contrôlé contre healpy), et la valeur MESURÉE de
   ce pixel est lue telle quelle. Pas d'interpolation : on voit le pixel du relevé. Quand un pixel du relevé est plus
   petit qu'un pixel de l'écran, on lit le niveau de la pyramide (moyenne des pixels mesurés, ciel_bandes.h) qui a la taille
   du pixel de l'écran : la vue large est la somme du mesuré, sans grain artificiel.
   Couleur : fausses couleurs (palette « inferno », van der Walt et Smith 2015, approchée par un polynôme), échelle
   logarithmique ou linéaire entre deux valeurs données par la fiche de la bande. Pixel sans mesure : hachures grises,
   pour montrer le trou de couverture au lieu d'inventer une valeur. */
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;
layout(std140, set = 0, binding = 0) uniform U {
    vec4 right, up, fwd;   /* vecteurs de la caméra dans le repère du relevé, déjà multipliés par tan(champ/2) */
    vec4 scale;            /* x : bas de l'échelle ; y : haut ; z : 1 = logarithmique ; w : opacité (effacement loin du Soleil) */
    vec4 grid;             /* x : Nside ; y : niveaux de la pyramide ; z : angle d'un pixel de l'écran au centre (rad) ; w : rien */
} u;
layout(std430, set = 0, binding = 1) readonly buffer Carte { float v[]; } carte;

const float PI = 3.14159265358979;

uint spread(uint x) {      /* bits de x écartés d'un rang : 0b1011 -> 0b1000101 */
    x &= 0xFFFFu;
    x = (x | (x << 8)) & 0x00FF00FFu;
    x = (x | (x << 4)) & 0x0F0F0F0Fu;
    x = (x | (x << 2)) & 0x33333333u;
    x = (x | (x << 1)) & 0x55555555u;
    return x;
}

uint ang2pixNest(int nside, vec3 d) {
    float z = d.z, za = abs(z);
    float phi = atan(d.y, d.x);
    if (phi < 0.0) phi += 2.0 * PI;
    float tt = phi / (0.5 * PI);
    int face, ix, iy;
    if (za <= 2.0 / 3.0) {
        float t1 = float(nside) * (0.5 + tt), t2 = float(nside) * z * 0.75;
        int jp = int(t1 - t2), jm = int(t1 + t2);
        int ifp = jp / nside, ifm = jm / nside;
        face = ifp == ifm ? (ifp | 4) : (ifp < ifm ? ifp : ifm + 8);
        ix = jm & (nside - 1);
        iy = nside - (jp & (nside - 1)) - 1;
    } else {
        int ntt = min(int(tt), 3);
        float tp = tt - float(ntt);
        float tmp = float(nside) * sqrt(3.0 * (1.0 - za));
        int jp = min(int(tp * tmp), nside - 1), jm = min(int((1.0 - tp) * tmp), nside - 1);
        if (z >= 0.0) { face = ntt; ix = nside - jm - 1; iy = nside - jp - 1; }
        else { face = ntt + 8; ix = jp; iy = jm; }
    }
    return uint(face) * uint(nside) * uint(nside) + spread(uint(ix)) + 2u * spread(uint(iy));
}

vec3 inferno(float t) {      /* polynôme de Matt Zucker (Shadertoy WlfXRN, domaine public) ajusté sur la palette inferno */
    const vec3 c0 = vec3(0.0002189403691192265, 0.001651004631001012, -0.01948089843709184);
    const vec3 c1 = vec3(0.1065134194856116, 0.5639564367884091, 3.932712388889277);
    const vec3 c2 = vec3(11.60249308247187, -3.972853965665698, -15.9423941062914);
    const vec3 c3 = vec3(-41.70399613139459, 17.43639888205313, 44.35414519872813);
    const vec3 c4 = vec3(77.162935699427, -33.40235894210092, -81.80730925738993);
    const vec3 c5 = vec3(-71.31942824499214, 32.62606426397723, 73.20951985803202);
    const vec3 c6 = vec3(25.13112622477341, -12.24266895238567, -23.07032500287172);
    return clamp(c0 + t * (c1 + t * (c2 + t * (c3 + t * (c4 + t * (c5 + t * c6))))), 0.0, 1.0);
}

void main() {
    vec2 ndc = uv * 2.0 - 1.0;
    vec3 ray = u.fwd.xyz + ndc.x * u.right.xyz - ndc.y * u.up.xyz;
    vec3 dir = normalize(ray);
    /* angle couvert par ce pixel de l'écran (plus petit au bord de l'image), et taille d'un pixel HEALPix du niveau 0 */
    float screen = u.grid.z / dot(ray, ray);
    float hpx = sqrt(4.0 * PI / (12.0 * u.grid.x * u.grid.x));
    int level = clamp(int(floor(log2(max(screen / hpx, 1.0)))), 0, int(u.grid.y) - 1);
    int nside = int(u.grid.x) >> level;
    uint base = 0u;
    for (int l = 0; l < level; ++l) { uint ns = uint(int(u.grid.x) >> l); base += 12u * ns * ns; }
    float val = carte.v[base + ang2pixNest(nside, dir)];
    vec3 c;
    if (isnan(val)) {      /* pas de mesure : hachures, une ligne sur huit pixels de l'écran */
        float h = mod(gl_FragCoord.x + gl_FragCoord.y, 8.0);
        c = h < 1.5 ? vec3(0.22) : vec3(0.04);
    } else {
        float t;
        if (u.scale.z > 0.5) t = val > 0.0 ? (log(val) - log(u.scale.x)) / (log(u.scale.y) - log(u.scale.x)) : 0.0;
        else t = (val - u.scale.x) / (u.scale.y - u.scale.x);
        c = inferno(clamp(t, 0.0, 1.0));
    }
    c *= u.scale.w;
    /* l'image passe ensuite par la compression c / (1 + c) (ecran.frag) : on écrit l'inverse pour que l'écran montre c */
    c = min(c, vec3(0.985));
    o = vec4(c / (1.0 - c), 1.0);
}
