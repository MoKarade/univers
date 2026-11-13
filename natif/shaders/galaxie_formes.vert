#version 450
/* Galaxies de forme MESURÉE (galaxies_formes.h, pipeline/natif/galaxies_formes.py : SGA-2020, HyperLEDA, Cosmicflows-4).
   Deux modes (pc.par.w) :
   0 : un point par galaxie, au vrai éclat (magnitude r), part (1 - s) de la lumière ;
   1 : une galaxie de particules (instance = galaxie, sommet = particule), part s de la lumière partagée entre ses N
       particules ; s passe de 0 à 1 quand la galaxie grandit de 2 à 8 pixels à l'écran : aucun saut, lumière conservée.
   Forme : disque exponentiel + bulbe (spirales, lenticulaires), bras logarithmiques au nombre et au pas typiques du type,
   sphéroïde aplati (elliptiques), grumeaux (irrégulières). Taille : diamètre D26 mesuré ; orientation : angle de position et
   rapport d'axes mesurés (inclinaison avec une épaisseur propre q0 = 0,2) ; côté proche, phase des bras, sens : tirés de la
   graine (modèle) ; type inconnu : tiré aussi (modèle). */
struct Rec { float ux, uy, uz, z, d, diam, ba, pa, T, r, gr; uint f; };
layout(std430, set = 0, binding = 0) readonly buffer Recs { Rec rec[]; };
layout(std430, set = 0, binding = 1) readonly buffer Pos { vec4 rel[]; };      /* position par rapport à la caméra (al), distance au Soleil (al) */
layout(std430, set = 0, binding = 2) readonly buffer Nb { uint npart[]; };      /* particules de la galaxie à cette image */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 par; vec4 par2; } pc;      /* par : exposition, hauteur (px), pixels par radian, mode */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
const float EPS = 0.40909280;      /* obliquité J2000 (rad) */

uint h(uint x) { x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15; x *= 0x846ca68bu; x ^= x >> 16; return x; }
float U(uint x) { return (float(h(x)) + 0.5) / 4294967296.0; }
float N01(uint x) { return sqrt(-2.0 * log(U(x))) * cos(6.2831853 * U(x ^ 0x9e3779b9u)); }

/* couleur d'un corps noir (approximation de Tanner Helland) */
vec3 couleurT(float T) {
    float t = clamp(T, 1000.0, 40000.0) / 100.0;
    float r = t <= 66.0 ? 1.0 : clamp(1.2929 * pow(t - 60.0, -0.1332), 0.0, 1.0);
    float g = t <= 66.0 ? clamp(0.3901 * log(t) - 0.6318, 0.0, 1.0) : clamp(1.1298 * pow(t - 60.0, -0.0755), 0.0, 1.0);
    float b = t >= 66.0 ? 1.0 : (t <= 19.0 ? 0.0 : clamp(0.5432 * log(t - 10.0) - 1.1962, 0.0, 1.0));
    return vec3(r, g, b);
}
/* g - r -> B - V -> température (Ballesteros 2012) */
float tempGR(float gr) { float bv = 0.98 * gr + 0.22; return 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62)); }

void cacher() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); }

