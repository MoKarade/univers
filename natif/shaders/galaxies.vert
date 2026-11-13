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
    float size = pc.par.w * pc.par.y / 1080.0;
    /* Même éclat propre supposé pour toutes ; au-delà de la distance pc.cam.w (liée à l'échelle de la vue), l'éclat
       apparent baisse comme l'inverse du carré de la distance, pour que le voisinage ne soit pas noyé par le lointain. */
    float d = max(length(p), 1.0);
    float fade = min(1.0, (pc.cam.w * pc.cam.w) / (d * d));
    vCol = pow(inCol.rgb, vec3(2.2)) * pc.par.x * fade / (size * size);      /* couleurs de la page (valeurs d'écran) ramenées en lumière linéaire */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
