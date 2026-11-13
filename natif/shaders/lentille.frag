#version 450
/* Déviation de la lumière par la gravité (lentille.h). Pour chaque pixel : direction de vue d ; pour chaque masse proche de
   la ligne de visée, on remonte le rayon jusqu'à la direction d'où vient la lumière s, puis on lit l'image non déviée en s.
   - champ faible (Soleil, planètes, et trous noirs loin du bord) : angle de déviation exact de la relativité générale pour
     une source à l'infini, alpha = (2 G M / c² D) (1 + cos chi) / sin chi (la formule qu'utilise Gaia) ;
   - trou noir (Schwarzschild) près de son bord : table calculée sur le processeur en suivant chaque rayon (lentille.h) ;
     rayon capturé : noir (l'ombre).
   Les pixels sur le disque d'un astre (Soleil, planète) ne sont pas déviés : c'est l'astre lui-même. */
layout(set = 0, binding = 0) uniform sampler2D scene;
layout(std430, set = 0, binding = 1) readonly buffer Tables { float defl[]; };   /* nTable déviations par trou noir */
struct L { vec4 dir; vec4 par; };      /* dir : direction (caméra) et genre (0 faible, 1 trou noir) ; par : (2GM/c²D, angle du disque, début de table, chi max) */
layout(push_constant) uniform Pc { vec4 cam; L lens[6]; } pc;   /* cam : tan(champ/2), largeur/hauteur, nombre de masses, points par table */
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 o;

void main() {
    float th = pc.cam.x, asp = pc.cam.y;
    int n = int(pc.cam.z), nt = int(pc.cam.w);
    vec3 d = normalize(vec3((2.0 * uv.x - 1.0) * th * asp, (1.0 - 2.0 * uv.y) * th, 1.0));
    for (int k = 0; k < n; ++k) {
        vec3 l = pc.lens[k].dir.xyz;
        vec3 c = cross(d, l);
        float sinc = length(c), cosc = dot(d, l);
        float chi = atan(sinc, cosc);
        if (chi < pc.lens[k].par.y) continue;                 /* sur le disque de l'astre */
        if (sinc < 1e-12) continue;
        vec3 p = normalize(d - cosc * l);                    /* perpendiculaire à l, du côté de d */
        float alpha;
        if (pc.lens[k].dir.w > 0.5 && chi < pc.lens[k].par.w) {
            float x = chi / pc.lens[k].par.w * float(nt - 1);
            int i = int(floor(x));
            int base = int(pc.lens[k].par.z);
            float a0 = defl[base + min(i, nt - 1)], a1 = defl[base + min(i + 1, nt - 1)];
            if (a0 < 0.0 || a1 < 0.0) { o = vec4(0.0, 0.0, 0.0, 1.0); return; }      /* capturé : l'ombre */
            alpha = mix(a0, a1, x - float(i));
        } else {
            alpha = pc.lens[k].par.x * (1.0 + cosc) / sinc;
        }
        float g = chi - alpha;                               /* angle entre la source et la masse */
        d = cos(g) * l + sin(g) * p;
    }
    if (d.z <= 1e-6) { o = vec4(0.0, 0.0, 0.0, 1.0); return; }      /* la lumière vient de derrière la caméra : pas dans l'image */
    vec2 s = vec2(0.5 + 0.5 * d.x / (d.z * th * asp), 0.5 - 0.5 * d.y / (d.z * th));
    if (any(lessThan(s, vec2(0.0))) || any(greaterThan(s, vec2(1.0)))) { o = vec4(0.0, 0.0, 0.0, 1.0); return; }
    o = vec4(texture(scene, s).rgb, 1.0);
}
