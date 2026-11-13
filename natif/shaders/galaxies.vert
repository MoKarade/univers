#version 450
/* Galaxies et quasars des relevés : direction mesurée, décalage vers le rouge mesuré. La distance est lue dans une
   table calculée par l'appli d'après la cosmologie choisie (cosmologie.h) : changer un paramètre déplace tous les
   points à l'image suivante. Chaque objet est un point de même éclat (son éclat propre n'est pas dans les données). */
layout(location = 0) in float inDx;
layout(location = 1) in float inDy;
layout(location = 2) in float inDz;
layout(location = 3) in float inZ;
layout(location = 4) in vec4 inCol;
layout(set = 0, binding = 0) uniform Table { vec4 d[65]; } table;      /* 257 distances en années-lumière, pas égaux en ln(1 + z) */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;   /* par : éclat, hauteur en pixels, 1 / ln(1 + zMax), taille du point */
layout(location = 0) out vec3 vCol;
void main() {
    /* galaxie dessinée par galaxies_formes.h (forme mesurée, particules) : 4e octet de couleur = 128 (galaxies_formes.py) */
    if (abs(inCol.a - 128.0 / 255.0) < 0.002) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); return; }
    float u = clamp(log(1.0 + inZ) * pc.par.z, 0.0, 1.0) * 256.0;
    int k = min(int(u), 255);
    float a = table.d[k >> 2][k & 3], b = table.d[(k + 1) >> 2][(k + 1) & 3];
    vec3 p = vec3(inDx, inDy, inDz) * mix(a, b, u - float(k)) - pc.cam.xyz;
    /* Éclat et taille SUPPOSÉS (le catalogue n'a que la direction et le décalage vers le rouge) : luminosité tirée de la
       fonction de luminosité de Schechter en bande r (Blanton et al. 2003 : M* = -20,44 + 5 log h, alpha = -1,05 ; h = 0,674),
       parmi les galaxies assez brillantes pour avoir été vues par le relevé (limite r = 17,7, celle du relevé principal du
       SDSS ; la même pour tous les relevés [supposé]) ; graine = rang de la galaxie. Éclat relatif à la moyenne de ces
       galaxies à cette distance (l'éclat d'ensemble des points ne change pas) ; taille proportionnelle à L^0,3 (relation
       taille-luminosité de Shen et al. 2003, disques). */
    float dSol = mix(a, b, u - float(k)) * (1.0 + inZ);      /* distance de luminosité (al) */
    float DM = 5.0 * log(max(dSol, 1.0) / 32.615638) / log(10.0);
    const float MSTAR = -21.30, MLIM = 17.7;
    float xlim = pow(10.0, -0.4 * (MLIM - DM - MSTAR));      /* L / L* la plus faible encore vue */
    uint hs = uint(gl_VertexIndex) * 2654435761u; hs ^= hs >> 15; hs *= 0x2c1b3c6du; hs ^= hs >> 12;
    float r1 = (float(hs & 0xffffu) + 0.5) / 65536.0, r2 = (float(hs >> 16) + 0.5) / 65536.0;
    float x, xm;
    if (xlim >= 1.0) { x = xlim - log(r1); xm = xlim + 1.0; }      /* queue exponentielle au-delà de L* */
    else {      /* loi en L^-1 de xlim à 1, puis queue exponentielle (poids des deux morceaux) */
        float a1 = log(1.0 / xlim) * 0.6065, a2 = 0.2194;
        float p1 = a1 / (a1 + a2);
        x = r2 < p1 ? pow(xlim, 1.0 - r1) : 1.0 - log(r1);
        xm = p1 * (1.0 - xlim) / max(log(1.0 / xlim), 1e-3) + (1.0 - p1) * 2.0;
    }
    float w = clamp(x / xm, 0.02, 50.0);
    float size = pc.par.w * clamp(pow(w, 0.3), 0.7, 2.5) * pc.par.y / 1080.0;
    /* au-delà de la distance pc.cam.w (liée à l'échelle de la vue), l'éclat apparent baisse comme l'inverse du carré de la
       distance, pour que le voisinage ne soit pas noyé par le lointain */
    float d = max(length(p), 1.0);
    float fade = min(1.0, (pc.cam.w * pc.cam.w) / (d * d));
    vCol = pow(inCol.rgb, vec3(2.2)) * pc.par.x * fade * w / (size * size);      /* couleurs de la page (valeurs d'écran) ramenées en lumière linéaire */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
