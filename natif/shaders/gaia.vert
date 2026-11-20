#version 450
#extension GL_GOOGLE_include_directive : require
/* Étoiles Gaia DR3 et étoiles du modèle (gaia.h). En-tête, tampons et partie propre à chaque étoile : gaia_corps.glsl. */
#define GV_CACHE_ACCES readonly
#define GV_PUSH_SUITE
#include "gaia_corps.glsl"
layout(location = 0) out vec3 vCol;
/* Étoile par étoile : la partie propre à l'étoile (gvTraceur), lue dans le cache pour les étoiles du MODÈLE quand il est à
   jour (gaia_traceur.comp, une fois par image), puis la partie propre à chaque étoile du sous-nuage (place dans la boule,
   part de lumière, tache). */
void horsChamp() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); }
void main() {
    uint idx = uint(gl_VertexIndex);
    uvec4 r = star[idx];
    uint flags = r.w >> 24;
    /* étoiles mesurées : une seule instance ; les autres instances du dessin (sous-nuages du modèle) ne les concernent pas */
    /* sous-nuage replié (gaia.h, selectLeaves : feuille trop loin pour le distinguer) : une seule instance, d'indice GV_SOUS_NUAGE */
    bool replie = uint(gl_InstanceIndex) >= GV_SOUS_NUAGE;
    if (gl_InstanceIndex > 0 && !replie && (flags & 16u) == 0u) { horsChamp(); return; }
    bool voisine = (flags & 32u) != 0u;
    vec3 p, teinte, poussiere = vec3(1.0);
    float garde = 1.0, gainFilm = 1.0, mDec = 0.0, fAge = 1.0, facteur = 1.0;
    bool lu = (flags & 16u) != 0u && (pc.cellBase & GV_CACHE) != 0u;
    if (lu) {
        vec4 c0 = cache[2u * idx], c1 = cache[2u * idx + 1u];
        if (c1.w < 0.0) { horsChamp(); return; }      /* effacée */
        p = c0.xyz; mDec = c0.w; teinte = c1.rgb; facteur = c1.w;
    } else if (!gvTraceur(idx, r, flags, p, garde, gainFilm, mDec, fAge, teinte, poussiere)) { horsChamp(); return; }
    /* copie Gaia de l'étoile suivie : cachée près de sa place exacte (elle est dessinée par etoiles_orbite.vert) */
    if (pc.hide.w > 0.0 && !voisine && (flags & 16u) == 0u && length(p - pc.hide.xyz) < pc.hide.w) { horsChamp(); return; }
    float part = 1.0;
    if ((flags & 16u) != 0u) {
        uint k = uint(gl_InstanceIndex) % GV_SOUS_NUAGE, graine = idx * GV_SOUS_NUAGE + k;
        part = replie ? 1.0 : GV_PART[(k + idx) % GV_SOUS_NUAGE];      /* replié : toute la lumière du traceur */
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
    if ((flags & 4u) != 0u && (pc.cellBase & GF_MODE_RENDU) != 0u) m += mDec;      /* éclat rééquilibré vu de loin (gvTraceur) */
    float flux;
    if (lu) flux = pc.par.x * pow(10.0, -0.4 * m) * part * facteur;      /* facteur : effacement × gain du film × vieillissement */
    else {
        flux = pc.par.x * pow(10.0, -0.4 * m) * garde * part * gainFilm;
        if ((flags & 16u) != 0u) flux *= fAge;      /* vieillissement de la lumière (étoiles du MODÈLE) */
    }
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    /* étoile du MODÈLE : tache bornée à 2,5 pixels (lumière inchangée : elle est divisée par la surface de la tache). Un
       traceur porte la lumière de nombreuses étoiles : vu de loin avec l'éclat multiplié, il ne doit pas devenir une grosse
       tache qu'aucune étoile réelle ne ferait. */
    if ((flags & 16u) != 0u) size = min(size, 2.5 * pc.par.y / 1080.0);
    vCol = teinte * min(flux, 3.0e4) / (size * size);
    if (!lu) vCol *= poussiere;      /* lu dans le cache : la poussière est déjà dans la teinte */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
