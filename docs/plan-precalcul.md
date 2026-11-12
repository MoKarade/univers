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
| Fusion Voie lactée–Andromède | **mesure** du mouvement propre d’Andromède (Wu et al. 2025 : 45,9 ± 8,1 ; −20,5 ± 6,6 µas/an) et des masses | [mesuré ici, reproduit Wu et al. 2026] fusion dans 90 % des cas en 10 Ga ; date médiane 6,4 Ga, de 4,9 à 7,6 Ga (16 à 84 %). Plus de particules ne change pas cette fourchette. |
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

## Résultats

### Clones du Groupe local (12/11/2026) [mesuré]
`pipeline/fusion/groupe_local_clones.py` reprend le code public de Sawala et al. 2025, vectorisé, et le fait tourner sur le processeur. Il a deux variantes :
- **sawala2025** : mouvement propre de M31 de Salomon et al. 2021. 5 000 tirages, 98 s.
- **wu2026** (par défaut) : Wu, Huang, Zhang, Sun & Shao 2026, arXiv:2603.22863. Mouvement propre de M31 de Wu et al. 2025 (45,9 ± 8,1 ; −20,5 ± 6,6 µas/an), le plus récent et le plus précis, déjà retenu par la page et par R9. 10 000 tirages, 214 s.

| Variante | Ici | Publié |
|---|---|---|
| sawala2025, Voie lactée + M31 | 43,3 % | ~44 % |
| sawala2025, + M33 | 62,3 % | ~2/3 |
| sawala2025, + LMC | 35,8 % | un peu plus d'1/3 |
| sawala2025, 4 galaxies | 52,6 % ; médiane 7,57 unités | « un peu plus de 50 % » ; 7,6 |
| **wu2026, 4 galaxies** | **90,1 % ; médiane 6,53 unités (6,38 Ga)** | **90 % ; 6,5 (+1,3 −1,5)** |

- Les deux publications sont reproduites. Avec les mesures les plus récentes (wu2026), en vrais Ga (l'unité de temps du carnet vaut 0,978 Ga) : la fusion a lieu dans 90 % des cas. Dates : 5 % → 4,43 ; 16 % → 4,89 ; médiane 6,38 ; 84 % → 7,63 ; 95 % → 8,52. M33 rejoint M31 dans 19 % des cas ; le Grand Nuage est absorbé par la Voie lactée dans 99,7 %.
- Notre rejeu R9 (fusion à 5,44 Ga, avec le mouvement propre central de Wu et al. 2025) tombe au 28ᵉ centile des cas qui fusionnent : c'est un scénario plausible. Réserve : R9 date la fusion à la coalescence des centres, les clones à un passage sous 20 kpc.
- La limite vient des mesures. L'erreur sur le mouvement propre de M31 (±8 µas/an) fait varier la date de fusion de ±1,4 Ga (16 à 84 %). Plus de particules n'y change rien.

### Fusion à 3 M de particules : crédibilité (12/11/2026) [mesuré, pipeline/fusion/analyse_forme.py]
- Disques de départ : aplatissement c/a = 0,18 et 0,19 (Voie lactée, M31), épaisseur médiane 0,35 et 0,40 kpc, rayon médian 4,2 et 4,8 kpc. Avant la rencontre, ils s'épaississent lentement : 0,55 kpc à 4 Ga, chauffage numérique et marées.
- Rencontre : premier passage à 4,64 Ga, à 2,4 kpc (presque de face, vitesse de côté de Wu et al. 2025 : 34 km/s). Centres confondus à 5,42 à 5,7 Ga. Littérature : van der Marel et al. 2012, premier passage 3,9 Ga et fusion 5,9 Ga ; Cox & Loeb 2008, fusion vers 5 Ga. Clones Wu 2026 : le premier passage sous 20 kpc tombe au 10ᵉ centile des cas qui fusionnent.
- Reste : elliptique triaxiale (b/a 0,8, c/a 0,6), profil de Sérsic n = 3,9 et Re = 6,1 kpc (proche de la loi de de Vaucouleurs, n = 4), comme le reste « Milkomeda » de Cox & Loeb 2008. Plus de disque ni de bras : c'est le résultat attendu, pas un défaut.
- Soleil à 10 Ga : à 67 kpc du centre du reste. Cox & Loeb 2008 le trouvent le plus souvent au-delà de 20 kpc.
- Défaut réel : seules 30 000 étoiles sur 3 M de particules (1 %) étaient gardées dans les images. Calcul relancé avec --toutes (1 M d'étoiles, ~3 Go), θ 0,7 comme le calcul du fil natif, et la composante de chaque étoile (disque ou bulbe) dans composantes.bin.
- Limites : disques de départ lisses (modèle d'équilibre AGAMA, sans bras mesurés) ; un seul scénario (mouvement propre central). La fourchette des dates vient des clones.
