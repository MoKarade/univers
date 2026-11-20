# Fiches des astres : format des données (appli PC)

Demande de Marc (20/11/2026) : la fiche d'un objet choisi doit montrer **toutes** les données disponibles : valeurs
mesurées avec incertitudes, catalogue source et référence, hypothèses et modèles (dits comme tels), grandeurs dérivées.

## Où

- Fichiers `fiches/*.tsv` à côté du programme (dossier d'installation, ex. `C:\dev\Univers-PC\fiches\`).
- Écrits par `pipeline/natif/fiches_*.py` (un script par famille), lus par `natif/src/fiches.h`.
- Les grandeurs que l'appli peut déduire elle-même (distance du moment, vitesse, coordonnées galactiques…) sont
  calculées dans l'appli (`interface_fiche.h`) et marquées « calculé ».

## Format

UTF-8, séparateur tabulation, une ligne par champ, les lignes d'un même astre **consécutives**. Lignes commençant par
`#` : commentaires (en-tête du fichier : script, date, sources).

| colonne | contenu |
|---|---|
| `cle` | nom exact de l'astre dans l'appli (voir « Clés ») |
| `groupe` | titre du groupe repliable (ordre d'apparition = ordre d'affichage) |
| `libelle` | nom de la grandeur, en français simple |
| `valeur` | nombre (point décimal, ex. `5778` ou `1.989e30`) ou texte. Limite : préfixe `<` ou `>` |
| `incertitude` | vide ; `0.05` (symétrique, ±) ; `+0.1/-0.2` (dissymétrique) ; même unité que la valeur |
| `unite` | texte français (`km`, `K`, `UA`, `km/s`, `mas`, `masses solaires`, `mag`…) ; vide si sans unité |
| `statut` | `mesuré` (observation, ou valeur ajustée sur des observations et publiée) ; `calculé` (déduit par le script de valeurs mesurées : la formule va dans `source`) ; `modèle` (sortie d'un modèle ou d'une hypothèse : isochrones, relation masse-rayon, distance d'après le décalage vers le rouge…) ; `publié` (valeur de catalogue compilée dont la méthode n'est pas une mesure directe, ex. nom, type morphologique) |
| `source` | référence courte : catalogue + article (`Gaia DR3 (Gaia Collaboration 2023)`, `JPL SSD, Park et al. 2021`) |

Aucune valeur inventée : une case vide de la source n'est pas écrite. Pas de valeur par défaut.

## Variante compacte « tableau » (grandes familles : astéroïdes, galaxies Cosmicflows-4…)

Même dossier, même extension `.tsv`. Un fichier est en tableau si sa première ligne non commentaire commence par `@`.
- Lignes d'en-tête, une par colonne, dans l'ordre : `@` TAB groupe TAB libellé TAB unité TAB statut TAB source.
- Puis une ligne par astre : `cle` TAB valeur1 TAB incertitude1 TAB valeur2 TAB incertitude2 … (deux cases par
  colonne d'en-tête, même syntaxe que ci-dessus ; case vide = grandeur absente pour cet astre, rien n'est affiché).
L'appli rend exactement les mêmes lignes qu'au format long.

## Clés (nom de l'astre dans l'appli)

- Soleil : `Soleil`. Planètes : `Mercure` … `Pluton`, `Lune` (natif/src/simulation.h, kPlanets).
- Lunes : 2e colonne de `lunes.tsv`.
- Étoiles : 2e colonne de `etoiles_noms.tsv` et de `etoiles_planetes_noms.tsv`.
- Galaxies, amas, structures : 1re colonne de `galaxies_noms.tsv`, `galaxies_cf4.tsv`, `galaxies_formes_noms.tsv`,
  `structures_noms.tsv`, `superstructures_noms.tsv`. Le centre galactique : `Centre de la Voie lactée`.
- Astéroïdes et comètes : le libellé de `asteroides::Catalogue::label` (natif/src/asteroides_catalogue.h) :
  `Ceres (1)`, `Astéroïde 2001 AB`, `1P/Halley`, `Comète C/2020 F3`.
- Sondes : nom de la sonde dans `sondes.bin`.

## Groupes conseillés (dans cet ordre)

Identité · Position · Mouvement · Physique · Orbite · Rotation · Atmosphère et surface · Lumière et couleur ·
Âge et évolution · Planètes · Découverte · Autres noms · Modèles et hypothèses.
