# Forme des Nuages de Magellan : état, mesures, ce que donne le grand calcul (24 novembre 2026)

Outil : `pipeline/fusion/forme_nuages.py` (essais : `pipeline/fusion/test_forme_nuages.py`, 21 vérifications, toutes
vertes). Mesures publiées : `pipeline/constantes/nuages_magellan.json` (source et statut pour chaque valeur).
Tout est calculé sur le processeur, sans la carte graphique, et sans rien écrire dans les films.

```
python pipeline/fusion/forme_nuages.py film  <dossier du film> --etoiles <étoiles visibles du film> --dates 0,0.1 --carte <préfixe>
python pipeline/fusion/forme_nuages.py etoiles <dossier des etoiles_visibles_*.npz>
```

## 1. Ce que l'appli montre aujourd'hui

Deux états à distinguer [Certain, lu dans les fichiers] :

| | Appli installée (étoiles du 13/11) | Film 3 à t = 0 (PC, en cours) et film 20 M de Colab |
|---|---|---|
| Source des étoiles | photo Mellinger 2009 remise à plat sur un disque (`etoiles_visibles_photos.py`) | vieilles étoiles posées sur la masse du calcul, jeunes sur les cartes WISE 12 µm (`groupe-local-3/etoiles`) |
| Grand Nuage | disque mince à l'inclinaison et à la ligne des nœuds publiées ; barre de la photo | même plan ; point le plus dense à 1,5 kpc du centre de masse |
| Petit Nuage | disque mince vu de face, 4,4 kpc d'épaisseur (5e-95e centile) | nuage épais : 15 kpc le long de la visée, 2,1 kpc d'écart type |
| Pont, Courant | rien | gaz et étoiles arrachés pendant la remontée du calcul (depuis −1,25 Ga) |

Cartes du ciel (coordonnées du Courant, Nidever et al. 2008 ; bleu : gaz du calcul ; jaune : étoiles ; croix : places
mesurées) : `docs/captures-nuages/appli_aujourdhui.png`, `film3_0.00Ga.png`, `film3_0.20Ga.png`.

## 2. Comparaison aux mesures, à t = 0

Mesuré par l'outil sur le film 3 du PC (le film 20 M de Colab donne les mêmes verdicts, à quelques % près).

| Quoi | Calcul | Mesure publiée | Verdict |
|---|---|---|---|
| Grand Nuage : inclinaison du disque | 31,8° | 24° à 36° selon le rayon (van der Marel & Kallivayalil 2014 ; Gaia) | conforme, **mais pas un contrôle indépendant** : les étoiles ont été posées sur ce plan |
| Grand Nuage : ligne des nœuds | 137° | 139 ± 4° | idem |
| Grand Nuage : côté proche | nord-est (47°) | nord-est | idem |
| Grand Nuage : point le plus dense / centre de masse | 1,5 kpc | 0,4 kpc du centre du disque, plus de 1 kpc du centre du gaz (van der Marel 2001) [Probable] | conforme ; il s'efface en 200 Ma (`ecarts.txt`) |
| Petit Nuage : profondeur des vieilles étoiles | 2,1 kpc (écart type) | 2,0 ± 0,4 kpc (RR Lyrae, Haschke et al. 2012) | conforme |
| Petit Nuage : côté le plus proche de nous | **nord** (353°) ; la queue part **derrière** (+10,5 kpc) | **est** (Nidever 2013, cité par Ripepi 2017) [Probable] | **ÉCART** |
| Petit Nuage : rotation des vieilles étoiles | 20 km/s | pas de rotation nette des vieilles étoiles (Murray et al. 2024) [Probable] | écart probable |
| Distance entre les deux Nuages | 25,8 kpc | 23,8 kpc | conforme (le Petit Nuage du film est à 2,6 kpc de sa place) |
| Gaz du pont | 1,5 × 10⁸ M☉ | 4,3 × 10⁸ M☉ (HI × 1,33, Brüns et al. 2005, à 55 kpc) | 3 fois trop peu |
| Gaz du Courant (au-delà de L_MS = −25°) | 2,8 × 10⁷ M☉ | 1,6 × 10⁸ M☉ neutre ; ~2 × 10⁹ avec l'ionisé (Fox et al. 2014) | **6 fois trop peu** (70 fois avec l'ionisé) |
| Gaz du bras avant | 6,5 × 10⁶ M☉ | 3,9 × 10⁷ M☉ | **6 fois trop peu** |

