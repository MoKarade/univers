# Tables de raccord (départ contraint → grand calcul)

Source : zoom fin de la paire v17 (départ contraint Cosmicflows-4 + 2MRS, Vierge imposée, paire ajustée par genetIC),
GADGET-4, matière noire seule. Statut à l'écran : **modèle (calcul contraint)**, pas une mesure.
Produit par `pipeline/contraint/environnement_paire.py` (voir son en-tête pour les formules et les limites).

| Fichier | Contenu |
|---|---|
| `masse_t.csv` | M200 (M☉), r200 (kpc physiques), concentration NFW (2,163 r200 / r_max) de la Voie lactée et d'Andromède |
| `orbite_paire.csv` | séparation (kpc), vitesses radiale et tangentielle (km/s, flot de Hubble compris) |
| `maree.csv` | tenseur de marée extérieur 3×3 au centre de masse de la paire, (km/s/kpc)², repère galactique de l'appli (phys::galaxie), particules entre 1,5 et 50 Mpc ; trace nulle (contrôle) ; énergie noire NON incluse |
| `spin.csv` | λ' de Bullock et direction unité du moment cinétique de chaque halo, même repère |

Version 1 (20/11/2026) : instantanés d'origine de −2,0 à 0 Ga (pas inégal, ~0,25 Ga). Version 2 (en calcul) : tous les
0,1 Ga de −2,4 à +10 Ga.
Repère des galaxies : Andromède = halo situé du côté de sa direction réelle vue de la Voie lactée.
Écarts connus de cette paire au ciel mesuré : masses 2,1 et 1,7e12 (mesuré 1,34 et 1,07e12 dans la table unique),
1 028 kpc (785), −61 km/s (−110).

## Convention de signe de `maree.csv` (confirmée)
T_ij = −∂²Φ_ext/∂x_i∂x_j, avec x mesuré depuis le centre de masse de la paire ; accélération de marée a_i = +T_ij x_j.
Calcul : T_ij = G Σ m (3 r_i r_j − r² δ_ij) / r⁵, r = position de la particule − centre (G = 4,30091e-6 kpc (km/s)²/M☉).
Contrôle de signe : une masse seule sur l'axe x donne T_xx = +2Gm/r³ > 0, donc **T_xx > 0 = étirement le long de x**
(la paire est tirée vers la masse et loin d'elle des deux côtés), T_yy = T_zz = −Gm/r³ < 0 = compression. Trace nulle.
Unités : (km/s/kpc)² ; 1 (km/s/kpc)² = 1,046 Ga⁻².

## Incertitude : `maree_dispersion.csv` (`pipeline/contraint/maree_dispersion.py`)
Même formule, au centre de masse de la paire, dans les 10 calculs où une paire existe (les graines sans paire sont
écartées : leur voisinage n'est pas celui d'un Groupe local). Résultat sur T_xx : 2,24e-3 ± 0,59e-3 à −1,27 Ga,
2,04e-3 ± 0,42e-3 aujourd'hui (moyenne ± écart-type, (km/s/kpc)²) ; les autres composantes et dates sont dans le fichier.
**Attention : 9 de ces 10 calculs partagent la même graine (réglages de paire différents) ; la vraie dispersion entre
réalisations indépendantes est probablement plus grande** [Probable]. Un balayage dédié (paire réglée sur plusieurs
graines) la mesurerait : environ 1 h de processeur par graine.

## Version 2 (20/11/2026) : dossier `v2/`, tous les 0,1 Ga de −2,3 à +5,1 Ga
Calcul relancé depuis l'instantané de −2,48 Ga avec une sortie tous les 0,1 Ga jusqu'à +10 Ga (2 101 s, 12 fils).
Suivi au niveau des **sous-halos** (les groupes FOF des deux galaxies se soudent dès ~+1,8 Ga, bien avant la fusion) :
- `masse_t.csv` : colonnes M200, r200, concentration VIDES (nan) quand les deux galaxies partagent un groupe (M200 n'a plus
  de sens) ; nouvelle colonne `masse_liee_msun` (masse liée du sous-halo, toujours remplie).
- **Fin des tables à +5,1 Ga** : la galaxie « andromede » de ce calcul est dissoute dans l'autre vers +5,2 Ga (sa masse
  liée tombe sous 25 % de son maximum). Premier passage serré : ~216 kpc à +5,1 Ga, −227 km/s. Après, il n'y a plus de
  paire à décrire ; la masse du reste fusionné peut être ajoutée sur demande.
- Avertissement (modèle) : ce calcul a un troisième halo de ~5e12 M☉ à ~3 Mpc de la paire, absent du ciel réel ; il pèse
  sur la marée et sur l'orbite. La dispersion de la marée entre graines indépendantes est en calcul (balayage « rcp »).
