# Nébuleuses en 3D (20 novembre 2026)

Demande de Marc : « l'espace paraît trop vide, il manque du gaz, des nébuleuses, de la poussière ».

Seules des nébuleuses dont la distance est PUBLIÉE sont placées (`pipeline/natif/nebuleuses.py`) :

| Genre | Source | Nombre | Ce qui est mesuré | Ce qui est supposé |
|---|---|---|---|---|
| Nébuleuses planétaires | Chornay et Walton 2021 (A&A 656, A110), étoiles centrales dans Gaia EDR3 ; gardées : association de fiabilité ≥ 0,8, parallaxe > 5 erreurs | 223 | direction, distance (Hélice : 199 pc ; Anneau M57 : 790 pc), rayon angulaire | éclat : repère de couleur fixe (bleu-vert de l'oxygène, rouge de l'hydrogène au bord) |
| Nuages moléculaires (poussière) | Zucker et al. 2020 (A&A 633, A51), 326 lignes de visée | 94 nuages | direction, distance (Orion 420 pc, Taureau 149 pc) | étendue : celle couverte par les lignes de visée (au moins 1 pc ; borne basse) ; opacité au centre : 10 % de lumière transmise |

Dessin (`natif/src/nebuleuses.h`, `shaders/nebuleuse.vert/.frag`) : une tache ronde de la taille mesurée ; la poussière
assombrit ce qui est déjà dessiné (multiplication), les nébuleuses planétaires s'ajoutent. Montrées à moins de 30 000 al
du Soleil (fondu jusqu'à 60 000) et autour d'aujourd'hui (fondu de 1 à 3 Ma). Case du menu « Couches ».

Vu à l'écran : la nébuleuse de l'Hélice (`captures-nebuleuses/`). **Pas encore vu** : l'effet des nuages sombres (petits à
l'écran avec l'étendue des lignes de visée : rayon médian 19 al à 1 600 al, soit ~0,7°) ; à vérifier au prochain créneau
de carte graphique. Non fait : leurs noms dans la recherche (il faudra un genre d'astre « nébuleuse »).

## Poussière : la carte 3D mesurée (20 novembre, soir)

Les nuages de Zucker et al. 2020 dessinés en taches étaient bien trop petits (étendue tirée des seules lignes de visée) et
presque invisibles. Ils sont remplacés par la carte 3D de la poussière d'Edenhofer et al. 2024 (déjà dans
`voie_lactee.bin`, grille locale de cases de 15,6 pc jusqu'à 1,24 kpc du Soleil) : pour chaque pixel, l'extinction A_V
est sommée le long du rayon et la transmission 10^(−0,4 A_V) multiplie ce qui est déjà dessiné (`voie_lactee.frag`,
mode « poussière seule »). Montrée vue de loin (au-delà de 4 000 al du Soleil, fondu jusqu'à 6 500) : de près, les
magnitudes mesurées des étoiles contiennent déjà cette poussière vue du Soleil, elle serait comptée deux fois.
Approché : une étoile placée devant un nuage est assombrie elle aussi (pas de profondeur dans l'image).
Captures : `captures-nebuleuses/P3D_6000.jpg`, `P3D_8000_plan.jpg` (filaments sombres autour du Soleil, vus à 6 000 et
8 000 al).
