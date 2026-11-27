# Refaire le grand calcul à une autre résolution (20 M, puis 50 M de particules)

Écrit le 23 novembre 2026 pour le fil « Tester le grand calcul sur Colab ». Marc : « fiabilité maximale possible, pour
tout ». Le film 3 du PC tourne à 9,8 M de particules de masse ; un état « aujourd'hui » ne se gonfle pas (la barre et les
bras dépendent du nombre de particules), donc toute la chaîne se refait à chaque résolution.

Tout le code est sur la branche `film-3`, dossier `pipeline/fusion`. Les commandes ci-dessous sont pour Linux (Colab, WSL).
`F` est le facteur de résolution : 1 = film 3 (9,8 M), 2 = 19,6 M, 5 = 49 M.

## Ce qu'il faut sur la machine

- le dépôt (branche `film-3`), python avec `cupy`, `scipy`, `numpy` ;
- un dossier de données `$D` rangé comme `C:/tmp/natif` : `gaia/gaia.bin`, `gaia/gaia_b.bin`, `gaia/gaia_agrege.bin`,
  `donnees/etoiles.bin`, `donnees/etoiles-visibles/` (contrats des étoiles visibles, dont
  `etoiles_visibles_voie_lactee.npz.film1`), `spirales-sortie/` (contrats des voisines) ;
- la marée : `maree_ciel_reel.csv` (`C:/dev/univers-contraint/pipeline/contraint/tables_raccord/ciel_reel/`) ;
- les traceurs, qui ne dépendent pas de la résolution : `C:/tmp/natif/groupe-local-3/traceurs/gaia.npz` et `naines.npz` ;
- l'état de départ des orbites déjà réglé : `C:/tmp/analyse-architecture/galaxies/v25/tir11/etat_corrige.json`.

## (a) et (b) Galaxies de départ, halo tournant compris — processeur seul

```bash
bash pipeline/fusion/tirer_galaxies.sh <galaxies> 2
```

AGAMA s'installe au premier passage (compilation). Sortie : `<galaxies>/plein/*.npz`. L'adoucissement suit N^(−1/3)
tout seul (× 0,79 à F = 2, × 0,58 à F = 5). Fait pour F = 2 sur le PC : `C:/tmp/analyse-architecture/galaxies/v26/plein`.

## (c) Réglage des orbites — 2 ou 3 tirs à basse résolution (environ 2 M de particules chacun)

```bash
cd pipeline/fusion
python -u rencontre.py tir <galaxies>/plein <tirs>/tir1 --fraction=0.1 --etat=<v25/tir11/etat_corrige.json> --releve-ma=50 --maree=<maree.csv>
python -u rencontre.py tir <galaxies>/plein <tirs>/tir2 --fraction=0.1 --etat=<tirs>/tir1/etat_corrige.json --releve-ma=50 --maree=<maree.csv>
python -u rencontre.py tir <galaxies>/plein <tirs>/tir3 --fraction=0.1 --etat=<tirs>/tir2/etat_corrige.json --releve-ma=50 --maree=<maree.csv>
```

(`--fraction=0.04` à F = 5.) Bon quand la fin du journal donne chaque galaxie à moins de 3 kpc de sa place mesurée
(référence : tir 11 du 20/11, 1,1 à 2,2 kpc). Le Petit Nuage est replacé d'office il y a 300 Ma (c'est écrit dans l'état).

## (d) Les deux passes, la barre, les étoiles visibles, puis le film — un seul lanceur, qui reprend où il s'est arrêté

```bash
export UNIVERS_PYTHON=python UNIVERS_DONNEES=$D
export UNIVERS_GALAXIES=<galaxies>/plein UNIVERS_ETAT=<tirs>/tir3/etat_corrige.json
export UNIVERS_CONTRAT=$D/donnees/etoiles-visibles/etoiles_visibles_voie_lactee.npz.film1 UNIVERS_CONTRATS_VOISINES=$D/spirales-sortie
export UNIVERS_GAZ=1 UNIVERS_EFFICACITE=0.0115 UNIVERS_MAREE=<maree.csv>
export UNIVERS_FILM=3 UNIVERS_GAIA=<traceurs>/gaia.npz UNIVERS_NAINES=<traceurs>/naines.npz UNIVERS_FIN_GA=10
bash pipeline/fusion/lancer_colab.sh <sortie>
```

Étapes, dans `<sortie>/journal.txt` : passe 1 (−1,25 Ga à aujourd'hui), mesure de la barre, passe 2 avec la barre de la
Voie lactée calée, Andromède tournée sur elle-même (`tour.json`), contrôle de l'arrivée, plan du disque calé, étoiles
visibles tirées de la masse (`etoiles/`), film (`film/`). Relancer la même commande reprend à la dernière sauvegarde
(toutes les 50 Ma). Pour s'arrêter après les passes : `UNIVERS_FIN_GA=0.1` (film d'essai de 100 Ma), puis relancer avec 10
après avoir déplacé `film/`.

Contrôles à faire avant le film long (valeurs du film 3 à 9,8 M, entre parenthèses) :
- arrivée des quatre voisines à moins de 3 kpc (1,2 ; 0,9 ; 0,95 ; 2,7) ;
- barre de la Voie lactée : force 0,25 à 0,30 entre 2 et 4 kpc, à moins de 5° de la direction mesurée (0,258 ; 2°) ;
- `python pipeline/fusion/barre_rayon.py <sortie>/passage1.npz 0` : gaz + étoiles nées de la Voie lactée ≈ 200 000 × F
  particules (157 800 + 42 100), sinon le retour de masse est faux ;
- film d'essai de 100 Ma : rayons des vieilles étoiles de chaque galaxie stables à 3 % près.

Pas de temps : 0,25 Ma. À F = 5, vérifier d'abord sur 100 Ma que l'énergie ne dérive pas plus qu'à F = 1 (0,008 % en
100 Ma) ; sinon ajouter `--pas-ma` au mode futur (à coder : le pas est fixé dans `avancer`).

## (e) Bulletin de la Voie lactée seule — pour savoir si le réglage v24 tient à cette résolution

```bash
cd pipeline/fusion
python -u stabilite_tir.py <galaxies>/brut/voie_lactee.npz 2.25 <bulletin>/vl_tir.json --releve-ma=10 --halo-tourne=0.35 --gaz=1 --efficacite=0.0115 --instantanes=0.25
python bulletin.py <bulletin>/vl_tir_t1.25.npz <bulletin>/vl_tir.json 1.25
```

(Fichier `brut/` : le halo n'y est pas encore tourné, `--halo-tourne` le fait.) Référence à 3,5 M (v24, 20/11) : barre
36,9 km/s/kpc et 5 kpc à 1,25 Ga, force 0,25, tout dans la marge des mesures sauf l'agitation au Soleil (46 pour 35 ± 5).
Si la barre sort de la marge, retoucher les options du tirage de la Voie lactée dans `tirer_galaxies.sh`.

## Mémoire et durées (mesures du PC, RTX 5080, 23/11)

- film 3 (9,8 M + 15,4 M de traceurs) : 11,4 Go de carte, 228 s pour 10 Ma au calme ;
- à F = 2 avec les traceurs : environ 16 Go, donc pas sur la 5080 ; durées estimées sur la G4 : passes ~16 h, film ~70 h ;
- à F = 5 : passes ~40 h, film ~130 h [estimations en N log N, à mesurer sur 15 minutes avant tout calcul long].