Les masses de gaz mesurées supposent tout le gaz à 55 kpc ; elles varient comme le carré de la distance, mal connue
(55 à 200 kpc) [Certain sur la dépendance]. Les seuils qui rangent la matière en pont, Courant et bras avant sont choisis
ici (`HORS_GN_KPC`, `HORS_PN_KPC`, `PONT_LARGEUR_KPC`, `COURANT_L_DEG`) [Supposition].

## 3. Ce que le grand calcul fournit, et ce qu'il ne peut pas fournir

- **t = 0 n'est pas calculé par le film** : c'est le contrat des étoiles visibles. Le film fait évoluer cette image ;
  il ne la corrige pas. Toute amélioration de la forme d'aujourd'hui passe par les étoiles de départ du prochain film
  [Certain].
- Le pont et le Courant visibles à t = 0 viennent de la remontée de 1,25 Ga (Petit Nuage remis à sa place mesurée il y
  a 300 Ma). Le Courant mesuré demande, d'après les modèles publiés, plusieurs milliards d'années d'interaction entre
  les deux Nuages avant leur chute vers la Voie lactée (Besla et al. 2012) [Probable] : 1,25 Ga ne peut pas le faire.
- Dans l'avenir (mesuré jusqu'à 4 Ga dans le film 3) : le Petit Nuage s'étire (35 kpc le long de la visée à +0,2 Ga,
  écart type 10 kpc à +2 Ga, 63 kpc à +4 Ga) et les deux Nuages s'éloignent (46 kpc à +2 Ga). C'est le calcul, sans
  mesure possible [Certain sur les valeurs, calculées].

## 4. Ce qui manque, par ordre d'effet

1. **Gaz du Courant et du bras avant, 6 fois trop faible.** Causes connues : Petit Nuage trop léger (3 × 10⁹ M☉ contre
   1 à 2 × 10¹⁰ il y a 3 Ga, `docs/lois-physiques/README.md`), histoire trop courte, pas de couronne chaude de la Voie
   lactée. Relève du fil du gaz et du prochain film, pas de l'affichage.
2. **Petit Nuage tourné du mauvais côté** : sa queue part derrière et vers le nord, la mesure met l'est devant. Piste :
   régler la rencontre des deux Nuages dans la remontée sur la mesure de Zivick et al. 2018 (il y a 147 ± 33 Ma, à
   7,5 ± 2,5 kpc) [Probable], puis remesurer avec l'outil.
3. **Étoiles du Petit Nuage d'aujourd'hui** : la profondeur peut venir des céphéides et RR Lyrae d'OGLE (distance de
   chaque étoile mesurée), au lieu de la masse du calcul. À faire pour les étoiles de départ du prochain film ; changer
   celles du film en cours casserait le contrat (ligne k du fichier = ligne k du film).
4. **Vieilles étoiles du Petit Nuage qui tournent** (20 km/s) alors que la mesure n'en voit pas nettement.

## 5. Vérifié, pas vérifié

- Vérifié : repère du Courant contre les places publiées des deux Nuages (0,01° près) ; passage ICRS-galactique (centre
  galactique à 0,001°) ; plan, côté proche, barre, rotation, rangement et lecture du film sur des géométries construites
  dont la réponse est connue.
- Pas vérifié : la comparaison à une carte HI réelle du Courant (non téléchargée : la carte montre seulement les places
  mesurées des deux Nuages) ; les valeurs « résumé » de `nuages_magellan.json` n'ont pas été relues dans l'article
  lui-même.
