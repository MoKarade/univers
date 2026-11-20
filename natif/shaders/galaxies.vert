#version 450
/* Galaxies et quasars des relevés : direction mesurée, décalage vers le rouge mesuré. La distance est lue dans une
   table calculée par l'appli d'après la cosmologie choisie (cosmologie.h) : changer un paramètre déplace tous les
   points à l'image suivante. Éclat : même loi que les étoiles et les galaxies de forme mesurée (exposition, magnitude,
   1/d²) ; la magnitude de chaque point est TIRÉE (le catalogue n'a pas l'éclat propre), voir plus bas. */
layout(location = 0) in float inDx;
layout(location = 1) in float inDy;
layout(location = 2) in float inDz;
layout(location = 3) in float inZ;
layout(location = 4) in vec4 inCol;
layout(set = 0, binding = 0) uniform Table { vec4 d[65]; } table;      /* 257 distances en années-lumière, pas égaux en ln(1 + z) */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;   /* par : exposition (celle des étoiles), hauteur en pixels, 1 / ln(1 + zMax), distance de vue (al) ; cam.w : pose propre aux galaxies (galaxies_pose.h) */
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
       SDSS ; la même pour tous les relevés [supposé]) ; graine = rang de la galaxie. Quasars : magnitude
       apparente 20 pour tous, ordre de grandeur des quasars SDSS DR16Q [supposé, À vérifier]. */
    float dSol = mix(a, b, u - float(k)) * (1.0 + inZ);      /* distance de luminosité (al) */
    float DM = 5.0 * log(max(dSol, 1.0) / 32.615638) / log(10.0);
    const float MSTAR = -21.30, MLIM = 17.7;
    float xlim = pow(10.0, -0.4 * (MLIM - DM - MSTAR));      /* L / L* la plus faible encore vue */
    uint hs = uint(gl_VertexIndex) * 2654435761u; hs ^= hs >> 15; hs *= 0x2c1b3c6du; hs ^= hs >> 12;
    float r1 = (float(hs & 0xffffu) + 0.5) / 65536.0, r2 = (float(hs >> 16) + 0.5) / 65536.0;
    float x;
    if (xlim >= 1.0) { x = xlim - log(r1); }      /* queue exponentielle au-delà de L* */
    else {      /* loi en L^-1 de xlim à 1, puis queue exponentielle (poids des deux morceaux) */
        float a1 = log(1.0 / xlim) * 0.6065, a2 = 0.2194;
        float p1 = a1 / (a1 + a2);
        x = r2 < p1 ? pow(xlim, 1.0 - r1) : 1.0 - log(r1);
    }
    /* Magnitude absolue r tirée : M = M* - 2,5 log10(L/L*) [supposé, voir plus haut]. Vue de la caméra : distance de
       luminosité depuis le Soleil, puis 1/d² entre le Soleil et la caméra (distance comobile), comme galaxie_formes.vert.
       Pas de correction K ni d'évolution de la lumière avec z [supposé]. */
    float mApp = inCol.a > 0.99 ? 20.0 : MSTAR - 2.5 * log(x) / log(10.0) + DM;
    float dCom = max(mix(a, b, u - float(k)), 1.0);
    float dc = max(length(p), 1.0);
    float flux = pc.par.x * pow(10.0, -0.4 * mApp) * (dCom / dc) * (dCom / dc);
    /* taille d'après l'éclat SANS la longue pose : mêmes points qu'avant, donc même coût pour la carte */
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 6.0) * pc.par.y / 1080.0;
    /* Longue pose propre aux galaxies (galaxies_pose.h), pleine jusqu'à 1,5 fois la distance de vue, puis qui s'efface
       jusqu'à 4 fois : sans quoi les millions de galaxies du SDSS, loin derrière le point regardé, faisaient un brouillard
       orange sur toute la vue de Laniakea (capture du 20/11). Au-delà, éclat réel sous la pose des étoiles. */
    float fondu = smoothstep(1.5 * pc.par.w, 4.0 * pc.par.w, dc);
    flux *= pow(max(pc.cam.w, 1.0), 1.0 - fondu);
    vec3 c = pow(inCol.rgb, vec3(2.2));      /* couleurs de la page (valeurs d'écran) ramenées en lumière linéaire */
    c /= max(max(c.r, c.g), max(c.b, 1e-4));      /* teinte seule, de plus grande composante 1 (comme couleurT des galaxies de forme) */
    vCol = c * min(flux, 3.0e4) / (size * size);      /* même énergie quelle que soit la taille du point */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
