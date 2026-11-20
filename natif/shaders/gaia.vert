#version 450
#extension GL_GOOGLE_include_directive : require
#include "orbite_galactique.glsl"
/* Étoiles Gaia DR3 (gaia.h) : lues directement dans des tampons de stockage. Même éclat et même tache que les étoiles
   du catalogue principal (etoiles.vert) : magnitude absolue G mesurée, loi en 1/d², position relative à la caméra
   soustraite en deux temps. Vitesse lue seulement si le temps a bougé depuis les mesures (J2016,0) ; par.w : milliards d'années depuis ces mesures. */
layout(std430, set = 0, binding = 0) readonly buffer Stars { uvec4 star[]; };          /* x, y, z (al), puis magnitude (demi-flottant) | couleur << 16 | drapeaux << 24 */
layout(std430, set = 0, binding = 1) readonly buffer Vel { uvec2 vel[]; };             /* vx, vy, vz en pas de 0,05 km/s (entiers 16 bits) */
layout(std430, set = 0, binding = 2) readonly buffer Col { vec4 colorOf[]; };          /* 256 pas de BP-RP -> couleur du corps noir */
struct Etat { vec4 p; vec4 v; };
layout(std430, set = 0, binding = 3) readonly buffer Orb { Etat orb[]; };        /* orbites exactes (gaia_orbites.h, orbites_pas.comp), le Soleil en dernier */
layout(set = 0, binding = 4) uniform sampler3D dust;      /* poussière 3D (voie_lactee.bin, canal g : A_V par pc), seulement si GF_POUSSIERE */
struct GalVoisine { vec4 c0; vec4 ct; vec4 axe; vec4 rr; };      /* gaia.h : cases 0-5 setGalaxies (centre à t = 0, à la date, axe + vitesse, rayon) ; 6-7 setAgeing */
layout(std430, set = 0, binding = 5) readonly buffer Voisines { GalVoisine voisines[]; };
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; uint sun; float frac; float exact; uint cellBase; vec4 hide; } pc;   /* hide : copie de l'étoile suivie (gaia.h, setHide) */   /* par : exposition, hauteur en pixels, temps en al par (km/s), temps en Ga */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
#include "gaia_acc.glsl"
#include "gaia_fiable.glsl"
/* Sous-nuage d'une étoile du MODÈLE (drapeau 16, traceur qui porte la lumière de nombreuses étoiles) : GV_SOUS_NUAGE étoiles,
   une par instance du dessin (gaia.h, enableSubClouds), tirées de façon déterministe à partir du rang du traceur (sa graine).
   Lumière : part fixe GV_PART[k] (loi de puissance d'indice -0,7, la plus brillante 20 %, somme = 1 : la lumière du traceur est conservée) ; la
   table est décalée d'un traceur à l'autre. Place : boule aplatie de GV_RAYON années-lumière autour du traceur, ouverte
   en douceur entre GV_LOIN et GV_PRES de la caméra (confondues vu de loin : aucun saut) [modèle]. */
const uint GV_SOUS_NUAGE = 16u;
const float GV_PART[16] = float[](0.201985, 0.124336, 0.093612, 0.076538, 0.065470, 0.057625, 0.051731, 0.047115,
                                  0.043386, 0.040301, 0.037700, 0.035472, 0.033540, 0.031844, 0.030343, 0.029002);
