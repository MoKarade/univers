/* Inclus par gaia.vert et gaia_agrege.vert (docs/gaia-rayons.md). Mêmes valeurs dans gaia.h (GaiaFiable), à garder identiques.
   1. Effacement dans le temps : seules les étoiles à orbite fiable (vitesse radiale mesurée, vitesse 3D connue à mieux que
      10 km/s, drapeau 2 de gaia.bin) suivent leur orbite loin d'aujourd'hui. Les autres sources ne sont montrées qu'autour
      du présent mesuré : leur lumière s'efface en exp(-(t / 3 Ma)²). Mesuré : sans vitesse radiale, l'erreur de place grandit
      d'environ 35 pc par million d'années (médiane), et dépasse l'erreur de distance d'aujourd'hui (80 à 180 pc entre 1 et
      4 kpc) en 2 à 5 millions d'années.
   2. Éclat rééquilibré vu de loin (drapeau 4, pipeline/natif/gaia_reequilibre.py) : HYPOTHÈSE, dite à l'écran. Gaia ne
      mesure pas la distance aussi loin dans toutes les directions ; vu de loin, cela dessine des rayons autour du Soleil.
      Chaque source reçoit un décalage d'éclat qui ramène sa case de ciel à la moyenne des cases voisines (15°). Il compte en
      proportion de l'écart caméra-Soleil rapporté à la distance de la source : rien vu du Soleil (le ciel reste celui mesuré),
      tout vu de loin. */
const float GF_TAU_ANS = 3.0e6;
const uint GF_MODE_RENDU = 0x80000000u;      /* bit haut de cellBase : vue « meilleur rendu » (Sim::bestLook) ; sinon 100 % mesuré */
float gfEffacement(float tGa) {
    float u = tGa * 1.0e9 / GF_TAU_ANS;
    return exp(-u * u);
}
float gfPoidsLoin(vec3 cam, vec3 star) { return clamp(length(cam) / max(length(star), 1.0), 0.0, 1.0); }
