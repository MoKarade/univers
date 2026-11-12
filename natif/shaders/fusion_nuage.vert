#version 450
/* Étoiles du calcul de la rencontre avec Andromède (fusion_nuage.h) : deux images du calcul (avant et après la date
   montrée, 20 millions d'années d'écart), en kpc par rapport au centre de la Voie lactée ; ligne droite entre les deux.
   Éclat : comme une étoile mesurée (etoiles.vert) quand la particule a une magnitude absolue (masse de la particule
   divisée par le rapport masse/lumière sourcé de sa galaxie) : même loi en 1/d², même exposition, donc même échelle de
   lumière que les étoiles mesurées. Sans rapport masse/lumière sourcé : éclat d'affichage fixe (par.z), dit à l'écran.
   origine : centre de la Voie lactée par rapport à la caméra (années-lumière) ; origine.w : part du pas écoulée.
   par : exposition, hauteur en pixels, éclat fixe (0 : éclat physique), part montrée (0 à 1). */
layout(location = 0) in vec3 inA;
layout(location = 1) in vec3 inB;
layout(location = 2) in float inMag;
layout(location = 3) in vec4 inCol;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 origine; vec4 par; } pc;
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
const float KPC_LY = 3261.5637769;
/* Repère galactocentrique -> écliptique (colonnes de la matrice M_GAL2ECL de la page), comme etoiles_orbite.vert. */
const mat3 M = mat3(-0.0548756577, -0.993821367, -0.0964766946,
                    0.4941094372, -0.1109908412, 0.8622858559,
                    -0.8676661376, -0.0003515418, 0.4971472117);
void main() {
    vec3 p = M * mix(inA, inB, pc.origine.w) * KPC_LY + pc.origine.xyz;
    float d = max(length(p), 1e-12);
    float flux = pc.par.z * pc.par.w;
    if (pc.par.z == 0.0) {
        float m = inMag + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0;
        flux = pc.par.x * pc.par.w * pow(10.0, -0.4 * m);
    }
    float size = clamp(1.5 + 1.2 * log2(1.0 + flux), 1.5, 14.0) * pc.par.y / 1080.0;
    vCol = inCol.rgb * min(flux, 3.0e4) / (size * size);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