const float GV_RAYON = 60.0, GV_LOIN = 20000.0, GV_PRES = 2000.0;
uint gvHash(uint x) { x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15; x *= 0x846ca68bu; x ^= x >> 16; return x; }
float gvUnif(uint x) { return (float(gvHash(x)) + 0.5) / 4294967296.0; }
/* case 6 ou 7 de la table (gaia.h, setAgeing) : 16 facteurs, un par composante */
float gvCase(GalVoisine G, uint k) { vec4 v = k < 4u ? G.c0 : (k < 8u ? G.ct : (k < 12u ? G.axe : G.rr)); return v[k & 3u]; }
vec3 gvCorpsNoir(float T) {      /* couleur relative d'un corps noir (approximation de Tanner Helland) */
    float t = clamp(T, 1000.0, 40000.0) / 100.0;
    float r = t <= 66.0 ? 1.0 : clamp(1.2929 * pow(t - 60.0, -0.1332), 0.0, 1.0);
    float g = t <= 66.0 ? clamp(0.3901 * log(t) - 0.6318, 0.01, 1.0) : clamp(1.1298 * pow(t - 60.0, -0.0755), 0.01, 1.0);
    float b = t >= 66.0 ? 1.0 : (t <= 19.0 ? 0.01 : clamp(0.5432 * log(t - 10.0) - 1.1962, 0.01, 1.0));
    return vec3(r, g, b);
}
void main() {
    uvec4 r = star[gl_VertexIndex];
    vec3 pos = uintBitsToFloat(r.xyz), move = vec3(0.0);
    uint flags = r.w >> 24;
    /* étoiles mesurées : une seule instance ; les autres instances du dessin (sous-nuages du modèle) ne les concernent pas */
    /* sous-nuage replié (gaia.h, selectLeaves : feuille trop loin pour le distinguer) : une seule instance, d'indice GV_SOUS_NUAGE */
    bool replie = uint(gl_InstanceIndex) >= GV_SOUS_NUAGE;
    if (gl_InstanceIndex > 0 && !replie && (flags & 16u) == 0u) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); return; }
    /* meilleur rendu, vu de loin : flou angulaire (gaia_fiable.glsl) */
    if ((pc.cellBase & GF_MODE_RENDU) != 0u && (flags & 32u) == 0u) pos = gfFlou(pos, uint(gl_VertexIndex), gfPoidsLoin(pc.camHi.xyz + pc.camLo.xyz, pos));
    /* orbite pas fiable (drapeau 2 absent) : montrée seulement autour d'aujourd'hui (gaia_fiable.glsl) */
    float garde = (flags & 34u) != 0u ? 1.0 : gfEffacement(pc.par.w);      /* 2 : orbite fiable ; 32 : galaxie voisine */
    if (garde < 1.0e-4) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); return; }
    uvec2 q = (pc.par.z != 0.0 || (flags & 52u) != 0u) ? vel[gl_VertexIndex] : uvec2(0u);      /* 16 : composante du modèle (vieillissement) */
    vec3 voisineBase = vec3(0.0);
    float gainFilm = 1.0;      /* facteur de lumière quand le film mène et que Gaia s'éteint (revue F1) */
    bool voisine = (flags & 32u) != 0u;
    if (voisine) {
        /* étoile d'une galaxie VOISINE (Andromède, Triangle, Nuages) : la galaxie se déplace en bloc le long de son centre de
           référence (centres_reference.h) ; l'étoile tourne autour de ce centre, sur un cercle, à la vitesse de rotation
           mesurée de sa galaxie au rayon où elle est (rotation solide au centre, plate au-delà) [modèle : pas d'agitation,
           pas de marées]. Rang de la galaxie : 4e entier de la vitesse. */
        GalVoisine G = voisines[uint(int(q.y) >> 16) & 15u];
        vec3 rel = pos - G.c0.xyz, a = G.axe.xyz;
        float along = dot(rel, a);
        float Rkpc = length(rel - along * a) / OG_KPC_LY;
        float w = G.axe.w * min(Rkpc / max(G.rr.x, 1e-3), 1.0) / max(Rkpc, 1e-3) * OG_K;      /* rad/Ga */
        /* agitation : chaque étoile tourne un peu plus ou moins vite (écart tiré de sa graine, écart type = agitation mesurée
           / vitesse de rotation, G.rr.y) ; sans elle, la rotation différentielle enroulerait tout en anneaux serrés */
        float u1 = gvUnif(uint(gl_VertexIndex) * 7u + 1u), u2 = gvUnif(uint(gl_VertexIndex) * 7u + 2u);
        w *= 1.0 + G.rr.y * sqrt(-2.0 * log(u1)) * cos(6.2831853 * u2);
        float ang = w * pc.par.w;
        rel = rel * cos(ang) + cross(a, rel) * sin(ang) + a * along * (1.0 - cos(ang));
        if (G.rr.z > 0.5) {
            /* le film du Groupe local couvre la date : l'étoile est là où le calcul unique l'a emportée, par rapport au centre
               de sa galaxie (état donné par l'appli, film_etoiles.h) ; plus de bloc rigide, les marées se voient */
            Etat e = orb[gl_VertexIndex];
            rel = OG_M * (e.p.xyz + pc.frac * 1.0e-3 * OP_K * e.v.xyz) * OG_KPC_LY;
            if (e.v.w > 0.0) gainFilm = e.v.w;
        }
        voisineBase = G.ct.xyz;
        pos = rel;
    }
    if (pc.par.z != 0.0 && !voisine) {
        vec3 v = vec3(float(int(q.x << 16) >> 16), float(int(q.x) >> 16), float(int(q.y << 16) >> 16)) * 0.05;
        /* ligne droite mesurée, raccordée sans seuil à l'orbite calculée autour de la Galaxie (orbite_galactique.glsl) ;
           sans vitesse radiale mesurée (drapeau), elle compte pour nulle : l'étoile ne s'éloigne ni ne s'approche du Soleil
           au départ [supposé, dit à l'écran] */
        if (pc.par.w == 0.0) move = v * pc.par.z;
        else if (pc.exact > 0.5) {
            /* orbite exacte : état calculé au dernier pas d'un million d'années, prolongé au second ordre jusqu'à la date ;
               raccord sans seuil avec la ligne droite mesurée, comme etoiles_orbite.vert */
            float u = pc.par.w * 1.0e9 / OG_RACCORD_ANS, w = 1.0 - exp(-u * u);
            float tEtat = pc.par.w - pc.frac * 1.0e-3, h = pc.frac * 1.0e-3 * OP_K;
            Etat a = orb[gl_VertexIndex], s = orb[pc.sun];
            if ((flags & 16u) != 0u && a.v.w > 0.0) gainFilm = a.v.w;      /* film : lumière que Gaia, éteint, ne porte plus (film_etoiles.h) */
            vec3 xa = a.p.xyz + h * a.v.xyz + 0.5 * h * h * accGal(a.p.xyz, tEtat);
            vec3 xs = s.p.xyz + h * s.v.xyz + 0.5 * h * h * accGal(s.p.xyz, tEtat);
            if ((flags & 16u) != 0u && voisines[5].c0.w > 0.5) xs = voisines[5].c0.xyz;      /* étoile du modèle : Soleil de l'appli (gaia.h, setSunGalacto) */
            move = mix(v * pc.par.z, OG_M * (xa - xs) * OG_KPC_LY - pos, w);
        } else move = ogDeplacement(pos, v, pc.par.z, pc.par.w);      /* épicycles, le temps que le calcul exact rattrape */
    }
    vec3 p = voisine ? ((voisineBase - pc.camHi.xyz) + pos) - pc.camLo.xyz : ((pos - pc.camHi.xyz) + move) - pc.camLo.xyz;
    /* copie Gaia de l'étoile suivie : cachée près de sa place exacte (elle est dessinée par etoiles_orbite.vert) */
    if (pc.hide.w > 0.0 && !voisine && (flags & 16u) == 0u && length(p - pc.hide.xyz) < pc.hide.w) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); return; }
    float part = 1.0;
    if ((flags & 16u) != 0u) {
        uint k = uint(gl_InstanceIndex) % GV_SOUS_NUAGE, graine = uint(gl_VertexIndex) * GV_SOUS_NUAGE + k;
        part = replie ? 1.0 : GV_PART[(k + uint(gl_VertexIndex)) % GV_SOUS_NUAGE];      /* replié : toute la lumière du traceur */
        float ouvert = replie ? 0.0 : smoothstep(GV_LOIN, GV_PRES, length(p));
        if (ouvert > 0.0) {
            /* point dans une boule aplatie (disque : épaisseur moitié) : direction et rayon tirés de la graine */
            float u1 = gvUnif(graine * 3u), u2 = gvUnif(graine * 3u + 1u), u3 = gvUnif(graine * 3u + 2u);
            float cz = 2.0 * u1 - 1.0, phi = 6.2831853 * u2, rr = GV_RAYON * pow(u3, 1.0 / 3.0);
            vec3 dir = vec3(sqrt(1.0 - cz * cz) * cos(phi), sqrt(1.0 - cz * cz) * sin(phi), 0.5 * cz);
            p += ouvert * rr * dir;
        }
    }
    float d = max(length(p), 1e-12);
    float m = unpackHalf2x16(r.w).x + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0;
    uint pas = (r.w >> 16) & 255u;
    /* éclat rééquilibré vu de loin (gaia_fiable.glsl) : HYPOTHÈSE, décalage en millièmes de magnitude */
    if ((flags & 4u) != 0u && (pc.cellBase & GF_MODE_RENDU) != 0u) m += gfPoidsLoin(pc.camHi.xyz + pc.camLo.xyz, pos) * 0.001 * float(int(q.y) >> 16);
    float flux = pc.par.x * pow(10.0, -0.4 * m) * garde * part * gainFilm;
    /* vieillissement de la lumière (étoiles du MODÈLE) : facteurs par composante à la date montrée, 1 aujourd'hui
       (MIST v1.2, Kroupa, histoires de formation supposées, naines blanches non comptées ; gaia.h, setAgeing) */
    float fT = 1.0;
    if ((flags & 16u) != 0u) {
        uint comp = (uint(int(q.y) >> 16) >> 4) & 15u;
        flux *= gvCase(voisines[6], comp);
        fT = gvCase(voisines[7], comp);
    }
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    /* étoile du MODÈLE : tache bornée à 2,5 pixels (lumière inchangée : elle est divisée par la surface de la tache). Un
       traceur porte la lumière de nombreuses étoiles : vu de loin avec l'éclat multiplié, il ne doit pas devenir une grosse
       tache qu'aucune étoile réelle ne ferait. */
    if ((flags & 16u) != 0u) size = min(size, 2.5 * pc.par.y / 1080.0);
    vec3 teinte = colorOf[pas].rgb;
    if (fT > 0.0 && abs(fT - 1.0) > 1e-4) teinte *= gvCorpsNoir(5800.0 * fT) / gvCorpsNoir(5800.0);      /* teinte décalée comme la température */
    vCol = teinte * min(flux, 3.0e4) / (size * size);
    /* étoile du MODÈLE (drapeau 16) : poussière entre la caméra et l'étoile, dans la carte 3D (repère galactocentrique,
       ±16 kpc, ±2 kpc ; hors de la carte : rien). Rougissement : A_R = 0,75 A_V, A_B = 1,32 A_V (loi de Cardelli et al.
       1989, R_V = 3,1, aux longueurs d'onde moyennes des trois couleurs de l'écran) [approché]. */
    if ((flags & 16u) != 0u && !voisine && (pc.cellBase & GF_POUSSIERE) != 0u) {      /* galaxies voisines : hors de la carte de poussière */
        vec3 ga = transpose(OG_M) * (pc.camHi.xyz + pc.camLo.xyz) / OG_KPC_LY + OG_SOLEIL_POS;
        vec3 gb = transpose(OG_M) * (pos + move) / OG_KPC_LY + OG_SOLEIL_POS;
        const vec3 lo = vec3(-16.0, -16.0, -2.0), span = vec3(32.0, 32.0, 4.0);
        float av = 0.0, segPc = length(gb - ga) * 1000.0 / 16.0;
        for (int i = 0; i < 16; ++i) {
            vec3 uvw = (mix(ga, gb, (float(i) + 0.5) / 16.0) - lo) / span;
            av += texture(dust, uvw).g * segPc;      /* bord transparent : hors de la carte, pas de poussière */
        }
        vCol *= pow(vec3(10.0), -0.4 * av * vec3(0.75, 1.0, 1.32));
    }
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
