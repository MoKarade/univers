#version 450
/* par.w : 1 = nébuleuse planétaire (repère lumineux, son éclat n'est pas dans les données : couleur fixe, bleu-vert de
   l'oxygène et rouge de l'hydrogène au bord) ; 2 = nuage moléculaire (poussière : assombrit ce qui est derrière, par
   multiplication ; opacité au centre supposée : la lumière y passe à 10 %). */
layout(location = 0) in float vPart;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;
layout(location = 0) out vec4 o;
void main() {
    vec2 q = gl_PointCoord * 2.0 - 1.0;
    float r2 = dot(q, q);
    if (r2 > 1.0) discard;
    float g = exp(-3.0 * r2) * (1.0 - r2);      /* profil doux, nul au bord du disque */
    if (pc.par.w < 1.5) {
        vec3 c = mix(vec3(0.25, 0.85, 0.80), vec3(0.95, 0.30, 0.35), smoothstep(0.3, 0.9, sqrt(r2)));
        o = vec4(c * 0.6 * g * vPart, 1.0);
    } else {
        float t = 1.0 - 0.9 * g * vPart;      /* transmission : 10 % au centre, soit A_V proche de 2,5 (supposé ; les cœurs des nuages proches dépassent souvent 5) */
        o = vec4(t, t, t, 1.0);
    }
}
