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
