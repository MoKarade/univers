/* Mouvement d'une étoile autour du centre de la Galaxie, à toute date : le même calcul que src/orbite_galactique.h
   (lire ce fichier pour le pourquoi et les limites), écrit pour la carte graphique.
   Départ : position et vitesse MESURÉES. Ensuite : orbite CALCULÉE par épicycles dans le potentiel [modèle] du fil
   physique (natif/physique/galaxie_orbites.h). Raccord sans seuil entre la ligne droite mesurée et l'orbite.
   essai_orbite.cpp contrôle que les constantes ci-dessous sont celles de la bibliothèque de physique.
   Unités internes : kpc, km/s, milliards d'années. */
const float OG_G = 4.30091e-6;
const float OG_MB = 0.5e10;
const float OG_AB = 0.5;
const float OG_MD = 6.8e10;
const float OG_AD = 3.0;
const float OG_BD = 0.28;
const float OG_RS = 16.0;
const float OG_GMH = 2552189.27458262;      /* halo calé sur 232,8 km/s au Soleil (phys::galaxie::gmHalo) */
const float OG_KL = 0.0031117906;           /* énergie noire : H0² ΩΛ en (km/s)²/kpc² (phys::galaxie::kLambdaKmsKpc2) */
const float OG_K = 1.0227121650456;         /* km/s/kpc -> radians par milliard d'années */
const float OG_KPC_LY = 3261.5637769;
const float OG_RACCORD_ANS = 3.0e5;
const float OG_AMP_MAX = 0.8;
const vec3 OG_SOLEIL_POS = vec3(-8.19999344, 0.007980814, 0.006606248);      /* kpc : -R0 x direction du centre */
const vec3 OG_SOLEIL_VIT = vec3(11.1, 245.04, 7.25);                          /* km/s */
/* Repère galactocentrique -> écliptique (colonnes de la matrice M_GAL2ECL de la page). */
const mat3 OG_M = mat3(-0.0548756577, -0.993821367, -0.0964766946,
                       0.4941094372, -0.1109908412, 0.8622858559,
                       -0.8676661376, -0.0003515418, 0.4971472117);

/* Fréquences au rayon R (kpc) : x = vitesse circulaire, y = rotation, z = épicycle radial, w = vertical (km/s/kpc). */
vec4 ogFrequences(float R) {
    float gb = OG_G * OG_MB, gd = OG_G * OG_MD, c2 = (OG_AD + OG_BD) * (OG_AD + OG_BD), D2 = R * R + c2, D = sqrt(D2), x = R / OG_RS;
    float m = log(1.0 + x) - x / (1.0 + x);
    float d1 = gb / ((R + OG_AB) * (R + OG_AB)) + gd * R / (D2 * D) + OG_GMH * m / (R * R);
    float d2 = -2.0 * gb / ((R + OG_AB) * (R + OG_AB) * (R + OG_AB)) + gd * (c2 - 2.0 * R * R) / (D2 * D2 * D)
             + OG_GMH * (x / ((1.0 + x) * (1.0 + x) * OG_RS * R * R) - 2.0 * m / (R * R * R));
    float nu2 = gb / (R * (R + OG_AB) * (R + OG_AB)) + gd * (OG_AD + OG_BD) / (OG_BD * D2 * D) + OG_GMH * m / (R * R * R);
    /* énergie noire (revue O3) : même retrait que phys::galaxie::frequences, sinon la carte et le processeur divergent */
    d1 -= OG_KL * R; d2 -= OG_KL; nu2 -= OG_KL;
    float om2 = d1 / R;
    return vec4(sqrt(R * d1), sqrt(om2), sqrt(max(d2 + 3.0 * om2, 1e-6)), sqrt(max(nu2, 1e-6)));
}

float ogF(float u, float e, float q, float beta) {
    float E = u - 2.0 * atan(beta * sin(u), 1.0 + beta * cos(u));
    return E / (q * sqrt(q)) - e * sin(u) / (q * (1.0 + e * cos(u)));
}

/* Position galactocentrique (kpc) à tGa d'une étoile partie de g (kpc) à la vitesse v (km/s). */
vec3 ogEpicycle(vec3 g, vec3 v, float tGa) {
    float R = max(length(g.xy), 1e-6);
    float lz = g.x * v.y - g.y * v.x, sens = lz < 0.0 ? -1.0 : 1.0;
    float vR = dot(g.xy, v.xy) / R;
    float rg = R;
    for (int i = 0; i < 6; ++i) rg = max(abs(lz) / ogFrequences(rg).x, 0.05);
    vec4 f = ogFrequences(rg);
    float x = R - rg;
    float amp = sqrt(x * x + (vR / f.z) * (vR / f.z)), maxAmp = OG_AMP_MAX * rg;
    if (amp > maxAmp) { x *= maxAmp / amp; vR *= maxAmp / amp; }
    float a = min(amp, maxAmp), alpha = atan(-vR / f.z, x);
    float k = OG_K * tGa, psi = f.z * k + alpha;
    float Rt = rg + a * cos(psi);
    /* Angle autour du centre : moment cinétique conservé, intégrale exacte de Lz / R(t)^2 (voir orbite_galactique.h). */
    float e = a / rg, q = 1.0 - e * e, beta = e / (1.0 + sqrt(q));
    float phi = atan(g.y, g.x) + sens * (f.y / f.z) * (ogF(psi, e, q, beta) - ogF(alpha, e, q, beta));
    float z = g.z * cos(f.w * k) + v.z / f.w * sin(f.w * k);
    return vec3(Rt * cos(phi), Rt * sin(phi), z);
}

/* Déplacement (années-lumière, repère du simulateur centré sur le Soleil) depuis aujourd'hui.
   pos : position aujourd'hui (al) ; vel : vitesse mesurée par rapport au Soleil (km/s) ;
   droitAl : années x (al par an pour 1 km/s), comme avant ; tGa : milliards d'années depuis aujourd'hui. */
vec3 ogDeplacement(vec3 pos, vec3 vel, float droitAl, float tGa) {
    vec3 droit = vel * droitAl;
    float u = tGa * 1.0e9 / OG_RACCORD_ANS;
    float w = 1.0 - exp(-u * u);
    if (w < 1e-9) return droit;
    vec3 g = transpose(OG_M) * pos / OG_KPC_LY + OG_SOLEIL_POS;
    vec3 v = transpose(OG_M) * vel + OG_SOLEIL_VIT;
    vec3 e = ogEpicycle(g, v, tGa) - g;
    vec3 s = ogEpicycle(OG_SOLEIL_POS, OG_SOLEIL_VIT, tGa) - OG_SOLEIL_POS;
    return mix(droit, OG_M * (e - s) * OG_KPC_LY, w);
}
