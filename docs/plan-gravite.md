# Plan « gravité mutuelle et événements prédits » (12 novembre 2026, proposition)

Demande de Marc : une vraie attraction mutuelle (chaque corps tire sur les autres, y compris les petits sur les gros : le Soleil qui tourne autour du centre de masse, les astéroïdes déviés), à toutes les échelles, et des événements prédits calés sur les publications (fusion avec Andromède, éclipses, rencontres d'étoiles…).

Confiance : [Certain] vérifié ; [Probable] source connue, chiffre non relu ; [À vérifier].

## 1. Ce qui est impossible, dit franchement

- Faire s'attirer **tous** les objets de la page entre eux (6 millions d'étoiles, 5 millions de galaxies, 123 000 astéroïdes) : N² ≈ 10¹³ calculs par pas. Hors de portée d'un téléphone, et même d'un superordinateur à cette échelle de temps. [Certain]
- Pour les étoiles entre elles, ce serait aussi **inutile** : dans le disque de la Galaxie, le temps au bout duquel les attractions d'étoile à étoile changent une orbite (temps de relaxation) dépasse de loin l'âge de l'Univers ; seul compte le champ d'ensemble de la Galaxie, déjà calculé (S2). [Certain : Binney et Tremaine 2008, § 1.2]
- Pour les galaxies lointaines, ce serait **faux** : on ne connaît que leur position et leur vitesse d'éloignement, pas leur vitesse en 3D ; une simulation devrait inventer les deux composantes manquantes (interdit, règle 4). [Certain]
- Le système solaire est **chaotique** : au-delà de quelques dizaines de millions d'années, la position d'une planète intérieure sur son orbite ne peut plus être prédite (temps de Lyapunov ≈ 5 millions d'années). La forme des orbites reste calculable plus loin. [Probable : Laskar 1989 ; Laskar et Gastineau 2009, Nature 459, 817]

## 2. Architecture retenue : exact là où ça compte

| Niveau | Qui s'attire | Méthode | Contrôle contre la littérature |
|---|---|---|---|
| G1 Soleil autour du centre de masse | Soleil ← 8 planètes (masses mesurées) | Exact, à chaque image : le Soleil compense les planètes | Position du Soleil donnée par JPL Horizons (écart attendu : quelques km) |
| G2 Système solaire au-delà de ±3 000 ans | Soleil, 8 planètes, Pluton, Lune, Cérès, Vesta, Pallas, Hygie : **tous entre eux** | Intégrateur symplectique de Wisdom et Holman (1991), correction de relativité générale (avance du périhélie de Mercure), dans un Web Worker ; départ de l'éphéméride JPL DE440 | Retrouver DE440 et les séries VSOP87 à ±3 000 ans ; avance de Mercure 43″ par siècle ; énergie conservée ; comparaison à REBOUND (Rein et Tamayo 2015) |
| G3 Petits corps | Astéroïdes et comètes tirés par G2 (leur masse sur les planètes : négligeable, sauf les quatre gros de G2) | Particules test dans le champ de G2 : les astéroïdes regardés ou proches de la Terre, en direct | Rapprochements publiés par JPL (CNEOS) : Apophis le 13 avril 2029, retour de Halley en 2061 |
| G4 Étoiles | Champ de la Galaxie (déjà fait, S2), qui maintenant **bouge** (G5) ; étoiles doubles à orbite publiée (Alpha du Centaure, Sirius…) : vraie orbite à deux corps | Existant + orbites publiées des couples | Dates des 42 passages d'étoiles (Bailer-Jones 2022) inchangées |
| G5 Groupe local | Voie lactée, Andromède, Triangle, Grand Nuage : **tous entre eux**, avec le freinage par la matière noire (Chandrasekhar) ; les 38 naines tirées par ces quatre | Peu de corps, calcul dans la page | Recul de la Voie lactée sous le Grand Nuage (≈ 30 à 40 km/s, Petersen et Peñarrubia 2021) [Probable] ; Grand Nuage avalé dans ≈ 2,4 milliards d'années (Cautun et al. 2019) [Probable] ; orbite du Triangle (Patel et al. 2017) |
| G6 Fusion avec Andromède | 300 000 particules qui s'attirent toutes | Calcul déjà écrit (R9, falcON), fait à l'avance, rejoué (R10, R11) | Date de fusion contre Sawala et al. 2025 et la page (5,85 Ga) |
| G7 Au-delà du Groupe local | Pas de N-corps (voir § 1) | Expansion + champ de vitesses publié de Cosmicflows-4 | Dit tel quel dans la page |

Tout ce qui est lourd (G6, tables de G2 et G3 pour les longues durées) est calculé à l'avance et chargé à part : la page n'a plus que ≈ 0,44 Mo de marge.

## 3. Événements prédits, chacun comparé à sa source

Éclipses (déjà contrôlées sur 7 dates NASA, à étendre), passages de Mercure et Vénus devant le Soleil, rapprochements d'astéroïdes (liste JPL CNEOS), retours de comètes, conjonctions de planètes, passages d'étoiles (déjà), Grand Nuage avalé, fusion avec Andromède. Un test par famille : date calculée par la page contre date publiée, avec la tolérance écrite.

## 4. Ordre proposé

1. G1 + G2 + G3 (système solaire), avec les événements du § 3 qui en dépendent.
2. G5 (Groupe local qui s'attire), G4 (étoiles doubles).
3. G6 (fusion : calcul complet puis rejoué).

Chaque étape suit la boucle de `CLAUDE.md` (construire, quatre critiques, résumé).

## État au 12 novembre 2026 (fait sur la branche `gravite-mutuelle`)

- **G2, calcul** : `app/src/21_nbody.js`. Soleil, 8 planètes (barycentres), Pluton, Cérès, Vesta, Pallas, Hygie s'attirent tous ; Wisdom-Holman en coordonnées héliocentriques démocratiques, pas de 4 jours, relativité du Soleil (post-newtonien, Anderson et al. 1975), anneau Terre-Lune (Quinn, Tremaine et Duncan 1991). Départ : JPL Horizons (DE440) au 10 novembre 2026 ; vitesses calées sur DE440 de 1650 à 2450 (`pipeline/gravite/ajuste.js`, facteur 1,9 × 10⁻⁶ pour Mercure, ≤ 2 × 10⁻⁷ ailleurs).
  Mesuré (`app/test/nbody.test.js`) : à 1850, 2000, 2126 et 2350 (dates non utilisées pour le calage), écart à Horizons ≤ 2,6″ (Mercure), ≤ 0,5″ (Vénus), ≤ 0,1″ (Terre), ≤ 1,2″ (astéroïdes) ; énergie conservée à 4 × 10⁻⁸ sur 10 000 ans ; avance relativiste du périhélie de Mercure 42,8″ par siècle (attendu 42,98″) ; aller-retour sur 1 000 ans : 0,6 km.
- **G2, temps longs** : `pipeline/gravite/long.js` (points de reprise tous les 10 000 ans), comparé à La2004 par `pipeline/gravite/compare_la2004.js`. Résultat : voir plus bas quand le calcul est fini. Pas encore branché dans la page.
- **G1** : fiche du Soleil, ligne « Centre de masse du système solaire » (VSOP87 + masses DE440). Écart à Horizons ≤ 170 km de 1650 à 2450 (`app/test/bary.test.js`).
- **G3** : `app/src/22_smallbody.js`. Astéroïde ou comète = particule test tirée par le Soleil, les planètes, la Terre et la Lune séparément, relativité comprise ; Dormand-Prince 5(4) à pas adaptatif. Mesuré (`app/test/petits.test.js`) : 10 rapprochements de la Terre de la liste CNEOS (astéroïdes de plus de ≈ 300 m, moins de 0,01 UA d'ici 2045), dont Apophis le 13 avril 2029 : 38 027 km contre 38 011 km, à 0,3 min ; tous à moins d'une minute et 0,05 % de Horizons. Périhélie de Halley en 2061 à 0,05 jour de Horizons. Pour 536531, la liste CNEOS vient d'une orbite plus ancienne (16 min d'écart avec Horizons, que le calcul suit).
  Dans la page : l'astéroïde ou la comète touché (catalogue embarqué ou tuiles) suit sa trajectoire calculée, 100 ans de part et d'autre de la date de ses éléments ; le point dessiné reçoit à chaque image ses éléments osculateurs (écart point-calcul : 19 km pour Vesta, 190 km pour Halley, précision des nombres en simple précision) ; la fiche liste les passages à moins de 7,5 millions de km de la Terre. Non calculés, et dit : poussée des gaz des comètes, effet Yarkovsky.
- **Événements** : passages de Mercure et de Vénus devant le Soleil, 1600 à 2300, calculés par la page (`app/src/23_events.js`, `gen/transits.js`) ; contrôle (`app/test/evenements.test.js`) : de 2026 à 2200, les 23 passages de Mercure et les 2 de Vénus du catalogue de la NASA, aucun de plus, milieu à 2,3 min au plus, distance des centres à 0,5″. De 1600 à 2300 : 94 et 12 passages, comme le catalogue.

Pas encore fait : G2 branché dans la page au-delà de ±3 000 ans, G4, G5, G6.

## Planètes sur des millions d'années (12 novembre 2026)

- Calcul long (`pipeline/gravite/long.js`, sur le PC de Marc) : 21 Ma vers l'avenir (102 min), 20 Ma vers le passé (arrêté là). Énergie conservée à 2 × 10⁻⁸.
- Contrôle contre La2004 (Laskar et al. 2004, excentricité de la Terre, `compare_la2004.js`), corrélation par tranche d'un million d'années : avenir 0,9998 / 0,9986 / 0,97 / 0,98 / 0,93 / 0,98 / 0,94 / 0,86 / 0,84 / 0,79 / 0,84 (0 à 11 Ma), puis < 0,6 ; passé 0,9999 / 0,999 / 0,998 / 0,993 / 0,987 / 0,966 / 0,953 / 0,84 / 0,90 / 0,79 / 0,74. Au-delà d'environ 10 Ma, notre calcul s'écarte de la référence (Lune moyennée en anneau, pas de marées ni d'aplatissement du Soleil).
- Donc la page n'utilise la table que sur ±10 Ma (`orbites_planetes.txt`, 2,1 Mo, joint) ; au-delà : « position inconnue », orbites figées indicatives.
- Lecture de la table (`app/test/long.test.js`, extrait ±200 000 ans) : 0,2° pour les planètes rocheuses, 1° pour les géantes (Jupiter et Saturne lues tous les 250 ans).
