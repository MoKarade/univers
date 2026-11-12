#version 450
/* Lumière additionnée des sources Gaia à distance mal mesurée (gaia.h, gaia_agrege.bin). Deux usages, choisis par
   pc.camLo.w :
   0 : cases 3D (morceau de ciel × tranche de parallaxe), placées à leur distance, étalées sur leur taille à l'écran ;
   1 : ciel seul (distance inconnue), dessiné comme vu du Soleil : direction seulement, flux mesuré tel quel. */
struct Cell { vec4 pm; vec4 rest; };      /* x, y, z (al), magnitude ; rayon (al ou rad), erreur, couleur (bits), nombre (bits) */
layout(std430, set = 0, binding = 0) readonly buffer Cells { Cell cell[]; };
layout(std430, set = 0, binding = 2) readonly buffer Col { vec4 colorOf[]; };      /* binding 1 : vitesses des étoiles, inutile ici */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 camHi; vec4 camLo; vec4 par; } pc;   /* par.w : tan(champ / 2) */
layout(location = 0) out vec3 vCol;
const float LY_PER_PC = 3.2615638;
const int SPREAD = 8;          /* points par case (gaia.h dessine SPREAD instances) */
const float OVERLAP = 2.5;     /* tache plus large que la case : les cases voisines se recouvrent, pas de trous entre elles */
void main() {
    Cell c = cell[gl_VertexIndex];
    float pxPerRad = pc.par.y / (2.0 * pc.par.w);
    vec3 p;
    float flux, ext;
    if (pc.camLo.w == 0.0) {
        /* la case couvre un dixième de décade en parallaxe : sa lumière est répartie en SPREAD points également espacés
           (en log) sur cette épaisseur, au lieu d'un seul point au milieu (sinon : des coquilles autour du Soleil) */
        float s = pow(10.0, ((float(gl_InstanceIndex) + 0.5) / float(SPREAD) - 0.5) * 0.1);
        p = (c.pm.xyz * s - pc.camHi.xyz) - pc.camLo.xyz;
        float d = max(length(p), 1e-12);
        flux = pc.par.x * pow(10.0, -0.4 * (c.pm.w + 2.5 * log(float(SPREAD)) / log(10.0) + 5.0 * log(d / LY_PER_PC) / log(10.0) - 5.0));
        ext = OVERLAP * c.rest.x * s / d * pxPerRad;
    } else {
        p = c.pm.xyz;                          /* direction seule */
        flux = pc.par.x * pow(10.0, -0.4 * c.pm.w);
        ext = 2.0 * OVERLAP * c.rest.x * pxPerRad;      /* vu du Soleil, pixels du ciel jointifs : recouvrement plus large */
    }
    float size = clamp(max(1.5 * pc.par.y / 1080.0, ext), 1.0, 512.0);
    vCol = colorOf[floatBitsToUint(c.rest.z) & 255u].rgb * flux / (size * size);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = size;
}