void main() {
    bool particules = pc.par.w > 0.5;
    uint g = particules ? uint(gl_InstanceIndex) : uint(gl_VertexIndex);
    uint k = particules ? uint(gl_VertexIndex) : 0u;
    Rec R = rec[g];
    vec4 P = rel[g];
    float dCam = max(length(P.xyz), 1.0);
    float diamRad = R.diam * 2.9088821e-4;      /* minutes d'arc -> radians */
    float px = diamRad * P.w / dCam * pc.par.z;
    float s = smoothstep(2.0, 8.0, px);
    float F = pc.par.x * pow(10.0, -0.4 * R.r);      /* flux vu du Soleil, même loi que les étoiles */
    uint seed = g * 2654435761u;

    /* type : mesuré, sinon tiré (30 % elliptiques et lenticulaires, 60 % spirales, 10 % irrégulières) [modèle] */
    float T = R.T;
    if (T > 90.0) { float u = U(seed ^ 77u); T = u < 0.2 ? -5.0 : (u < 0.3 ? -2.0 : (u < 0.9 ? 1.0 + 7.0 * U(seed ^ 78u) : 10.0)); }
    float Tc = R.gr < 90.0 ? tempGR(R.gr) : (T < -1.0 ? 4300.0 : (T < 6.0 ? 5200.0 : 7500.0));

    vec3 p = P.xyz, col = couleurT(Tc);
    float part = 1.0 - s;
    if (particules) {
        uint n = max(npart[g], 1u);
        if (k >= n) { cacher(); return; }
        part = s / float(n);
        /* repère du ciel autour de la direction de la galaxie (écliptique) : nord céleste, est */
        vec3 u = vec3(R.ux, R.uy, R.uz);
        vec3 ncp = vec3(0.0, sin(EPS), cos(EPS));
        vec3 est = normalize(cross(ncp, u)), nord = cross(u, est);
        float pa = radians(R.pa >= 0.0 ? R.pa : 360.0 * U(seed ^ 11u));
        float ba = R.ba > 0.0 ? clamp(R.ba, 0.05, 1.0) : 0.3 + 0.7 * U(seed ^ 12u);
        float q0 = 0.2, cosi = sqrt(clamp((ba * ba - q0 * q0) / (1.0 - q0 * q0), 0.0, 1.0)), sini = sqrt(1.0 - cosi * cosi);
        vec3 grand = cos(pa) * nord + sin(pa) * est, petit = -sin(pa) * nord + cos(pa) * est;
        float proche = U(seed ^ 13u) < 0.5 ? 1.0 : -1.0;      /* côté proche non mesuré [modèle] */
        vec3 incl = cosi * petit + proche * sini * u;
        vec3 nrm = normalize(cross(grand, incl));
        float R26 = 0.5 * diamRad * P.w;      /* rayon à l'isophote 26 (al) */
        float hd = R26 / 3.5;                 /* longueur d'échelle du disque : l'isophote 26 tombe vers 3,5 longueurs [supposé] */
        uint q = seed ^ (k * 0x85ebca6bu + 0x27d4eb2fu);
        vec3 o;
        float tcomp = Tc;
        if (T < -2.5) {                       /* elliptique : profil de Hernquist, axes mesurés (grand, petit, ligne de visée ~ petit) */
            float v = U(q), a = 0.25 * R26;
            float rr = min(a * sqrt(v) / (1.0 - sqrt(v)), 3.0 * R26);
            float cz = 2.0 * U(q ^ 1u) - 1.0, ph = 6.2831853 * U(q ^ 2u);
            vec3 d = vec3(sqrt(1.0 - cz * cz) * cos(ph), sqrt(1.0 - cz * cz) * sin(ph), cz);
            o = rr * (d.x * grand + ba * d.y * petit + ba * d.z * u);
            tcomp = Tc - 300.0;
        } else {
            float bt = T < 0.5 ? 0.5 : clamp(0.45 - 0.05 * T, 0.03, 0.45);      /* part du bulbe selon le type [ordre publié, supposé] */
            vec3 e1 = grand, e2 = normalize(cross(nrm, e1));
            if (U(q ^ 3u) < bt) {             /* bulbe : Hernquist aplati */
                float v = U(q ^ 4u), a = 0.08 * R26;
                float rr = min(a * sqrt(v) / (1.0 - sqrt(v)), R26);
                float cz = 2.0 * U(q ^ 5u) - 1.0, ph = 6.2831853 * U(q ^ 6u);
                o = rr * (sqrt(1.0 - cz * cz) * cos(ph) * e1 + sqrt(1.0 - cz * cz) * sin(ph) * e2 + 0.7 * cz * nrm);
                tcomp = Tc - 600.0;
            } else if (T > 9.5) {             /* irrégulière : grumeaux */
                uint c = h(q ^ 7u) % 7u;
                float cr = hd * 1.5 * sqrt(U(seed ^ (c * 31u + 1u))), cph = 6.2831853 * U(seed ^ (c * 31u + 2u));
                vec2 cc = cr * vec2(cos(cph), sin(cph)) + 0.35 * hd * vec2(N01(q ^ 8u), N01(q ^ 9u));
                o = cc.x * e1 + cc.y * e2 + 0.15 * hd * N01(q ^ 10u) * nrm;
                tcomp = Tc + 2500.0;
            } else {                          /* disque exponentiel, bras logarithmiques pour les spirales */
                float rr = -hd * log(U(q ^ 11u) * U(q ^ 12u));
                float ph = 6.2831853 * U(q ^ 13u);
                if (T > 0.5 && U(q ^ 14u) < (T < 6.0 ? 0.55 : 0.3)) {
                    float arms = T < 6.0 ? 2.0 : 3.0 + floor(3.0 * U(seed ^ 15u));      /* 2 bras (grand dessin) ou plus (floconneuse) [modèle] */
                    float pitch = radians(8.0 + 3.0 * T);                                /* angle d'enroulement selon le type [ordre publié] */
                    float j = floor(arms * U(q ^ 16u));
                    ph = 6.2831853 * (U(seed ^ 17u) + j / arms) - log(max(rr, 0.05 * hd) / hd) / tan(pitch) + 0.25 * N01(q ^ 18u);
                    tcomp = Tc + 2500.0;      /* étoiles jeunes des bras */
                }
                o = rr * (cos(ph) * e1 + sin(ph) * e2) + 0.08 * hd * N01(q ^ 19u) * nrm;
            }
        }
        p += o;
        col = couleurT(tcomp);
    }
    float d = max(length(p), 1.0);
    float flux = F * part * (P.w / d) * (P.w / d);
    float size = particules ? 1.6 * pc.par.y / 1080.0 : clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 6.0) * pc.par.y / 1080.0;
    if (flux <= 0.0) { cacher(); return; }
    vCol = col * min(flux, 3.0e4) / (size * size);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
