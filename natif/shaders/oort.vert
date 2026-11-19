#version 450
/* Nuage d'Oort : MODÈLE (structures.h, oortModel). Chaque comète suit son ellipse képlérienne autour du Soleil ; sa place
   à la date montrée est calculée ici (équation de Kepler, méthode de Newton). Pas de marée galactique ni d'étoile qui passe. */
layout(location = 0) in vec4 inA;      /* a (UA), e, inclinaison, nœud ascendant (rad) */
layout(location = 1) in vec4 inB;      /* argument du périhélie, anomalie moyenne à J2000 (rad), mouvement moyen (rad/an), - */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;   /* par : part montrée, hauteur (px), années depuis J2000, al par UA */
layout(location = 0) out vec3 vCol;
void main() {
    float a = inA.x, e = inA.y, inc = inA.z, node = inA.w, w = inB.x;
    float M = mod(inB.y + inB.z * pc.par.z, 6.2831853);
    float E = e < 0.8 ? M : 3.14159265;
    for (int k = 0; k < 10; ++k) E -= (E - e * sin(E) - M) / (1.0 - e * cos(E));
    float xo = a * (cos(E) - e), yo = a * sqrt(1.0 - e * e) * sin(E);      /* dans le plan de l'orbite, UA */
    float cw = cos(w), sw = sin(w), cn = cos(node), sn = sin(node), ci = cos(inc), si = sin(inc);
    vec3 r = vec3((cn * cw - sn * sw * ci) * xo + (-cn * sw - sn * cw * ci) * yo,
                  (sn * cw + cn * sw * ci) * xo + (-sn * sw + cn * cw * ci) * yo,
                  (sw * si) * xo + (cw * si) * yo);      /* écliptique J2000 */
    vec3 p = r * pc.par.w - pc.cam.xyz;      /* années-lumière, depuis la caméra */
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = max(1.0, 1.2 * pc.par.y / 1080.0);
    /* repère, pas de la lumière (une comète du nuage est bien trop faible pour être vue) : bleu glacé, même éclat pour toutes */
    vCol = vec3(0.55, 0.75, 1.0) * 0.035 * pc.par.x;
}
