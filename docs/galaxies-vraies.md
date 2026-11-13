# Galaxies « vraies » dès aujourd'hui (appli PC)

Demande de Marc, 13 novembre 2026 : voir la Voie lactée entière dès maintenant, puis « selon les vraies images, les vraies
régions ». Ce document dit ce qui est mesuré, ce qui est modèle et ce qui ne ressemble pas encore.

## Andromède, Triangle, Grand et Petit Nuage de Magellan : vraies photos

- Script : `pipeline/natif/galaxies_images.py` -> `galaxies-images/` (quatre PNG de 1024 px et `galaxies_images.tsv`,
  3 Mo en tout), rangés par `natif/installer.ps1`. Affichage : `natif/src/galaxies_images.h`,
  `shaders/galaxie_image.vert|frag`.
- Photos [Certain] : M31 et M33, Digitized Sky Survey 2 (plaques bleue et rouge) ; Nuages, mosaïque de tout le ciel de
  Mellinger 2009 (rouge, vert, bleu), le DSS2 du Grand Nuage ayant des trous et des zones brûlées entre plaques. Les deux
  par le service SkyView de la NASA. Le service HiPS du CDS (hips2fits) et VizieR à Strasbourg ne répondaient pas le
  13/11/2026 ; le miroir de VizieR à Harvard répondait.
- Traitement : fond du ciel retiré autour de la galaxie, étoiles de premier plan retirées (point plus brillant que la
  médiane locale de plus de 5 écarts types), amas globulaires de la Voie lactée devant le Petit Nuage masqués (47 Tuc,
  NGC 362), bord adouci sur une ellipse. Couleur DSS2 : vert fabriqué (moyenne rouge-bleu).
- Mise en 3D : chaque pixel est une direction du ciel vue du Soleil, prolongée jusqu'au plan du disque défini par
  l'angle de position et l'inclinaison publiés, à la distance de l'astre dans l'appli. Vue d'ici : la photo.
- Éclat : somme de la photo recalée sur la magnitude absolue V publiée (même loi que les étoiles) ; éclat de surface
  divisé par |cos θ| selon l'angle de vue.

Limites [À vérifier / modèle] :
- disque supposé mince : vu de face, Andromède (inclinée de 77°) est étirée 4,4 fois sur son petit axe et floue ;
- côté proche du disque de M33 non vérifié dans les publications ;
- Petit Nuage posé face à nous (il est épais et allongé le long de la ligne de visée) ;
- les plaques photographiques ne sont pas linéaires : les rapports d'éclat à l'intérieur d'une galaxie sont approchés ;
- un reste de voile bleuté autour du Grand Nuage vient de la mosaïque ;
- le Petit Nuage n'est pas dans le calcul de la fusion : sa photo s'éteint avec les étoiles mesurées.

## Voie lactée vue de dessus : régions mesurées

- Script : `pipeline/natif/voie_lactee.py` (format `UNIVMW02` : vieilles étoiles, poussière, jeunes étoiles des bras,
  régions HII), shader `shaders/voie_lactee.frag`.
- Mesuré : bras de Reid et al. 2019 (masers à parallaxe) sur leur étendue mesurée ; 1 413 régions HII du catalogue
  WISE (Anderson et al. 2014) qui ont une distance, à leur place et à leur taille ; barre (5 kpc, ~27° de la ligne
  Soleil-centre) et bulbe (Bland-Hawthorn & Gerhard 2016) ; poussière mesurée près du Soleil (Edenhofer et al. 2024) ;
  étoiles Gaia une à une près du Soleil (étoiles OB et amas jeunes compris).
- Modèle, dit à l'écran : prolongement des quatre grands bras au-delà des portions mesurées (angle d'enroulement ~12°,
  au plus 180° d'azimut, éclat atténué à 40 %) ; part de lumière portée par les bras ; éclat des régions HII ; bandes
  de poussière sur le bord intérieur des bras ; couleurs par population.
- Affichage : la lueur est compressée sur sa luminance (ln(1 + Y)) pour que le bulbe ne passe pas au blanc.
- Carte de contrôle : rendu de l'appli contre la carte des régions mesurées (C:\tmp\vl-entiere\comparaisons2).

## Nuage des scénarios d'orbite

Caché par défaut ; Menu, « Incertitude : routes possibles des galaxies ». Option de contrôle `--incertitude`.

## À remplacer (Marc, 13/11/2026, 13 h 11)

« La Voie lactée c'est une image, pas ce que je veux » : la lueur vue de dessus (grille de lumière) doit être remplacée
par une Voie lactée faite d'étoiles en 3D (Gaia là où il mesure, étoiles tirées d'un modèle de population publié au-delà,
niveaux de détail sur la carte graphique). Travail suivant, sur sa propre branche. Les photos des galaxies voisines
restent.
