# Physique du gaz : refroidissement exact et explosions d'étoiles (24/11/2026)

Fil « Physique du gaz ». Suite prévue du grand calcul N-corps du Groupe local (Marc, 19/11/2026 : « tout »).
Labels : [Certain] lu ou mesuré aujourd'hui ; [Probable] publié, source connue ; [Supposition] ; [À vérifier].

## En bref

- Le gaz du grand calcul est aujourd'hui **tiède et d'une seule phase** (`gaz_galaxie.Gaz`, branche film-3) : il ne
  chauffe ni ne refroidit, et les explosions d'étoiles sont remplacées par une pression effective. [Certain]
- Une version « thermique » (`GazThermique`) a été écrite le 19/11 mais **jamais exécutée**. En la relisant, trois
  défauts sont apparus (plus bas). [Certain]
- Ce lot écrit, sans la carte graphique (prise par le grand film), la physique qui manquait, et la **contrôle sur le
  processeur** : `pipeline/fusion/gaz_physique.py`, `gaz_cpu.py`, `essai_gaz_physique.py`.
- Le branchement dans le grand calcul attend la fin du film (la carte, et les fichiers du fil du grand calcul).

## Ce qui est écrit

| Pièce | Fichier | Statut |
|---|---|---|
| Courbe de refroidissement (équilibre par collisions, composition solaire) | `gaz_physique.lambda_cie` | Modèle publié : ajustement de Cholla (Schneider & Robertson), code lu le 24/11 [Certain pour les coefficients] |
| Refroidissement intégré **exactement** à chaque pas | `gaz_physique.Refroidissement` | Méthode de Townsend 2009 (ApJS 181, 391, éq. 24-26) [Certain] |
| Nombre de supernovæ par masse d'étoiles formée | `nombre_sn_par_masse` | Chabrier 2003 ; 6-100 M☉ donne 1,7359 × 10⁻², la valeur publiée par Dalla Vecchia & Schaye 2012 est 1,736 × 10⁻² [Certain, mesuré] |
| Instant de chaque explosion (durée de vie des étoiles) | `duree_de_vie`, `Explosions` | Raiteri et al. 1996 : 8 M☉ → 39,7 Ma, 100 M☉ → 3,35 Ma [Probable] |
| Supernovæ thermonucléaires (Ia) | `Explosions` | 1,3 × 10⁻³ par M☉, délai en 1/t dès 40 Ma (Maoz & Mannucci 2012) [Probable] |
| Dépôt de l'énergie, saut de 10^7,5 K | `deposer` | Dalla Vecchia & Schaye 2012, avec une **réserve** par particule d'étoiles : énergie conservée exactement [Certain, contrôlé] |
| Gaz sur processeur, mêmes équations que la carte (plus la forme d'énergie de Monaghan, défaut) | `gaz_cpu.sph` | Jumeau de `gaz_gpu.sph` en double précision [Certain pour la correspondance ligne à ligne ; comparaison chiffrée à faire quand la carte est libre : `essai_gaz_physique.py gpu`] |

## Défauts trouvés dans `gaz_gpu` et `GazThermique` (branche film-3 ; gaz « chaud » jamais exécuté)

0. **Le gaz chaud crée de l'énergie** (`gaz_gpu.py`, noyau `forces`, `du += 0.5f * f * vr`) : une particule froide
   voisine d'une particule très chaude perd de l'énergie au nom de la pression de sa voisine, passe sous zéro, et le
   plancher la remet à zéro : +6,6 % d'énergie sur l'explosion de Sedov (mesuré sur le jumeau, entièrement dû au
   plancher). Remède d'une ligne : `du += mass[j] * (pr[k] + 0.5f * visc) * g * vr` (forme de Monaghan 1992, celle de
   GADGET-2) ; mesuré : −0,09 %. Le film en cours est en gaz tiède (`--gaz=1`, sans énergie interne) : non touché.
   [Certain, mesuré]

1. **Refroidissement tronqué** : la boucle s'arrête après 24 sous-pas de 20 % et jette le temps restant. Du gaz à
   10^7,5 K dans un milieu dense resterait vers 10^5-10^6 K au lieu de se refroidir. Remède : `Refroidissement.refroidir`
   (exact, sans boucle). [Certain, lecture du code]
2. **Normalisation de la courbe, facteur ~4** : le code prend la perte n² Λ avec n = ρ / (0,6 m_p), comme Cholla. Les
   valeurs de cette courbe tombent sur celles des tables normalisées par n_e n_i (Sutherland & Dopita 1993). Avec n², le
   gaz se refroidirait environ 4 fois trop vite. Choix ici : n_e n_i ; l'autre reste disponible pour comparer.
   [Probable ; à vérifier contre une table de Sutherland & Dopita 1993 ou Gnat & Sternberg 2007]
