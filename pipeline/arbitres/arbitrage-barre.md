# Arbitrage de la barre de la Voie lactée : notre moteur ou le modèle de masse ? (18/11/2026)

Question (docs/deuxieme-film.md, écarts 1 à 3) : la barre tourne trop lentement (~20 km/s/kpc pour 39 mesurés), grossit
sans arrêt, et le disque s'épaissit trop. Vient-ce de notre moteur GPU (pas fixe de 0,25 Ma, adoucissement de Plummer,
arbre en simple précision) ou du modèle de masse de départ ?

Méthode : refaire le même mûrissement avec GADGET-4, un code de référence indépendant, et comparer les mêmes mesures.
Labels : [Certain] mesuré ici ; [Probable] déduit ; [À vérifier].

## Verdict : c'est le MODÈLE, pas le moteur [Probable, fort]

GADGET-4, parti du même départ avec la même barre guide, donne la même barre lente, la même barre qui grossit et le même
épaississement que notre moteur. Les écarts entre les deux codes sont bien plus petits que l'écart aux mesures réelles.

| | Notre tir GPU (3,5 M) | GADGET-4 (1 M) | Mesuré dans la vraie Voie lactée |
|---|---|---|---|
| Vitesse de la barre à +2 Ga | 25 km/s/kpc | 25 km/s/kpc | 39 km/s/kpc |
| Vitesse de la barre à +3 Ga | 20 km/s/kpc | 17 km/s/kpc | 39 km/s/kpc |
| Force A2, anneau 4–6 kpc, +3 Ga | 0,34 | 0,45 | — |
| Longueur de la barre, +3 Ga | non relevée | 6,8 kpc (7,2 à +2,5 Ga) | 5,0 kpc |
| Épaisseur des vieilles étoiles, 4–6 kpc, plan xy : 0 → +3 Ga | 0,45 → 0,71 kpc | 0,45 → 0,62 kpc | ~0,2–0,3 kpc |
| Dérive d'énergie sur 3 Ga (E/E₀ − 1, barre guide comprise) | −1,7 × 10⁻³ | −1,8 × 10⁻³ | — |

Tous les chiffres des deux codes : [Certain] (mesurés par les mêmes fonctions). Valeurs réelles : celles citées dans
docs/deuxieme-film.md et modeles_v2.py.

Ce que GADGET-4 change par rapport à notre moteur, sans que le résultat change :
- pas de temps individuels et adaptatifs, le plus petit étant de 0,09 Ma, contre notre pas fixe de 0,25 Ma ;
- noyau d'adoucissement en spline (Plummer équivalent), contre Plummer ;
- arbre en double précision, avec le critère d'ouverture géométrique θ = 0,7 et les quadripôles, comme le nôtre ;
- intégrateur et code entièrement indépendants.

Puisque tous ces choix de moteur changent sans que la barre lente ni l'épaississement disparaissent, ces deux écarts viennent
du modèle de masse et du mûrissement : un halo sans rotation qui freine la barre, un disque central froid qui fait une barre
longue, et une barre qui épaissit le disque en flambant. [Probable]

## Évolution détaillée (mêmes instants)

