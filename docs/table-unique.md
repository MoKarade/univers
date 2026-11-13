# Table unique des constantes et orbites de référence du Groupe local (étapes 0 et 3 du plan B+, 13 novembre 2026)

Plan : `docs/refonte-simulations-pro.md` (PR 95), option B+ validée par Marc le 13/11 (« go option b+ »).
Labels : [Certain] calculé ou lu ce jour ; [Probable] publié, non relu en entier ; [Supposition] choix fait ici.

## 1. Ce qui existe maintenant

| Fichier | Rôle | Qui le lit |
|---|---|---|
| `pipeline/constantes/table_source.py` | **la seule source écrite à la main** : repère, Soleil, cosmologie, modèles de masse des 4 galaxies, lois de masse, observables d’aujourd’hui, orientation des disques ; chaque bloc avec sa source | `construire.py` |
| `pipeline/constantes/univers.json` | table générée, avec les grandeurs calculées (masses des modèles, positions et vitesses d’aujourd’hui dans le repère phys::galaxie, axes de rotation) | Python (`constantes.py`) |
| `natif/physique/constantes_univers.h` | même table pour l’appli | **pas encore branché** (voir § 4) |
| `pipeline/constantes/grand_livre.py` → `docs/grand-livre-masses.md` | compare la table à ce que lisent l’appli et les calculs ; liste les écarts | les fils qui doivent s’aligner |
| `pipeline/fusion/groupe_local_reference.py` | ensemble Monte-Carlo des orbites des centres **sur les masses de la table**, avec énergie noire et Petit Nuage ; réalisation de référence | — |
| `pipeline/fusion/resultats/cible_aujourdhui.json` | pour le fil des galaxies de départ : où chaque galaxie doit être **aujourd’hui** (position, vitesse, masse), et où la référence la place à −3 Ga | `depart_passe.py` |
| `pipeline/fusion/resultats/centres_reference.npz` | pour le fil Voie lactée (affichage) : centre de chaque galaxie de −3 à +10 Ga, un point par ~1 Ma | `fenetre.cpp` (branchement par ce fil) |

Régénérer : `python pipeline/constantes/construire.py && python pipeline/constantes/grand_livre.py && python pipeline/fusion/groupe_local_reference.py`.

## 2. Ce que la table tranche

| Point | Tranché | Pourquoi |
|---|---|---|
| R0 | **8,20 kpc** | McMillan 2017 (résumé : 8,20 ± 0,09), identique à l’appli et au repère du fil Voie lactée [Certain] |
| Vitesse circulaire au Soleil | **232,8 km/s** | McMillan 2017 (résumé) : c’est le modèle de masse du calcul N-corps ; l’appli a 230 (écart au grand livre) [Certain] |
| Mouvement propre du Soleil | (11,1 ; 12,24 ; 7,25) km/s | Schönrich et al. 2010 [Probable] |
| Distance d’Andromède | **761 kpc** (module 24,407 ± 0,032) | Li et al. 2021, via Sawala 2025 [Probable] |
| Mouvement propre d’Andromède et du Triangle | **Wu et al. 2025** (le plus récent) ; Sawala 2025 en variante | [Probable] |
| Masse d’Andromède | **1,065 × 10¹² M☉** ± 0,25 (modèle de Tamm 2012 intégré) | le film et l’ensemble tirent de la même loi ; Sawala (1,3 ± 0,4) en variante [Supposition pour la largeur] |
| Masse de la Voie lactée | **1,343 × 10¹² M☉** ± 0,30 (modèle de McMillan intégré, halo coupé à 250 kpc) | largeur : McMillan 2017 (1,30 ± 0,30) [Certain pour le calcul] |
| Masse du Triangle | **4,08 × 10¹¹ M☉** ± 1,0 (Corbelli 2014) | [Probable] |
| Grand Nuage | **1,38 × 10¹¹ M☉ après coupure** (Erkal 2019) | le modèle de `modeles_v2.py` n’en gardait que 0,97 après sa coupure à 100 kpc : la table règle le Hernquist (2,29 × 10¹¹, 25,8 kpc avant coupure) pour respecter à la fois la masse totale et 1,7 × 10¹⁰ M☉ dans 8,7 kpc [Certain pour le calcul] ; **tir de stabilité à refaire** |
| Petit Nuage | 3 ± 1 × 10⁹ M☉, **masse totale adoptée, pas mesurée** ; modèle réglé ici (halo de Hernquist 3,09 × 10⁹ et 1,73 kpc coupé à 10 kpc, soit 2,13 × 10⁹ ; étoiles 3,1 × 10⁸ ; gaz 5,6 × 10⁸) sur la matière noire dans 4 kpc (1 à 1,5 × 10⁹, Di Teodoro et al. 2019) ; mouvement propre et vitesse : Kallivayalil 2013 ; distance : Graczyk 2020 | masses internes : [Probable] ; total et formes : [Supposition] ; vitesse circulaire du modèle ~50 km/s contre ~55 mesurés à 2,8 kpc |
| Vitesses d’ensemble | **calculées depuis les observables de la table**, pas `conditions.json` | `conditions.json` est périmé : M31 à 783 kpc, Triangle à 809 kpc, Triangle à 72 km/s de la table, Grand Nuage à 20 km/s (grand livre § 2) [Certain] |
| Axes de rotation | calculés (inclinaison, angle de position, sens, côté proche ou bout en approche) | Triangle et Grand Nuage : identiques à ceux du fil Voie lactée ; Andromède : 3° d’écart (77° contre son inclinaison) ; Andromède : côté proche retrouvé au nord-ouest à partir du sens et du côté en approche, comme attendu [Certain] |