3. **Explosions au moment de la naissance**, toutes d'un coup, et énergie conservée seulement en moyenne (tirage au
   sort). Remède : les supernovæ partent entre 3,4 et 40 Ma selon la masse des étoiles, puis les Ia ; l'énergie passe
   par une réserve, conservée exactement.

## Contrôles (sans carte graphique)

`python pipeline/fusion/essai_gaz_physique.py` (environnement `C:\tmp\venv-cupy`) :

- refroidissement exact contre une intégration très fine (Runge-Kutta, pas adaptatif) : 22 cas de 2 × 10⁴ à 10⁸ K,
  densités 0,01 et 1 atome/cm³, pas de 0,1 à 2 temps de refroidissement : écart < 10⁻⁴ ; un pas = mille petits pas à
  10⁻⁶ près ; plancher de 10⁴ K exact ;
- supernovæ par masse formée contre la valeur publiée ; somme des pas = total ;
- réserve d'énergie : déposée + restante = libérée à 10⁻¹² près ; masse inchangée ;
- jumeau processeur : gradient connu, tube à choc, explosion de Sedov ; puis explosion d'étoiles dans du gaz qui
  rayonne (cinétique + interne + rayonnée = départ + déposé).

Résultats du 24/11/2026 (processeur, `TOUT BON`) :

| Contrôle | Mesuré | Référence |
|---|---|---|
| Refroidissement exact, 28 cas de 2 × 10⁴ à 10¹⁰ K | écart < 10⁻⁴ | Runge-Kutta fin |
| Supernovæ 6-100 M☉ par M☉ (Chabrier) | 1,7359 × 10⁻² | 1,736 × 10⁻² (Dalla Vecchia & Schaye 2012) |
| Réserve : déposée + restante / libérée | 1 à 10⁻¹² | 1 |
| Tube à choc isotherme, 13 143 particules | densité −4,1 %, vitesse −0,7 % | solution exacte |
| Sedov, 32 736 particules, forme de Monaghan | rayon −5,4 %, énergie −0,09 % | 1,1527 (E t²/ρ)^(1/5) |
| Sedov, même montage, forme « moyenne » de gaz_gpu | énergie +6,6 % à 8 000 particules, entièrement due au plancher | 0 |
| Explosion dans du gaz à 1 atome/cm³ qui rayonne, 2 Ma | bilan −0,08 % ; 68 % de l'énergie rayonnée, 17 % en mouvement | 0 |

Le 68 % rayonné à cette finesse (particules de 268 M☉, 20 pc) est attendu : c'est le « sur-refroidissement » des
explosions mal résolues que le saut de 10^7,5 K atténue sans le supprimer [Probable].

## Ce qui n'est pas calculé, et doit être dit à l'écran

Gaz froid sous 10⁴ K (nuages moléculaires) ; chauffage par la lumière des étoiles ; vents des étoiles massives et
pression de leur lumière ; champ magnétique et rayons cosmiques (même ordre d'énergie que le gaz, second ordre pour la
forme d'un disque) ; noyau actif (négligeable aujourd'hui, incertain pendant la fusion) ; métaux (Z fixé au solaire).
[Probable pour les ordres de grandeur, voir docs/lois-physiques/04-gaz-poussiere-lumiere.md]

## Masse et énergie noire

- Masse : rien ici ne crée ni ne détruit de masse. Les explosions ne déplacent que de l'énergie ; naissances et retour
  de masse changent la nature d'une particule, pas sa masse (gaz_galaxie.py). [Certain]
- Énergie noire : la gravité du gaz passe par le même calcul N-corps que tout le reste, avec le terme d'énergie noire du
  grand calcul (energie_noire.py). Ce lot ne touche pas à la gravité. [Certain]

## Branchement dans le grand calcul (après le film)

1. Dans `gaz_galaxie.GazThermique` : remplacer `_refroidir` par `Refroidissement.refroidir(u, rho, d, xp=cp)` ;
   remplacer le chauffage à la naissance par : réserve par particule d'étoiles (`Explosions.energie_liberee` selon l'âge,
   étoiles du départ comprises pour les Ia), puis `deposer` sur les voisines de gaz (version carte à écrire : même
   règle, voisines déjà trouvées par l'arbre de gaz_gpu).
2. `essai_gaz_physique.py gpu` : jumeau processeur contre carte, puis `essai_gaz.py sedov` sur la carte.
3. Galaxie seule 0,5 Ga en `--gaz=2` : sursaut central, barre, nombre de sous-pas (le gaz à 10^7,5 K demande des
   sous-pas ~10 fois plus courts : coût à mesurer avant de l'annoncer).
4. Bulletin : taux de naissance (1,65 ± 0,19 M☉/an) **et** sa répartition en rayon (Elia et al. 2022).
