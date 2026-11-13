# Vieillissement de la lumière des étoiles visibles (13 novembre 2026)

Demande de Marc (« faire vieillir les étoiles ») appliquée aux **traceurs** de `etoiles_visibles_<galaxie>.npz`
(docs/contrat-etoiles-visibles.md) : chacun porte la lumière **mesurée** d’une population d’étoiles. Les étoiles une à une
(Gaia) ont leur propre vieillissement (fil « vie des étoiles », `pipeline/natif/etoiles_vie.py`, branche `etoiles-vie`) ;
ce fichier ne les touche pas.

Labels : [Certain] calculé ici ; [Probable] publié, non relu en entier ; [Supposition] choix fait ici ; [À vérifier].

## 1. Ce que l’appli applique

```
lum_affichée(t)  = lum_mesurée  × facteur_lum(comp, t)
teff_affichée(t) = teff_mesurée × facteur_teff(comp, t)
```

`t` : date du film en Ga (0 = aujourd’hui ; −3 à +10, pas de 50 Ma ; interpolation linéaire entre deux dates). À t = 0, les
deux facteurs valent exactement 1 : rien ne change aujourd’hui. Table : `pipeline/etoiles/vieillissement_populations.json`,
champ `composantes[comp][régime].lum` et `.teff`, aux dates `t_ga`. `teff` = 0 veut dire « plus aucune étoile » (régime
sans naissance, dans le passé, pour les étoiles jeunes).

## 2. Deux régimes

| Régime | Quoi | Quand l’utiliser |
|---|---|---|
| `naissance_continue` | les composantes qui forment des étoiles aujourd’hui (disque mince, bras) continuent au même rythme, dans le passé comme dans le futur | **recommandé** tant que le film n’a pas de gaz : la Voie lactée forme aujourd’hui ~1 à 2 M☉ par an [Probable] et ses bras restent bleus [Supposition : rythme constant] |
| `sans_naissance` | rien ne naît (ce que fait le film N-corps) : les bras s’éteignent en ~100 Ma, et dans le passé les étoiles pas encore nées disparaissent | pour montrer ce que serait la galaxie sans formation d’étoiles ; **fait apparaître et disparaître** des étoiles jeunes, à éviter par défaut |

## 3. Résultats [Certain : calculé par la tâche GitHub `populations-mist` avec les isochrones MIST v1.2]

| Composante (`comp`) | Histoire supposée | lum à +10 Ga | teff à +10 Ga | lum à −3 Ga |
|---|---|---|---|---|
| 1 disque mince, naissance continue | 0–10 Ga, solaire | ×1,05 | ×0,94 | ×1,02 |
| 1 disque mince, sans naissance | idem | ×0,18 | ×0,72 | ×0,92 |
| 2 bulbe et barre | sursaut à 10 Ga, solaire | ×0,64 | ×0,95 | ×1,32 |
| 4 disque épais | 9–12 Ga, [Fe/H] −0,5 | ×0,68 | ×0,98 | ×1,27 |
| 5 bras et régions HII, naissance continue | 0–100 Ma | ×1,00 | ×1,00 | ×1,00 |
| 5 bras, sans naissance | idem | ×0,002 | ×0,46 | 0 (pas nées) |
| 6 halo d’étoiles | sursaut à 12 Ga, [Fe/H] −1,5 | ×0,71 | ×1,00 | ×1,25 |

Contrôles d’ordre de grandeur (population simple solaire) : la lumière baisse comme t^−0,71 entre 1 et 10 Ga (valeur
classique d’environ −0,8, de mémoire [À vérifier]) ; 3,5 M☉ formées par L☉ à 10 Ga (quelques unités attendues [À vérifier]).
Variation au plus 0,6 % tous les 50 Ma (régime recommandé) : aucun saut.

## 4. Modèle et limites

- Isochrones MIST v1.2, v/vcrit 0,4, 15 métallicités de −4 à +0,5 (Choi et al. 2016 ; Dotter 2016) [Probable] ; fonction
  de masse de Kroupa 2001 de 0,1 à 100 M☉ ; population simple = somme sur l’isochrone.
- **Naines blanches non comptées** : quelques % de la lumière d’une population vieille [Probable] ; la baisse est donc un
  peu exagérée pour le bulbe, le disque épais et le halo.
- Couleur : somme de corps noirs, rapport des flux à 440 et 550 nm [Supposition, approximation pour une teinte].
- Histoires de formation par composante : **supposées** (ordres de grandeur de la littérature, voir `COMPOSANTES` dans le
  script) ; métallicité unique par composante.
- Les isochrones ne sont pas dans le dépôt : la tâche `.github/workflows/populations-mist.yml` les télécharge
  (mist.science), calcule la table et la remet sur la branche.