## 3. Orbites des centres : résultats [Certain : calculé ici, 5 000 tirages chacun, normale tronquée à ±2σ]

| Variante | Galaxies | Énergie noire | Fusion Voie lactée–Andromède en 10 Ga | Date (16 % / médiane / 84 %) |
|---|---|---|---|---|
| Contrôle : masses et mouvements propres de Sawala 2025 | 4 | non | **56 %** (publié : « un peu plus de 50 % » ; ancien script : 52,6 %) | 6,4 / 7,5 / 8,9 Ga |
| Sawala 2025 | 4 | oui | 55 % | 6,5 / 7,6 / 9,0 Ga |
| **Table unique** | 5 (Petit Nuage compris) | non | 96 % | 5,3 / 6,5 / 7,6 Ga |
| **Table unique (référence de l’appli)** | 5 | **oui** | **96 %** | **5,4 / 6,6 / 7,8 Ga** |

Lecture :
- Le contrôle retrouve Sawala à 3 points près ; l’écart restant vient du repère (R0 8,20 au lieu de 8,122, Soleil un peu différent) et du tirage
  [Probable].
- L’énergie noire retarde la fusion d’environ 0,1 Ga et ôte ~1 point de probabilité : c’est l’ordre de grandeur attendu (15 % de la force
  à 770 kpc, rien sous 300 kpc) [Certain pour le calcul].
- **Le passage de 55 % à 96 % vient des mesures choisies, pas du code** : mouvement propre d’Andromède de Wu et al. 2025 (moins de vitesse
  transverse) et Voie lactée plus lourde (McMillan). Wu et al. 2026 trouvent 90 % avec le même mouvement propre [Probable]. C’est la
  grandeur la plus discutée de tout le sujet : l’écran doit dire « 96 % avec ces mesures, environ 50 % avec celles de Sawala 2025 ».
- Grand Nuage absorbé par la Voie lactée dans 100 % des cas ; Triangle absorbé par Andromède dans 14 % ; Petit Nuage absorbé par le Grand dans 69 %.

Réalisation de référence (toutes les grandeurs à leur valeur centrale, énergie noire, 5 galaxies) :

| Galaxie | Aujourd’hui | Il y a 3 Ga | Premier passage au plus près de la Voie lactée | Centres à moins du seuil |
|---|---|---|---|---|
| Andromède | 765 kpc | 984 kpc | **+5,54 Ga à 30 kpc** | fusion à +6,90 Ga (médiane de l’ensemble : 6,65) |
| Triangle | 864 kpc | 919 kpc | +4,73 Ga à 392 kpc | — |
| Grand Nuage | 49 kpc | 179 kpc | +0,51 Ga à 28 kpc | sous 20 kpc à +1,18 Ga |
| Petit Nuage | 60 kpc | 67 kpc | +0,20 Ga à 44 kpc | sous le seuil du Grand Nuage à +0,64 Ga |

Fichier `centres_reference.npz` (13 296 dates de −3,000 à +10,000 Ga, pas de 0,978 Ma, t = 0 exactement à l’indice 3068) : contrôle
d’interpolation d’Hermite cubique en sautant 4 points sur 5 (5 Ma) : **erreur au plus 0,002 kpc** ; plus grand pas entre deux dates 1,1 kpc.
La référence **ne fusionne pas les centres d’un coup** (Sawala le fait, et le centre de la Voie lactée sauterait alors de plusieurs kpc
pour tout l’affichage) : les deux corps restent et le frottement les rapproche en continu.

Limites : galaxies indéformables (orbites des centres seulement), frottement analytique, adoucissement de 20 kpc ; une histoire parmi
d’autres. Le film N-corps la remplacera.

## 4. Ce qui n’est pas fait, et par qui

- **Brancher la table dans l’appli** (`galaxie_orbites.h` : kV0 230 → 232,8, vitesse du Soleil) : change toutes les orbites d’étoiles de ~1 %.
  Pris par le fil Voie lactée (PR 96), avec les shaders et un contrôle visuel.
- **Remplir `GALAXIES` de `modeles_v2.py` depuis la table** (`constantes.modele_pour_modeles_v2(cle)`) : fil des galaxies de départ,
  avec un nouveau tir du Grand Nuage.
- **Brancher `centres_reference.npz` dans l’appli** : fil Voie lactée (PR 96), qui déplace chaque galaxie en bloc en attendant le film.
- **Essai de forme** (continuité de la forme de chaque galaxie d’une image à la suivante) : à brancher sur `essai_continuite.cpp` quand le
  film v2 existera (il n’y a aujourd’hui rien qui change de forme de façon continue à mesurer).
