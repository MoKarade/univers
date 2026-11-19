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
    vec3 col = kind == 1 ? vec3(0.30, 0.62, 1.00) : kind == 2 ? vec3(0.70, 0.40, 1.00) : kind == 3 ? vec3(0.60, 0.35, 0.95) : vec3(0.50, 0.30, 0.85);
    /* les vides sont très nombreux et se superposent : beaucoup plus discrets que l'unique frontière de Laniakea */
    float k = kind == 1 ? 1.0 : kind == 2 ? 0.30 : kind == 3 ? 0.10 : 0.12;
    float fill = kind == 1 ? 0.006 : 0.0005;
    /* on généralise en s'éloignant : ce qui est bien plus loin que l'échelle regardée (cam.w) s'estompe */
    float far = 1.0 / (1.0 + pow(d / (3.0 * pc.cam.w), 2.0));
    o = vec4(col * k * pc.par.x * far * (fill + 0.06 * rim), 1.0);
}
