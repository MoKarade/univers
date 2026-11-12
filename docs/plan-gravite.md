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
