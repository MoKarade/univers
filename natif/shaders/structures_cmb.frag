#version 450
/* Surface d'émission du fond diffus cosmologique (genre 8 de superstructures.bin), avec la carte MESURÉE par Planck
   (SMICA, PR3 2018 : COM_CMB_IQU-smica_2048_R3.00_full, Planck Collaboration IV 2020), demande de Marc du 20/11/2026.
   La carte est lue dans ciel_cmb.bin et moyennée au chargement en Nside 256 (pixels de 14', structures.h). Pour chaque
   point de la sphère, la direction vue depuis le Soleil est tournée en coordonnées galactiques (repère de la carte), le
   pixel HEALPix emboîté est lu, et l'écart de température est montré en fausses couleurs (bleu froid, rouge chaud, ±300 µK).
   C'est une carte posée sur une sphère : en vraie lumière, ce rayonnement (micro-ondes) ne se voit pas à l'œil. */
layout(location = 0) in vec3 vRel;
layout(location = 1) in vec3 vNor;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 cam; vec4 par; } pc;
layout(std430, set = 0, binding = 0) readonly buffer Carte { float v[]; } carte;
layout(location = 0) out vec4 o;
const float PI = 3.14159265358979;
/* écliptique J2000 -> galactique : transposée de la matrice galactique -> écliptique de etoiles_orbite.vert */
const mat3 M = mat3(-0.0548756577, -0.993821367, -0.0964766946,
                    0.4941094372, -0.1109908412, 0.8622858559,
                    -0.8676661376, -0.0003515418, 0.4971472117);
uint spread(uint x) {      /* bits de x écartés d'un rang : 0b1011 -> 0b1000101 */
    x &= 0xFFFFu;
    x = (x | (x << 8)) & 0x00FF00FFu;
    x = (x | (x << 4)) & 0x0F0F0F0Fu;
    x = (x | (x << 2)) & 0x33333333u;
    x = (x | (x << 1)) & 0x55555555u;
    return x;
}

/* face (0 à 11) et coordonnées (ix, iy) dans la face du pixel HEALPix de Nside donné. Près des pôles, √(3(1−|z|)) est
   calculé comme √(3(x²+y²)/(1+|z|)) : même valeur, sans la perte de précision de 1−|z| en simple précision (pixels de
   quelques secondes d'arc dans les tuiles fines). */
ivec3 faceXY(int nside, vec3 d) {
    float z = d.z, za = abs(z);
    float phi = atan(d.y, d.x);
    if (phi < 0.0) phi += 2.0 * PI;
    float tt = phi / (0.5 * PI);
    int face, ix, iy;
    if (za <= 2.0 / 3.0) {
        float t1 = float(nside) * (0.5 + tt), t2 = float(nside) * z * 0.75;
        int jp = int(t1 - t2), jm = int(t1 + t2);
        int ifp = jp / nside, ifm = jm / nside;
        face = ifp == ifm ? (ifp | 4) : (ifp < ifm ? ifp : ifm + 8);
        ix = jm & (nside - 1);
        iy = nside - (jp & (nside - 1)) - 1;
    } else {
        int ntt = min(int(tt), 3);
        float tp = tt - float(ntt);
        float tmp = float(nside) * sqrt(3.0 * (d.x * d.x + d.y * d.y) / (1.0 + za));
        int jp = min(int(tp * tmp), nside - 1), jm = min(int((1.0 - tp) * tmp), nside - 1);
        if (z >= 0.0) { face = ntt; ix = nside - jm - 1; iy = nside - jp - 1; }
        else { face = ntt + 8; ix = jp; iy = jm; }
    }
    return ivec3(face, ix, iy);
}

uint ang2pixNest(int nside, vec3 d) {
    ivec3 f = faceXY(nside, d);
    return uint(f.x) * uint(nside) * uint(nside) + spread(uint(f.y)) + 2u * spread(uint(f.z));
}

vec3 palette(float t) {      /* t de -1 (froid) à 1 (chaud) : bleu, blanc cassé, rouge, comme les cartes de Planck */
    vec3 cold = vec3(0.10, 0.25, 0.85), mid = vec3(0.95, 0.90, 0.80), hot = vec3(0.90, 0.20, 0.05);
    return t < 0.0 ? mix(mid, cold, -t) : mix(mid, hot, t);
}
void main() {
    vec3 w = vRel + pc.cam.xyz;                      /* point de la sphère, années-lumière depuis le Soleil */
    bool outside = dot(pc.cam.xyz, pc.cam.xyz) > dot(w, w);
    if (outside && dot(vNor, vRel) > 0.0) discard;   /* vue de dehors : seule la face tournée vers la caméra (pas de double carte) */
    vec3 dg = transpose(M) * normalize(w);
    float dT = carte.v[ang2pixNest(256, dg)];        /* kelvins, moyenne de 14' */
    float t = clamp(dT / 300.0e-6, -1.0, 1.0);
    float far = smoothstep(2.0e9, 2.0e10, pc.cam.w); /* comme les autres sphères de l'univers observable */
    o = vec4(palette(t) * 0.35 * pc.par.x * far, 1.0);
}
