# Plan « précision maximale » : précalcul sur la carte graphique (12 novembre 2026)

Demande de Marc : « au mieux pour max de précision ». Le PC peut calculer longtemps, sur la carte graphique (RTX 5080, 16 Go). Ensuite l'appli rejoue les vrais déplacements.

Règle de vérité : chaque chiffre ci-dessous est **[mesuré]** (sur ce PC, ou publié avec sa source) ou **[estimation]** (à remplacer par une mesure dès le premier essai).

## 0. Où le calcul ne sert plus à rien (limites des mesures et du modèle)

| Domaine | Ce qui limite | Chiffre |
|---|---|---|
| Étoiles, au-delà d'environ 100 Ma | **modèle** de la Voie lactée : vitesse de rotation au Soleil connue à environ ±2,5 % (224 à 236 km/s) | [mesuré, essai_epicycles] à +100 Ma, l'écart médian vaut 1,6 kpc et 10° ; à +500 Ma, 6,6 kpc et 45°. Même départ, seul le modèle change. |
| Étoiles, vitesse de la barre (33 à 41 km/s/kpc) | modèle | [mesuré] 0,13 kpc à 100 Ma ; 1 kpc à 500 Ma (médiane) |
| Étoiles, bras spiraux | modèle : leur vitesse n'est pas établie, ils ne sont pas dans le calcul | non chiffrable sans eux |
| Étoiles sans vitesse radiale mesurée | **mesure** manquante : une composante de la vitesse est inconnue | à chiffrer avec les clones (§1) |
| Fusion Voie lactée–Andromède | **mesure** du mouvement propre d'Andromède (48,9 ± 10,5 ; −36,9 ± 8,1 µas/an, Salomon 2021) et des masses | [publié, Sawala et al. 2025, Nature Astronomy] fusion dans 54 % des cas en 10 Ga ; médiane 7,6 Ga pour les cas qui fusionnent. Plus de particules ne change pas cette probabilité. |
| Système solaire au-delà d'environ 50 Ma | **chaos** : deux départs écartés de quelques mètres divergent complètement | [publié, Laskar et al. 2011, La2010] horizon d'environ 50 Ma, à confirmer ici par des clones |
| Lunes des planètes géantes hors des fichiers NASA | pas de théorie valable sur des siècles | inconnu (déjà caché dans l'appli) |

Conséquence pour l'affichage : au-delà de l'horizon, l'appli montre le nuage des possibles (clones) et non une position unique.

## 1. Étoiles : calcul exact et incertitudes de mesure

- **Calcul exact en temps réel** (fil natif) : nuanceur de calcul qui porte `Potentiel::acc` et le saut de grenouille, en float32. [mesuré] Sur le processeur : 7,9 ns par étoile et par pas, sur 32 fils. [estimation] Sur la carte : 0,05 à 0,3 ms par pas pour 6,15 M d'étoiles.
- **Clones d'incertitude** (précalcul) : 32 clones par étoile, tirés dans les erreurs mesurées par Gaia (parallaxe, mouvements propres, leurs corrélations, vitesse radiale). Une vitesse radiale non mesurée est tirée parmi les vitesses mesurées des étoiles voisines, et l'appli le signale.
  - Mémoire : 32 clones × 24 octets = 768 o/étoile. Pour 6,15 M d'étoiles, 4,7 Go de mémoire vidéo : ça passe en une fois. Pour les 98 M d'étoiles Gaia, il faut des lots.
  - Temps [estimation, base mesurée de 7,9 ns] : pour 6,15 M d'étoiles × 32 clones × 1 000 pas (1 Ga), 26 min sur le processeur. Sur la carte, quelques minutes. Pour les 98 M d'étoiles Gaia, 7 h sur le processeur ; sur la carte, je ne sais pas encore (à mesurer).
  - Disque : on garde par étoile l'écart des clones à 12 dates (de 10 000 ans à 1 Ga), en float16. Soit 24 o/étoile : 150 Mo pour etoiles.bin, 2,4 Go pour Gaia.
  - Téléchargement nécessaire : les colonnes d'erreur de Gaia DR3 pour les 98 M d'étoiles, environ 4 Go [estimation]. **Accord de Marc requis.**
- Contrôle : comparer le calcul sur carte au calcul double précision (`Orbites`) sur l'échantillon de essai_epicycles. Exiger une médiane sous 1 pc et un 99 % sous 10 pc.

## 2. Fusion avec Andromède

1. **Clones du Groupe local** (processeur, minutes) : reprendre la méthode publiée de Sawala et al. 2025 (code public github.com/TillSawala/MW-M31). Voie lactée, M31, M33, LMC et SMC ; masses, distances, mouvements propres et vitesses de leur tableau 1. Frottement dynamique de Chandrasekhar partagé entre les deux galaxies ; pas de 1 Ma ; 5 000 tirages. Contrôle : retrouver leurs 54 % ± 2.
2. **Vrai N-corps haute résolution** (carte graphique, Vulkan) pour quelques clones représentatifs (médiane des fusions, cas sans fusion). Somme directe des forces ou arbre.
   - [estimation] 2 M de particules, environ 2 s par pas, 20 000 pas : environ 11 h par scénario. À mesurer sur un premier essai court.
   - Disque : environ 12 Go par scénario (positions sur 16 bits, 1 000 images). **Prévenir Marc au-delà de quelques dizaines de Go.**
   - Gain attendu : centres et étoiles moins bruités que R9 (300 k particules, falcON). Mesuré par la dérive d'énergie et l'écart des centres entre résolutions. Le gain porte sur le *détail*, pas sur la date de fusion.

## 3. Système solaire longue durée

- Aujourd'hui : table à ±10 Ma, contrôlée contre La2004 (corrélation 0,99 à 4 Ma, 0,74 à 10 Ma).
- Précalcul : modèle enrichi (aplatissement du Soleil J2, plus d'astéroïdes, marées Terre-Lune) et clones écartés de quelques mètres, jusqu'à ±60 Ma. Le calcul se fait sur le processeur (13 corps : la carte n'aide pas), un clone par fil.
- [estimation] Environ 30 h pour 32 clones et 60 Ma par sens, d'après la vitesse du calcul actuel. À mesurer.
- Disque : quelques dizaines de Mo.
- Gain mesuré : accord avec La2010 (fichiers publics de l'IMCCE) au-delà de 10 Ma ; horizon chaotique mesuré par les clones.

## Ordre

1. Clones du Groupe local (rapide, change ce que l'appli affiche pour la fusion).
2. Nuanceur d'intégration exacte et outil de précalcul des clones d'étoiles (avec les erreurs Gaia après accord).
3. Système solaire ±60 Ma (tourne en fond sur le processeur).
4. N-corps haute résolution de la fusion.