A2 = force du motif à deux bras des étoiles du disque (sortes 1 et 4) par anneau ; Ωb = vitesse de la barre (angle de
l'anneau, relevés espacés de 10 Ma, médiane sur ±50 Ma) ; épaisseur = médiane de |z|.

| t (Ga) | A2 0,5–2 / 2–4 / 4–6 kpc : GPU | GADGET-4 | Ωb GPU | Ωb GADGET-4 | épaisseur 4–6 kpc GPU | GADGET-4 | GADGET-4 : A2 0,5–4 kpc, longueur, vieilles / jeunes (plan propre, 4–9 kpc) |
|---|---|---|---|---|---|---|---|
| 0,00 | 0,00 / 0,00 / 0,00 | 0,00 / 0,01 / 0,00 | (pas de barre) | (pas de barre) | 0,45 | 0,45 | 0,00, —, 0,47 / 0,09 kpc |
| 0,25 | 0,29 / 0,35 / 0,21 | 0,27 / 0,32 / 0,21 | 40 | 42 | 0,48 | 0,48 | 0,30, 3,8 kpc, 0,49 / 0,12 kpc |
| 0,50 | 0,18 / 0,23 / 0,04 | 0,12 / 0,19 / 0,05 | 34 | 37 | 0,51 | 0,53 | 0,16, 3,8 kpc, 0,55 / 0,14 kpc |
| 1,00 | 0,08 / 0,03 / 0,05 | 0,15 / 0,22 / 0,22 | 34 | 26 | 0,53 | 0,52 | 0,17, 4,2 kpc, 0,56 / 0,16 kpc |
| 1,50 | 0,17 / 0,26 / 0,14 | 0,27 / 0,43 / 0,21 | 28 | 25 | 0,54 | 0,54 | 0,34, 5,2 kpc, 0,59 / 0,18 kpc |
| 2,00 | 0,29 / 0,46 / 0,27 | 0,25 / 0,44 / 0,34 | 25 | 25 | 0,53 | 0,56 | 0,34, 6,8 kpc, 0,60 / 0,20 kpc |
| 2,50 | 0,33 / 0,52 / 0,36 | 0,31 / 0,53 / 0,42 | 22 | 20 | 0,55 | 0,58 | 0,41, 7,2 kpc, 0,61 / 0,22 kpc |
| 3,00 | 0,30 / 0,46 / 0,34 | 0,34 / 0,58 / 0,45 | 20 | 17 | 0,71 | 0,62 | 0,45, 6,8 kpc, 0,64 / 0,24 kpc |

- Jusqu'à 0,5 Ga, pendant que la barre guide (39 km/s/kpc) agit, les deux codes sont presque identiques [Certain].
- Une fois le guide retiré (1,0 Ga), la barre faite des étoiles ralentit dans les deux codes, de ~35 à ~20 km/s/kpc
  [Certain]. Dans GADGET-4, elle se reforme un peu plus tôt (1,0 Ga) et finit un peu plus forte.
- À 3 Ga, l'épaisseur de notre tir saute de 0,55 à 0,71 kpc dans l'anneau 4–6 kpc ; celle de GADGET-4 monte régulièrement
  jusqu'à 0,62. Cet écart de 0,1 kpc est la seule différence notable : c'est peut-être un flambage plus brusque dans notre
  tir, ou un effet du pas fixe [À vérifier]. Il ne change pas le verdict.
- Le plan propre du disque de GADGET-4 penche de moins de 1° en 3 Ga (galaxie seule) [Certain] : épaisseur dans le plan
  propre ≈ épaisseur dans le plan xy.

## Limites [à lire avant de conclure plus loin]

1. **Résolution différente** : GADGET-4 à 1 M de particules (tirage au hasard, mêmes proportions, masses multipliées
   d'autant, adoucissements gardés), contre 3,5 M pour notre tir. À 3,5 M, GADGET-4 aurait demandé environ 27 h
   (18,7 Ma simulés en 10 min, mesuré). Notre essai à 10,85 M (deuxieme-film.md, point 4) ne changeait ni la barre ni
   l'épaisseur. La résolution pèse donc peu [Probable]. Le léger surcroît de force de la barre dans GADGET-4 peut venir
   du bruit plus fort à 1 M [Supposition].
2. **Barre guide centrée sur l'origine** dans GADGET-4, contre le centre de masse courant dans notre tir. Le centre de
   masse est ramené à l'origine au départ ; pour une galaxie seule, sa dérive est négligeable [Probable].
3. **Épaisseur des jeunes étoiles** : notre tir de mûrissement ne la relevait pas. La valeur du film (0,10 → 0,64 kpc en
   3 Ga) se mesure après le mûrissement, avec les galaxies voisines : elle n'est pas comparable. Dans GADGET-4, pendant le
   mûrissement : 0,09 → 0,24 kpc [Certain].
4. **Énergie noire** : non ajoutée. Pour une galaxie seule de ~250 kpc sur 3 Ga, son accélération (Λ c² r / 3) est de
   l'ordre de 7 × 10⁻⁶ fois la gravité de la galaxie à 10 kpc (H₀² Ω_Λ r ≈ 0,034 contre v²/r ≈ 5 300 (km/s)²/kpc) : négligeable [Probable, ordre de grandeur].
5. Une seule réalisation de chaque côté : pas de barre d'erreur statistique.

## Ce que ça implique pour Univers

Changer de moteur ou de pas de temps ne corrigera ni la vitesse ni la croissance de la barre. Il faut agir sur le modèle :
donner au halo une rotation, partir d'un disque plus mince (mûrissement plus court), ou revoir la masse du disque central
(c'est la « suite proposée » de deuxieme-film.md, qui se trouve confirmée). [Probable]

## Reproduire

- Départ : `C:\tmp\analyse-architecture\galaxies\v9\voie_lactee_barre.npz` (modeles_v2.py, centre froid, sans barre ; c'est
  celui que `v9/murir.sh` a fait mûrir pour le deuxième film). Notre tir : `v9/voie_lactee_tir.json` (3,5 M, 3 Ga, relevés
  toutes les 10 Ma, barre guide 2e9 M☉, 5 kpc, 39 km/s/kpc, 0,3 + 0,2 + 0,5 Ga).
- GADGET-4 (révision c64a4a2), Ubuntu 24.04 sous WSL2, 8 processus MPI, processeur seul, de 13 h 35 à 19 h 39 (heure du
  Québec), soit 6 h 04 pour 3 Ga à 1 M de particules.
- Scripts (`pipeline/arbitres/barre/`) :
  - `appliquer_patch.sh` + `guide_barre.patch.cc` : ajoutent la barre guide (option `EXTERNALGRAVITY_GUIDEBAR`) à GADGET-4 ;
  - `Config.sh`, `param_modele.txt` : gravité seule, quadripôles, θ = 0,7 géométrique, sans PM ni boîte périodique ;
  - `preparer.sh` (compilation et conversion), `tir.sh` (lancement), `npz_vers_gadget.py` (conversion .npz → HDF5) ;
  - `mesurer.py` (mêmes mesures que stabilite_tir.py), `resume_gpu.py`, `comparer.py` (tableau ci-dessus) ;
  - `mesures_gadget_1M.json` : toutes les mesures GADGET-4, toutes les 50 Ma (+ paires à 10 Ma).
- Les instantanés (121 fichiers, ~3,9 Go) restent dans `~/arbitres/barre-1M/output` sous Ubuntu : ils ne vont pas dans le dépôt.

## Suite (nuit du 18 au 19/11) : candidats corrigés, vérifiés par GADGET-4

Départs `v16` : masses recalées (Voie lactée 1,07e12 M☉), centre calme. Même barre guide que plus haut, gravité seule,
sans gaz, 1 M de particules, 1,5 Ga, 8 cœurs. Le candidat « halo tournant » est identique, particule par particule, à
`v16/voie_lactee_barre_halo_tournant.npz` (429 076 vitesses retournées, paramètre de rotation 0,033–0,038) [Certain].
Durée : 3 h 13 par tir (mesuré).

| t (Ga) | Ωb, halo tournant : GADGET-4 | Ωb, témoin sans rotation : GADGET-4 | Ωb, notre moteur (v16, halo tournant) | Épaisseur 4–6 kpc : GADGET-4 tournant / témoin |
|---|---|---|---|---|
| 0,5 | 48 (guide encore actif) | 40 | 42,2 | 0,28 / 0,26 |
| 1,0 | 31,7 | 29,4 | 32,3 | 0,31 / 0,30 |
| 1,5 | 30,2 | 29,4 | 29,9 | 0,33 / 0,32 |

Correctif du 19/11 : une première version de ce tableau comparait à 38,1 / 36,8 / 34,8 km/s/kpc. Ces valeurs venaient
d'un autre départ (v13 avec barre guide). Les chiffres de notre moteur pour ce même départ v16 sont 42,2 / 32,3 / 29,9
(fil du calcul).

Autres mesures GADGET-4, halo tournant à 1,5 Ga : force de la barre A2 = 0,33, longueur 4,8 kpc ; au Soleil, disque mince
épais de 0,33 kpc (0,22 au départ), agitation radiale 52 km/s (28 au départ). Témoin : A2 0,37, longueur 5,8 kpc,
0,30 kpc, 51 km/s [Certain].

Lecture :
- Le nouveau modèle corrige l'essentiel de l'épaississement. Dans les deux codes, le disque reste près de 0,3 kpc, contre
  0,45 → 0,55 kpc avec l'ancien départ v9 [Certain].
- La barre est plus rapide qu'avec v9 : environ 30 km/s/kpc à 1,5 Ga dans GADGET-4, contre ~25 avant. Mais elle reste
  sous les 39 mesurés [Certain].
- Les deux codes sont d'accord sur ce départ : 31,7 / 30,2 km/s/kpc pour GADGET-4, 32,3 / 29,9 pour notre moteur à
  1 et 1,5 Ga [Certain]. Le pas fixe de notre moteur n'y est pour rien [Probable]. Dans GADGET-4, la rotation du halo ne
  gagne que 1 à 2 km/s/kpc sur le témoin [Certain].
- À +0,5 Ga, la barre guide n'est pas encore éteinte (descente de 0,5 à 1,0 Ga) : la vitesse n'est pas encore celle de la
  barre faite par les étoiles elles-mêmes.

### Andromède v16, halo tournant (19/11, fini à 9 h 00, heure du Québec)

Départ `v16/andromede_barre_halo_tournant.npz`, barre guide propre à Andromède (3e9 M☉, 4 kpc, 40 km/s/kpc, comme v9
et v17). **GADGET-4 tourne sans gaz** ; le tir de notre moteur auquel on compare a du gaz et des naissances d'étoiles.

| t (Ga) | Ωb GADGET-4 (sans gaz) | Ωb notre moteur (avec gaz) | A2 0,5–4 kpc | Longueur | Épaisseur 4–6 kpc |
|---|---|---|---|---|---|
| 0,5 | 29,7 (barre encore faible, A2 0,14) | 39,0 | 0,14 | 7,2 kpc | 0,46 kpc |
| 1,0 | 17,6 | 36,1 | 0,27 | 6,8 kpc | 0,50 kpc |
| 1,5 | 17,3 | 35,8 | 0,28 | 7,8 kpc | 0,50 kpc |

Ce qui est mesuré [Certain] :
- Sans gaz, la barre d'Andromède ralentit jusqu'à environ 17 km/s/kpc et s'allonge à 7–8 kpc. La valeur mesurée sur le
  ciel est d'environ 40 km/s/kpc et 4 kpc.
- Le disque s'épaissit de 0,37 à 0,50 kpc (4–6 kpc), et sa rotation moyenne y tombe de 210 à 134 km/s : il s'échauffe fortement.
- Le disque reste dans le plan xy, et tourne dans le même sens que la barre guide (plan propre incliné de moins de 1°).

Lecture : l'écart avec notre moteur (17 contre 36 km/s/kpc) est bien plus grand que pour la Voie lactée, où les deux
codes s'accordent. La différence de physique est la cause la plus probable : avec le gaz, la barre reste rapide ; sans
gaz, elle s'effondre [Probable]. Le témoin sans rotation du halo, qui tourne en ce moment, puis un tir de notre moteur
sans gaz sur le même départ, permettraient de le confirmer [À vérifier].

### Andromède v16, témoin sans rotation du halo (fini à 10 h 41, heure du Québec)

Même départ et même guide, sans rotation du halo, sans gaz : Ωb = 24,1 / 15,6 / 14,9 km/s/kpc à 0,5 / 1 / 1,5 Ga ;
A2 = 0,20 / 0,21 / 0,24 ; longueur 4,8 kpc ; épaisseur 4–6 kpc 0,37 → 0,50 kpc [Certain].
Lecture : la rotation du halo gagne 2 à 6 km/s/kpc (17,3 contre 14,9 à 1,5 Ga), mais sans gaz la barre d'Andromède
reste à moins de la moitié des ~40 mesurés [Certain]. Le gaz reste l'explication la plus probable de la vitesse de 36
trouvée par notre moteur [Probable] ; seul un tir de notre moteur sans gaz sur ce départ le prouverait [À vérifier].

Mesures complètes : `barre/mesures_vl_halo_tournant.json`, `barre/mesures_vl_temoin.json`,
`barre/mesures_m31_halo_tournant.json`, `barre/mesures_m31_temoin.json`. En cours : `v13/centre` avec halo tournant.
