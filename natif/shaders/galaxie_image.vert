#version 450
/* Photos des galaxies voisines posées sur le plan de leur disque (galaxies_images.h).
   inPos : point du disque par rapport au centre de la galaxie (années-lumière, écliptique) ; inUv : place dans la photo. */
layout(location = 0) in vec3 inPos;
layout(location = 1) in vec2 inUv;
layout(push_constant) uniform Pc { mat4 viewProj; vec4 centre; vec4 normal; vec4 par; } pc;
layout(location = 0) out vec2 vUv;
layout(location = 1) out float vSlant;
void main() {
    vec3 p = inPos + pc.centre.xyz;      /* par rapport à la caméra */
    /* éclat de surface d'un disque mince transparent vu sous l'angle θ de sa normale : celui vu de face / |cos θ|
       (borné : vu par la tranche, le disque mince deviendrait infiniment brillant) */
    vSlant = 1.0 / max(abs(dot(normalize(p), pc.normal.xyz)), 0.12);
    vUv = inUv;
    gl_Position = pc.viewProj * vec4(p, 1.0);
}
