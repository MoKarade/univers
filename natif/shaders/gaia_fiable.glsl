/* Inclus par gaia.vert et gaia_agrege.vert (docs/gaia-rayons.md). Mêmes valeurs dans gaia.h (GaiaFiable), à garder identiques.
   1. Effacement dans le temps : seules les étoiles à orbite fiable (vitesse radiale mesurée, vitesse 3D connue à mieux que
      10 km/s, drapeau 2 de gaia.bin) suivent leur orbite loin d'aujourd'hui. Les autres sources ne sont montrées qu'autour
      du présent mesuré : leur lumière s'efface en exp(-(t / 3 Ma)²). Mesuré : sans vitesse radiale, l'erreur de place grandit
      d'environ 35 pc par million d'années (médiane), et dépasse l'erreur de distance d'aujourd'hui (80 à 180 pc entre 1 et
      4 kpc) en 2 à 5 millions d'années.
   2. Poussière : l'éclat mesuré depuis la Terre contient la poussière entre l'étoile et le Soleil (A_G estimé par Gaia,
      drapeau 4). Vue d'ailleurs, cette poussière n'est plus sur le trajet : elle est retirée en proportion de l'écart
      caméra-Soleil rapporté à la distance de l'étoile (0 au Soleil, toute au-delà) [approché : la poussière caméra-étoile
      n'est pas ajoutée]. */
const float GF_TAU_ANS = 3.0e6;
float gfEffacement(float tGa) {
    float u = tGa * 1.0e9 / GF_TAU_ANS;
    return exp(-u * u);
}
float gfPoidsPoussiere(vec3 cam, vec3 star) { return clamp(length(cam) / max(length(star), 1.0), 0.0, 1.0); }
