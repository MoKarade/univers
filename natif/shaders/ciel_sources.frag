#version 450
/* Cercle (anneau) autour de la direction de la source : on voit la carte au travers. */
layout(location = 0) in vec3 vCol;
layout(location = 0) out vec4 o;
void main() {
    float r = length(gl_PointCoord * 2.0 - 1.0);
    if (r > 1.0 || r < 0.70) discard;
    vec3 c = min(vCol, vec3(0.985));
    o = vec4(c / (1.0 - c), 1.0);      /* inverse de la compression de l'écran (ecran.frag) */
}
