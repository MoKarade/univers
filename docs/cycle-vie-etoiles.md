# Cycle de vie des étoiles (appli PC, 20 novembre 2026)

Demande de Marc : voir le cycle de vie d'une étoile (naissance dans un nuage, séquence principale, géante rouge,
nébuleuse planétaire, naine blanche, supernova, étoile à neutrons, trou noir) et le Soleil devenir une géante rouge, en
avançant le temps. Règles : au plus près du réel, masse conservée, pas de bascule brutale de forme.

Labels : [Certain] calculé ici et contrôlé ; [Probable] publié ; [Supposition] choix fait ici ; [À vérifier].

## Ce qu'on voit

- **Le Soleil et les 33 étoiles nommées** changent de rayon, de couleur et d'éclat avec la date (sphère vue de près,
  point vu de loin). Aujourd'hui, rien ne change : l'écran montre la mesure × (modèle à la date / modèle aujourd'hui).
- **La matière autour** : nuage de naissance (sombre, il cache ce qui est derrière), vents des géantes, nébuleuse
  planétaire (gaz ionisé qui brille), reste de supernova. Dessinée en couches sphériques (`cycle_nebuleuse.h`).
- **Panneau, onglet Astre, « Vie de l'étoile »** : étape, âge, masse, rayon, température, éclat, où est passée la
  matière (bilan conservé), sa fin et quand ; un bouton par étape (« Géante », « Nébuleuse », « Supernova »…) qui met
  la date au début de l'étape, une vitesse qui la fait durer une trentaine de secondes, et la caméra à bonne distance.
- **Pose « photo »** : comme pour les galaxies, la pose suit la nébuleuse la plus brillante à l'écran (brillance moyenne
  0,3 dans le rayon qui contient la moitié de sa lumière) ; les étoiles saturent, comme sur une photo. Vue de près
  (l'étoile est une sphère), le gaz suit l'échelle des surfaces (même réglage que la surface du Soleil).
- **Le Soleil reste montré à toute date** (avant : il disparaissait après le premier passage d'Andromède, +4,6 Ga).
  Au-delà, sa place dans la Galaxie n'est pas calculée : il est montré à l'origine du repère, et le panneau le dit.

## Résultats (essai_cycle, [Certain] : calculés ici avec les modèles ci-dessous)

| Soleil (MIST 1 M☉) | Valeur |
|---|---|
| Quitte la séquence principale | dans 5,35 Ga |
| Géante rouge la plus grande | 205 R☉ (0,95 UA) dans 6,89 Ga |
| Naine blanche | dans 6,90 Ga, 0,540 M☉, 0,013 R☉ ; à +9 Ga : 6 000 K |

Étoiles nommées (placées par éclat et couleur, voir plus bas) : Bételgeuse 18 M☉ (16 à 20 ; Joyce et al. 2020 :
16,5 à 19), supernova dans 0,09 à 0,55 Ma ; Antarès 20 M☉, dans 0,04 à 0,4 Ma ; Rigel et Deneb 13 M☉ ; Sirius 2,16 M☉
(mesuré : 2,06), naine blanche dans 0,7 à 1,1 Ga ; Procyon 1,44 M☉ (mesuré : 1,50).

Étoiles massives ajoutées pour voir la fin des plus grosses (`natif/etoiles_cycle.tsv`, températures publiées par
spectroscopie à la place de B-V, qui ne distingue plus les étoiles très chaudes) : **Naos** (Zêta de la Poupe, O4,
40 000 K, Howarth & van Leeuwen 2019) : 45 M☉, s'effondre en **trou noir de 26 M☉ sans explosion** dans environ 2 Ma ;
**Alnitak** (29 500 K, Bouret et al. 2008) : 22 M☉, supernova puis étoile à neutrons. Bételgeuse : 3 500 K (Joyce et al. 2020).
Naos est une étoile peut-être issue d'une fusion (Howarth & van Leeuwen 2019) : la masse placée par le modèle d'une
étoile seule est plus grande que la leur [À vérifier].

Contrôles qui passent : masse conservée à toute date (écart < 1e-6, Soleil et 20 M☉), rayon continu (aucun saut entre
deux dates proches, raccord MIST -> Montréal à 0,0000007 dex en éclat), 20 M☉ -> étoile à neutrons de 1,5 M☉, 30 M☉ ->
trou noir, 60 M☉ -> effondrement direct sans explosion, supernova au plateau M_V = -16,7.

## Modèles et sources

| Partie | Modèle | Statut |
|---|---|---|
| Vie de l'étoile | trajectoires MIST v1.2, [Fe/H] = 0, sans rotation (Choi et al. 2016 ; Dotter 2016) ; 182 masses de 0,1 à 300 M☉, interpolées point d'évolution par point d'évolution | [Probable] |
| Naine blanche | refroidissement de Montréal, hydrogène pur (Bédard et al. 2020), raccordé à l'éclat de la fin de MIST | [Probable] |
| Reste de supernova | recette « rapide » de Fryer et al. 2012 ; seuil trou noir à 3 M☉ de baryons | [Probable] ; seuil [Supposition] |
| Supernova | courbe moyenne de type II (Anderson et al. 2014) ; photosphère qui part du rayon de l'étoile à ~4 000 km/s | [Probable] |
| Naissance | cœur de 0,1 pc (Bergin & Tafalla 2007), efficacité 1/3 (Alves et al. 2007), phase enfouie 0,5 Ma (Evans et al. 2009) ; dispersion du reste à 1 km/s | [Probable] ; dispersion [Supposition] |
| Vents | vitesse : Lamers et al. 1995 (chaudes), 15 km/s (géantes, Höfner & Olofsson 2018) ; freinage chasse-neige dans 1 atome/cm³ | [Probable] ; densité [Supposition] |
| Nébuleuse planétaire | le vent rapide du cœur nu pousse le vent lent en coquille à 25 km/s (Kwok et al. 1978 ; vitesse typique mesurée) | [Probable] ; épaisseur 15 % [Supposition] |
| Lumière du gaz | photons ionisants d'un corps noir, recombinaisons cas B (Osterbrock & Ferland 2006), 30 % de l'énergie absorbée en lumière visible ; poussière : 209 cm²/g (Bohlin et al. 1978), albédo 0,6 | [Probable] ; 30 % et teintes [Supposition] |
| Mélange avec le milieu | une coquille freinée sous ~10 km/s se confond avec le milieu (Cioffi et al. 1988) ; passage de 10 à 5 km/s | [Probable] ; largeur [Supposition] |
| Placement des étoiles nommées | point le plus probable de la grille d'après M_V et B-V mesurés (σ log L = 0,1 ; σ log T = 0,03), Salpeter, âge < 13,8 Ga ; fourchettes 16-84 % à l'écran | estimation [Supposition sur les σ] |

## Vu à l'écran (captures du 20/11, fenêtre cachée 1600 × 900)

Soleil géante rouge (+6,77 Ga) et sur la branche asymptotique (+6,89 Ga) : grosse sphère orange teintée ; naine blanche
(+7,5 Ga) : petite sphère bleutée ; Bételgeuse en supernova : photosphère blanche de 50 UA ; Rigel il y a 16,8 Ma :
nuage sombre qui cache les étoiles derrière lui, puis jeune étoile bleue qui ionise son nuage (lueur bleue, anneau
sombre de poussière). Pas encore vu : la nébuleuse planétaire du Soleil avec la pose « photo » (corrigée après les
captures) ; le reste de la supernova de Bételgeuse (trop faible avant cette correction).

## Limites connues

- Nébuleuse planétaire du Soleil plus faible que les plus brillantes observées (quelques L☉ au lieu de dizaines à
  centaines) : la coquille du modèle n'est pas assez comprimée [À vérifier contre un modèle hydrodynamique publié].
- Une seule métallicité (solaire) ; ni rotation, ni étoiles doubles (Sirius B, Spica, Antarès B…).
- Planètes : au-delà des tables de positions, elles ne sont pas montrées ; Mercure et Vénus sont englouties d'après le
  rayon calculé [Probable], la Terre peut-être [À vérifier : dépend des marées, non comptées par MIST].
- Les étoiles du catalogue Gaia (sans nom) ne vieillissent pas une à une ici (travail resté sur la branche `etoiles-vie`).

## Refaire la table

```bash
curl -sSfLO https://mist.science/data/tarballs_v1.2/MIST_v1.2_feh_p0.00_afe_p0.0_vvcrit0.0_EEPS.txz
# tables : https://www.astro.umontreal.ca/~bergeron/CoolingModels/Tables/Table_Mass_0.5 ... 1.3
python pipeline/natif/vie_cycle.py <dossier EEPS> <dossier Montréal> vie_cycle.bin
essai_cycle vie_cycle.bin
```
