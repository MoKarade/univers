#version 450
/* Voile transparent : presque rien de face, plus vif là où la surface est vue de biais (le contour d'une bulle), pour que
   la forme en 3D se lise sans cacher les galaxies derrière. Couleur par genre : 1 Laniakea (bleu), 2 à 4 vides (violet,
   plus pâle en s'éloignant : la forme y est de plus en plus généralisée). */
layout(location = 0) in vec3 vRel;
layout(location = 1) in vec3 vNor;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;
layout(location = 0) out vec4 o;
void main() {
    float d = length(vRel);
    float c = abs(dot(normalize(vNor), vRel / max(d, 1.0)));
    float rim = pow(1.0 - c, 3.0);
    int kind = int(pc.par.w + 0.5);
    /* 5 superamas du catalogue SDSS (orange), 6 superstructures nommées (or), 7 bord de l'univers observable (blanc bleuté),
       8 surface d'émission du fond diffus cosmologique (rouge orangé) : superstructures_bin.py */
    vec3 col = kind == 1 ? vec3(0.30, 0.62, 1.00) : kind == 2 ? vec3(0.70, 0.40, 1.00) : kind == 3 ? vec3(0.60, 0.35, 0.95) : kind == 4 ? vec3(0.50, 0.30, 0.85)
             : kind == 5 ? vec3(1.00, 0.55, 0.20) : kind == 6 ? vec3(1.00, 0.80, 0.30) : kind == 7 ? vec3(0.75, 0.85, 1.00) : vec3(1.00, 0.45, 0.25);
    /* les vides sont très nombreux et se superposent : beaucoup plus discrets que l'unique frontière de Laniakea */
    float k = kind == 1 ? 1.0 : kind == 2 ? 0.30 : kind == 3 ? 0.10 : kind == 4 ? 0.12 : kind == 5 ? 0.10 : kind == 6 ? 0.45 : 1.0;
    float fill = kind == 1 ? 0.006 : kind >= 7 ? 0.004 : 0.0005;
    /* on généralise en s'éloignant : ce qui est bien plus loin que l'échelle regardée (cam.w) s'estompe ; les deux sphères
       de l'univers observable n'ont de sens que vues de très loin : elles apparaissent quand l'échelle regardée dépasse
       quelques milliards d'années-lumière */
    float far = kind >= 7 ? smoothstep(2.0e9, 2.0e10, pc.cam.w) : 1.0 / (1.0 + pow(d / (3.0 * pc.cam.w), 2.0));
    o = vec4(col * k * pc.par.x * far * (fill + 0.06 * rim), 1.0);
}
