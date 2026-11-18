# Codes et bibliothèques open source réutilisables pour Univers (18 novembre 2026)

Demande : recenser ce qu'on peut reprendre plutôt qu'écrire, pour l'appli PC (C++, Vulkan, CUDA, RTX 5080 sous
Windows) et ses calculs (`pipeline/fusion/`). Pour chaque code : licence, carte graphique, Windows ou WSL, ce qu'il
remplacerait chez nous, l'effort et le gain en précision. **Aucun code n'a été modifié, aucun calcul lancé.**

Prolonge `docs/refonte-simulations-pro.md` (PR 95), qui comparait les *méthodes* des pros. Ici, on regarde les
*logiciels* eux-mêmes, et ce qu'ils valent concrètement sur la machine de Marc.

Labels : [Certain] lu ce jour sur la page officielle ou dans notre code ; [Probable] lu dans un résumé, ou connu
avec une source nommée ; [Supposition] mon raisonnement ou mon estimation ; [À vérifier] non confirmé ce jour.

---

## 0. En bref

1. **Aucun grand code de simulation ne peut remplacer notre moteur sur cette machine.** GADGET-4, AREPO, GIZMO,
   SWIFT, RAMSES, Enzo et ChaNGa tournent tous sur **processeur, sous Linux, avec MPI**. Aucun n'est fait pour Windows.
   Leur part sur carte graphique est nulle ou expérimentale : SWIFT sur GPU n'est « que marginalement plus rapide »
   que sur processeur (2025). [Certain pour l'OS et le GPU, pages lues]
2. **Notre gravité sur carte graphique (`gravite_gpu.py`) est de la même famille que Bonsai**, le seul code de
   gravité « pro » taillé pour le GPU. Bonsai est sous Apache 2.0, mais il est Linux seulement, figé vers 2017 et
   compilé pour de vieilles cartes. **On garde notre moteur.** [Certain pour Bonsai, Probable pour la comparaison]
3. **Le vrai usage des codes pros chez nous, c'est l'arbitre, pas le remplaçant.** GADGET-4 ou GIZMO sous WSL2,
   sur les 16 cœurs du 9950X3D, peuvent refaire *nos* galaxies de départ (mêmes particules AGAMA) sans toucher la
   carte graphique. Ça tranche la question ouverte du deuxième film : la barre trop lente et le disque qui s'épaissit
   viennent-ils du modèle de masse ou de notre moteur (pas fixe, adoucissement) ? [Supposition, à tester]
4. **À adopter tout de suite** : AGAMA (déjà là), les tables de refroidissement de **Grackle** (données, pas la
   bibliothèque), **REBOUND** comme référence du système solaire, et deux **données** : **Gaia DR4 le 2 décembre
   2026**, et **PHANGS** (CC BY 4.0) pour caler la formation d'étoiles du gaz.
5. **À garder maison** : la gravité GPU, le moteur de gaz SPH (en reprenant trois améliorations publiées, pas du
   code), le rendu, la lumière des étoiles via MIST.
6. **À laisser de côté** : MESA (MIST en est déjà le produit), MUSIC, monofonIC et genetIC (conditions
   cosmologiques : pas notre méthode depuis le plan B+), PeTar (amas d'étoiles), ChaNGa, SWIFT, RAMSES, Enzo,
   Shamrock (pas encore de gravité).

---

## 1. Ce qu'on a aujourd'hui (relu dans le code ce jour)

| Brique | Chez nous | Où | Label |
|---|---|---|---|
| Système solaire | Wisdom-Holman en coordonnées démocratiques, pas de 4 jours, relativité du Soleil au 1er ordre, départ DE440 | `natif/physique/nbody_noyau.h` | [Certain] |
| Gravité des galaxies | arbre de Barnes-Hut sur GPU (construction Karras 2012), quadripôles, CuPy, forces en simple précision ; **saute-mouton à pas fixe de 0,25 Ma** pour toutes les particules | `pipeline/fusion/gravite_gpu.py`, `rencontre.py`, `stabilite_tir.py` | [Certain] |
| Énergie noire | terme Ω_Λ H₀² r ajouté à chaque particule | `pipeline/fusion/energie_noire.py` | [Certain] |
| Galaxies de départ | AGAMA, à l'équilibre, paramètres publiés ; tiré par une tâche GitHub, car AGAMA ne s'installe pas sur le PC faute de compilateur | `modeles_v2.py`, `docs/plan-natif.md` | [Certain] |
| Gaz (tout neuf, branche `film-3`) | SPH sur GPU : spline cubique, ~58 voisines, viscosité de Monaghan avec l'interrupteur de Balsara, isotherme à 10 km/s, plancher de Jeans, naissance d'étoiles de Schmidt à 1 % par temps de chute libre au-dessus de 0,1 cm⁻³. **Pas de refroidissement, pas de rétroaction des explosions d'étoiles.** Contrôles : gradient, tube à choc, effondrement d'Evrard | `gaz_gpu.py`, `gaz_galaxie.py`, `essai_gaz.py` | [Certain] |
| Lumière des étoiles | table de vieillissement MIST v1.2 (Kroupa) | `docs/vieillissement-lumiere.md` | [Certain] |
| Étoiles visibles tirées des particules | maison, idée d'Ananke | `etoiles_visibles_masse.py` | [Certain] |

Les écarts mesurés dans le deuxième film (`docs/deuxieme-film.md`) : barre à ~20 km/s/kpc au lieu de 39, barre qui
grossit sans arrêt, disque qui s'épaissit trop, pas de gaz. [Certain, lu]

Un point que j'ai relevé en lisant le gaz : le pas est **le même pour tout le monde** (0,25 Ma). `gaz_galaxie.py`
mesure le nombre de Courant mais ne réduit pas le pas. Calcul ici : avec h = 0,02 kpc et un choc à 200 km/s, la
condition de Courant (0,3 h / v) donne environ 0,03 Ma, **huit fois moins que le pas utilisé**. Dans les chocs de la
rencontre, le gaz risque donc d'être faux. [Supposition, calcul fait ici, à confirmer par le relevé `cfl` du code]

---

## 2. Le tableau

Colonnes : **Lic.** licence ; **GPU** usage de la carte graphique ; **Win** Windows natif, WSL2 ou rien ; **Remplace**
ce que ça remplacerait chez nous ; **Effort** et **Gain** sont mes estimations [Supposition] sauf mention contraire.

### 2.1 Grands codes de simulation (gravité + gaz)

| Code | Lic. | GPU | Win | Ce qu'il apporte | Remplace | Effort | Gain |
|---|---|---|---|---|---|---|---|
| **GADGET-4** | GPL [Certain] | non mentionné [Certain] | Linux/Unix, MPI-3 ; Windows non mentionné → WSL2 [Certain pour Linux] | SPH à entropie conservée, arbre/TreePM/FMM, refroidissement et formation d'étoiles « simples » dans la version publique [Certain] | rien dans l'appli ; **arbitre** de notre gravité et de notre gaz | moyen : installation WSL2 + conversion de nos `.npz` au format GADGET (HDF5) | **fort comme contrôle** : dit si nos écarts viennent du moteur |
| **AREPO** | GPL-3 [À vérifier, page muette] | non mentionné | MPI seulement, pas d'OpenMP dans la version publique [Certain] ; Linux → WSL2 | gaz sur maillage mobile de Voronoi, le plus juste pour les chocs et le mélange ; refroidissement primordial et formation d'étoiles simples [Certain] | notre SPH, en théorie | élevé | fort pour le gaz, mais hors GPU et hors temps réel |
| **GIZMO** | GPL (version publique) [Certain] | non mentionné | Mac et Linux confirmés [Certain] → WSL2 | MFM/MFV (gaz sans maillage, plus juste que le SPH classique), refroidissement, **formation d'étoiles et rétroaction galactiques dans la version publique** ; la rétroaction FIRE est réservée [Certain] | notre gaz, en théorie ; **arbitre** du gaz | moyen à élevé | fort comme contrôle du gaz avec rétroaction |
| **SWIFT** | LGPL-3 [Certain] | expérimental : noyaux ×3,5, simulation complète « à peine plus rapide » sur Grace Hopper (2025) [Certain, résumé lu] | BSD, Linux [Certain] | SPH par tâches, très rapide sur processeur ; modèles EAGLE et COLIBRE [Probable] | rien | élevé | faible pour nous |
| **RAMSES** | CeCILL [À vérifier, la page dit seulement « open source »] | portage GPU partiel et ancien (OpenACC, hydro seule, 2014) ; ramsesGPU « surtout abandonné » [Certain] | non mentionné → WSL2 | grille adaptative (AMR), communauté active (école en octobre 2026) [Certain] | rien | élevé | faible pour nous |
| **Enzo** | « Enzo Public License » [Certain pour le nom, texte non lu] | port CUDA partiel (hydro et MHD) [Certain, article 2014] | non mentionné | AMR, Grackle, formation d'étoiles [Probable] | rien | élevé | faible |
| **ChaNGa** | GPL [Certain] | non mentionné sur les pages lues ; il existe des travaux GPU [À vérifier] | Unix, Charm++ [Certain] | arbre + SPH, refroidissement des métaux, formation d'étoiles par H₂, superbulles, trous noirs [Certain] | rien | élevé | faible |
| **GAMER-2** | « open source » [Certain] ; BSD-3 de mémoire [À vérifier] | **oui, CUDA** : hydro, Poisson, pas de temps [Certain] | non mentionné → WSL2 avec CUDA | le seul code complet pensé GPU : AMR, gravité, particules, **Grackle**, formation d'étoiles [Certain] | notre gaz, en théorie | très élevé (grille contre nos particules, couplage au film) | fort pour le gaz, mais **occupe la carte** |
| **Shamrock** | CeCILL 2.1 [Probable, résumé] | **oui, SYCL compilé en CUDA** [Certain] | non mentionné | SPH du schéma Phantom, 25 M particules/s sur une H100 [Certain] ; **pas encore d'autogravité** [Probable] | rien aujourd'hui | — | à revoir quand la gravité arrive |
| **Phantom** | GPL-3 [Certain] | non mentionné | macOS et grappes ; Windows non mentionné | SPH de référence (Fortran), potentiels galactiques, chimie H₂, puits [Certain] | rien | — | lecture utile pour le schéma |

### 2.2 Gravité seule sur carte graphique

| Code | Lic. | GPU | Win | Remplace | Effort | Gain |
|---|---|---|---|---|---|---|
| **Bonsai** | Apache 2.0 [Certain] | tout l'arbre sur GPU [Certain] ; capacité 3.0 et plus, compilé à l'époque avec CUDA 5.5, Tesla « plus supportée » [Certain] | Linux seulement dans la doc [Certain] | `gravite_gpu.py` | élevé : portage Windows, Blackwell (sm_120), dépôt figé (copyright 2010–2017) [Certain] | **faible** : même méthode que la nôtre. Bonsai-SPH (2019, noyaux Wendland, Courant à 0,3) se **lit** comme référence pour le gaz |
| **PeTar** | MIT [Certain] | optionnel, forces de l'arbre [Certain] | Linux seulement [Certain] | rien : amas d'étoiles sans adoucissement, binaires, SSE/BSE [Certain] | — | hors sujet |
| falcON / pyfalcon | GPL [Probable] | non | déjà utilisé chez nous avant le GPU [Certain, `gravite_gpu.py`] | déjà remplacé | — | reste un arbitre gratuit pour la gravité |

### 2.3 Petits corps et système solaire

| Code | Lic. | GPU | Win | Remplace | Effort | Gain |
|---|---|---|---|---|---|---|
| **REBOUND** 5.2.2 (5 oct. 2026) | GPL-3 (PyPI « GPL-3.0-only », texte « ou toute version ultérieure ») [Certain, contradiction relevée] | non (OpenMP, AVX512) [Certain] | **Windows natif, paquets pip pour Windows** [Certain] | **référence** de `nbody_noyau.h` : IAS15 (pas adaptatif, précision machine), WHFast, MERCURIUS et TRACE pour les rencontres proches ; relativité via REBOUNDx [Certain] | faible : `pip install rebound`, un script de comparaison | moyen : contrôle indépendant de notre Wisdom-Holman, et des comètes et astéroïdes qui frôlent les planètes (là où un Wisdom-Holman à pas fixe se trompe) [Probable] |

### 2.4 Conditions initiales

| Code | Lic. | GPU | Win | Remplace | Effort | Gain |
|---|---|---|---|---|---|---|
| **AGAMA** 1.0.0 (18 nov. 2025) | champ PyPI « GPL, MIT, BSD », sans détail [Certain] | non mentionné | **compilation MSVC documentée** (GSL requis), pas de paquet tout fait [Certain] ; chez nous, tâche GitHub | **déjà adopté** | — | déjà acquis ; l'étape suivante est le **modèle auto-cohérent** (section 5 de l'article) pour que disque, bulbe et halo soient à l'équilibre ensemble [Probable] |
| **galpy** | BSD-3 [Certain] | non | intégration continue sous Windows [Certain] | rien ; AGAMA fait mieux pour les conditions de départ | faible | faible : contrôle d'orbites |
| **MUSIC2 / monofonIC** | non lue [À vérifier] | non mentionné | non mentionné | rien : conditions **cosmologiques** (LPT au 3e ordre) pour GADGET, AREPO, RAMSES [Certain] | — | aucun avec le plan B+ |
| **genetIC** | non lue [À vérifier] | non mentionné | non mentionné | rien : conditions cosmologiques « modifiées » pour zoomer sur un halo voulu, précision sous le pour cent [Certain] | — | seulement si un jour on refait un Groupe local à la HESTIA |

### 2.5 Physique du gaz et des étoiles

| Code | Lic. | GPU | Win | Remplace | Effort | Gain |
|---|---|---|---|---|---|---|
| **Grackle** | bibliothèque : non lue [À vérifier] ; gracklepy : BSD-3 [Certain] | non mentionné | aucun paquet Windows (Linux et macOS seulement) [Certain] ; C99 + Fortran + HDF5 | **notre gaz isotherme** : refroidissement primordial et des métaux (tables Cloudy), chauffage par le fond UV (Faucher-Giguère 2009 ou Haardt & Madau 2012) [Certain] | **faible si on prend les tables** (fichiers HDF5) et qu'on les interpole dans notre noyau GPU ; élevé si on lie la bibliothèque | **fort** : le gaz passe d'une température fixe à un gaz qui chauffe et refroidit, condition pour avoir du gaz chaud et des bras qui se refont [Probable] |
| **MESA** | LGPL-3 [Certain] | non | **WSL2 ou Docker seulement**, pas de natif [Certain] | rien : MIST *est* une grille MESA [Certain] | — | aucun de plus que MIST |
| **MIST** (données) | CC BY 4.0 pour la copie Zenodo (Kiauhoku) [Certain] ; site d'origine non lu | — | — | déjà adopté | — | acquis |
| **python-fsps** | MIT, avec conditions d'usage de FSPS à lire [Certain] | non | non mentionné ; demande un compilateur Fortran [Certain] | complète MIST : spectre complet par population, émission nébulaire, poussière [Certain pour la fonction] | moyen | moyen : couleurs plus justes pour les régions jeunes |
| **py-ananke** 0.6.0 | AGPL-3 ou GPL-3 (le paquet se contredit) [Certain] | non | **Unix seulement** [Certain] | `etoiles_visibles_masse.py` | moyen (WSL2) | faible : on a déjà la même idée, et ses isochrones sont Padova, MIST seulement « prévu » [Certain] |
| **SKIRT** | AGPL-3 [Certain] | non mentionné | non lu [À vérifier] | rien aujourd'hui : poussière par transfert de rayonnement, pour dessiner de vraies bandes sombres à partir de notre gaz | élevé | fort pour le **rendu** quand le gaz sera bon, pas pour la physique |

### 2.6 Données de calibration

| Données | Accès | Ce que ça calerait | Label |
|---|---|---|---|
| **Gaia DR4** | **prévue le mercredi 2 décembre 2026** ; 66 mois d'observation ; `gaia_source` 2,0 milliards de lignes ; **312 M vitesses radiales** (DR3 : 33,8 M) ; astrométrie par époque 62 To ; **~400 To en tout** | les deux tiers des étoiles Gaia de l'appli **sans vitesse radiale** (prise nulle aujourd'hui) en auraient une pour beaucoup plus d'étoiles ; barre et bras mesurés plus loin | [Certain pour la date et les nombres, page ESA lue ; DR3 33,8 M : Probable] |
| **PHANGS** (HST, JWST, ALMA, MUSE) | CC BY 4.0 [Certain] ; HST : 38 spirales, 5 bandes, ~100 000 amas d'étoiles catalogués ; JWST : 19 galaxies, 8 filtres [Certain] | l'**efficacité de formation d'étoiles** et le **temps d'épuisement du gaz** mesurés zone par zone dans de vraies spirales : de quoi vérifier nos « 1 % par temps de chute libre » et « 0,1 cm⁻³ » au lieu de les supposer | [Certain pour le contenu ; Probable pour l'usage] |

---

## 3. Licences : ce que ça change pour nous

L'appli est **privée**, un seul utilisateur, et elle n'est pas distribuée. Les licences GPL, LGPL et AGPL
n'imposent rien tant qu'on ne distribue pas le programme ; l'AGPL ajoute le cas d'un service offert à d'autres sur
un réseau, ce qui n'est pas le cas ici. [Probable, lecture courante de ces licences ; je ne suis pas juriste]

Conséquence pratique : **on peut tout utiliser**. La seule règle à se donner : garder ces codes **à côté** de l'appli
(outils de calcul, scripts de contrôle, données) plutôt que de les coller dans le binaire. Si un jour Univers est
publié, il n'y aura rien à démêler. Les données (MIST, PHANGS, Gaia) demandent seulement de citer la source, ce que
l'appli fait déjà.

---

## 4. Ce qui changerait vraiment la précision, classé

| Rang | Action | Code repris | Gain attendu | Effort | Label |
|---|---|---|---|---|---|
| 1 | **Faire refaire nos galaxies de départ par un code pro** (Voie lactée seule, 3 Ga, sans gaz puis avec), sur processeur sous WSL2, et comparer la vitesse de la barre, sa taille et l'épaisseur du disque à nos tirs GPU | GADGET-4 (gravité) puis GIZMO (gaz) | **tranche si nos écarts viennent du moteur ou du modèle** ; c'est la question qui bloque le prochain film | 1 à 2 jours de fil, puis des heures de processeur, **sans toucher la carte** | [Supposition] |
| 2 | **Gaia DR4** dès le 2 décembre : vitesses radiales et astrométrie à jour pour les étoiles de l'appli | données | fort : moins d'étoiles « vitesse supposée » | moyen ; stockage à demander à Marc (une sélection, pas les 400 To) | [Certain pour la date] |
| 3 | **Refroidissement et chauffage du gaz** à partir des tables de Grackle, interpolées dans `gaz_gpu.py` | tables Grackle (Cloudy) | fort pour le gaz | moyen | [Probable] |
| 4 | **Pas de temps par particule** (ou par groupes de puissances de 2), au moins pour le gaz | idée de GADGET, Bonsai-SPH, Phantom ; pas leur code | fort pour les chocs de la rencontre (voir le calcul du § 1) | moyen | [Supposition] |
| 5 | **Noyau de Wendland et interrupteur de viscosité de Cullen et Dehnen** dans le SPH | méthode publiée (Dehnen & Aly 2012 : les noyaux de Wendland évitent l'instabilité d'appariement quel que soit le nombre de voisines) | moyen : moins de viscosité parasite dans un disque qui tourne, convergence meilleure | faible | [Certain pour Dehnen & Aly, résumé lu ; Probable pour le gain chez nous] |
| 6 | **Calage de la formation d'étoiles sur PHANGS** | données | moyen : les paramètres deviennent mesurés | faible à moyen | [Probable] |
| 7 | **REBOUND IAS15 comme contrôle** du système solaire et des rencontres proches de comètes | REBOUND | moyen, localisé | faible | [Probable] |
| 8 | Rétroaction des explosions d'étoiles | méthode publiée (GIZMO public, GADGET) | fort à terme, mais à faire après 3 et 4 | élevé | [Supposition] |

---

## 5. Recommandation

**Adopter :**
- **AGAMA** : garder, et passer au modèle auto-cohérent quand on refera les galaxies de départ.
- **GADGET-4, puis GIZMO, sous WSL2, comme arbitres.** Pas dans l'appli : comme banc d'essai qui refait nos galaxies
  de départ. C'est le meilleur rapport gain/effort de ce document, et il ne prend pas la carte graphique au fil qui
  l'utilise. [Probable]
- **Les tables de Grackle** pour le refroidissement, lues par notre noyau GPU. On prend les données, pas la
  bibliothèque, qui n'existe pas pour Windows.
- **REBOUND** (pip, Windows natif) comme référence du système solaire.
- **Gaia DR4** et **PHANGS** comme données de calibration.

**Garder maison :**
- **La gravité GPU.** Même famille que Bonsai, déjà contrôlée (énergie à 0,04 % sur le deuxième film). Changer de
  moteur coûterait cher pour rien. [Probable]
- **Le moteur de gaz SPH**, à condition de lui ajouter le pas de temps adapté, le noyau de Wendland, l'interrupteur
  de Cullen et Dehnen et le refroidissement. Aucun code pro ne fait du gaz sur GPU sous Windows avec notre gravité ;
  GAMER-2 est le seul candidat sérieux, mais il travaille sur une grille, prendrait la carte et demanderait de tout
  recoupler. [Probable]
- **La lumière des étoiles** (MIST) et le tirage des étoiles visibles. FSPS seulement si les régions jeunes sortent
  de mauvaise couleur.

**Ne pas prendre :** MESA, MUSIC, monofonIC, genetIC, PeTar, ChaNGa, SWIFT, RAMSES, Enzo, Bonsai, Ananke, Shamrock
(pour l'instant). Les raisons sont dans le tableau.

Ce que je ne recommande **pas**, et pourquoi : remplacer notre gaz par AREPO ou GIZMO pour le film. Ce serait plus
juste sur le papier, mais sur processeur seul, sous Linux, sans lien avec le film ni avec la gravité GPU déjà
validée. On perdrait des semaines d'intégration pour un gain qu'on peut mesurer d'abord avec l'arbitre (rang 1).
[Supposition]

---

## 6. Prochaines étapes proposées (rien n'est lancé)

1. Vérifier que WSL2 est installé sur le PC de Marc (geste de Marc si ce n'est pas le cas : droits administrateur).
2. Fil « arbitre » : convertir `voie_lactee.npz` au format GADGET, tir de 3 Ga sans gaz sur processeur, comparaison
   avec `stabilite_tir.py` sur les mêmes mesures (barre, épaisseur).
3. Fil gaz : relever le nombre de Courant réel d'un tir de `film-3` ; s'il dépasse 0,3, pas de temps adapté avant
   toute autre chose.
4. Demander à Marc la place pour une sélection de Gaia DR4 avant le 2 décembre.

---

## 7. Sources lues pour ce document

Codes de simulation :
- GADGET-4 : https://wwwmpa.mpa-garching.mpg.de/gadget4/01_index/ ; https://ar5iv.labs.arxiv.org/html/2010.03567
- AREPO : https://arepo-code.org/about-arepo ; https://ar5iv.arxiv.org/html/1909.04667
- GIZMO : https://ar5iv.arxiv.org/html/1712.01294 ; https://ascl.net/1410.003
- SWIFT : https://sourceforge.net/projects/swiftsim/ ; https://web3.arxiv.org/abs/2505.14538 (GPU, 2025)
- RAMSES : https://ramses.cnrs.fr ; https://github.com/pkestene/ramsesGPU ; https://arxiv.org/pdf/1412.0934
- Enzo : https://enzo.readthedocs.io/en/enzo-2.5/index.html
- ChaNGa : https://github.com/N-BodyShop/changa ; https://faculty.washington.edu/trq/hpcc/tools/changa.html
- GAMER-2 : https://ar5iv.arxiv.org/html/1712.07070
- Shamrock : https://shamrock-code.github.io ; https://arxiv.org/html/2503.09713v1
- Phantom : https://phantomsph.readthedocs.io/ ; https://ar5iv.arxiv.org/html/1702.03930
- Bonsai : https://github.com/treecode/bonsai ; https://ar5iv.arxiv.org/html/1909.07439 ; https://ar5iv.arxiv.org/html/1412.0659
- PeTar : https://github.com/lwang-astro/PeTar

Bibliothèques :
- REBOUND : https://pypi.org/project/rebound ; https://rebound.hanno-rein.de/
- AGAMA : https://pypi.org/project/agama ; https://github.com/astronom4ek/Agama/blob/master/INSTALL ; https://ar5iv.arxiv.org/html/1802.08239
- galpy : https://www.github.com/jobovy/galpy
- MUSIC2-monofonIC : https://ui.adsabs.harvard.edu/abs/2020ascl.soft08024H/abstract
- genetIC : https://ui.adsabs.harvard.edu/abs/2020arXiv200601841S
- Grackle : https://github.com/grackle-project/grackle ; https://grackle.readthedocs.io/en/latest/ ; https://pypi.org/project/gracklepy/
- MESA : https://docs.mesastar.org/en/latest/windows-install.html ; https://github.com/MESAHub/mesa
- MIST : https://ui.adsabs.harvard.edu/abs/2016ApJ...823..102C ; https://zenodo.org/records/14908017
- python-fsps : https://python-fsps.readthedocs.io/
- py-ananke : https://pypi.org/project/ananke/
- SKIRT : https://www.github.com/SKIRT/SKIRT8
- Dehnen & Aly 2012 : https://ar5iv.arxiv.org/html/1204.2471

Données :
- Gaia DR4 : https://www.cosmos.esa.int/en/web/gaia/dr4 ; https://www.cosmos.esa.int/web/gaia/news-2026
- PHANGS : https://archive.stsci.edu/hlsp/phangs/phangs-hst ; https://archive.stsci.edu/hlsp/phangs/phangs-jwst

Notre code : branche `film-3` (PR 102) pour `pipeline/fusion/` ; `appli-pc` pour `natif/` ; `docs/deuxieme-film.md` ;
`docs/refonte-simulations-pro.md` (PR 95).

## 8. Limites

- Les dépôts GitHub des codes n'ont pas pu être ouverts directement depuis ce fil (accès refusé) : les licences
  viennent des pages officielles, de PyPI ou des articles. Celles marquées [À vérifier] (AREPO, RAMSES, GAMER-2,
  Grackle, MUSIC, genetIC) demandent un coup d'œil au fichier LICENSE.
- Les efforts et les gains sont des estimations, pas des mesures. Le rang 1 sert justement à mesurer.
- Je n'ai pas vérifié si WSL2 est installé sur le PC.
