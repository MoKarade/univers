#version 450
/* Nébuleuses (nebuleuses.h, pipeline/natif/nebuleuses.py) : une tache ronde par nébuleuse, à sa place et de sa taille
   MESURÉES (distance publiée, rayon publié ou étendue des lignes de visée), tournée vers la caméra. */
layout(location = 0) in vec4 inPR;      /* x, y, z, rayon (années-lumière, écliptique J2000, centre : Soleil) */
layout(location = 1) in uvec4 inG;      /* x : genre (1 nébuleuse planétaire, 2 nuage moléculaire) */
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;   /* cam.xyz : caméra (al) ; par : part montrée, hauteur (px), pixels par radian, genre dessiné */
layout(location = 0) out float vPart;
void main() {
    vec3 p = inPR.xyz - pc.cam.xyz;
    float d = max(length(p), 1e-3);
    float px = inPR.w / d * pc.par.z;      /* rayon à l'écran (pixels) */
    bool genre = inG.x == uint(pc.par.w + 0.5);
    gl_Position = pc.viewProj * vec4(p, 1.0);
    gl_PointSize = genre && px >= 0.75 && d > inPR.w ? min(2.0 * px, 2048.0) : 0.0;      /* caméra dans la nébuleuse : pas de tache */
    /* s'efface quand elle devient plus petite que 2 pixels (rien à voir) et quand la caméra s'en approche à moins de 3 rayons */
    vPart = pc.par.x * smoothstep(0.75, 2.0, px) * smoothstep(1.0, 3.0, d / inPR.w);
}
