# Champ de gravité des galaxies en coefficients (étape 8 du plan B+, préparation ; 13 novembre 2026)

Plan : `docs/refonte-simulations-pro.md` § 4.2 et § 6.2 (étapes 7 et 8). But : que les étoiles mesurées (Gaia) sentent la
gravité **du calcul N-corps** à chaque date, sans rejouer ses millions de particules.

Labels : [Certain] mesuré ici ; [Probable] publié, non relu en entier ; [Supposition] choix fait ici.

## 1. Pièces

| Fichier | Rôle |
|---|---|
| `pipeline/champ/champ_bfe.py` | `coefficients(pos, m, kind, axe=None, rayon_max=None)` : le champ d’une galaxie à une image ; `evaluer(C, x)` : potentiel et force ; `sauver` / `charger` (.npz) ; `sauver_bin` (format du C++) ; `rayon_jacobi(d, m, M)` |
| `pipeline/champ/test_champ.py` | précision contre des potentiels exacts ; `--reference dossier` écrit les fichiers de l’essai C++ |
| `natif/physique/champ_bfe.h` | lecteur et évaluateur C++ autonome (en-tête seul), branché nulle part |
| `natif/physique/essais/essai_champ_bfe.cpp` | le C++ doit redonner les valeurs de Python |

## 2. Méthode

Celle d’AGAMA (Vasiliev 2019, MNRAS 482, 1525) [Probable], réécrite ici pour tourner sans AGAMA et pour que le C++ fasse
exactement le même calcul :
- **halo, bulbe**, et particules de disque hors de la boîte du disque : développement multipolaire jusqu’à l = 8 sur
  72 nœuds en ln r ; Φ_lm et dΦ_lm/dr **exacts aux nœuds** (sommes intérieures et extérieures sur les particules),
  Hermite cubique entre eux ; au-delà de la dernière particule, Φ_lm ∝ r^−(l+1) (exact) ;
- **disque** (kind 1, 3, 4) dans une boîte de 12 λ × 6 λ (λ : rayon qui contient la moitié de la masse du disque) :
  harmoniques azimutales m = 0 à 6 sur une grille (R, z) de 41 × 41 nœuds resserrée près du centre et du plan ; masses
  déposées sur 96 × 96 cellules, noyau exact de 1/|x − x′| (fonctions Q_{m−1/2}, contrôlées à 10⁻¹² près),
  adoucissement de Plummer 0,005 λ (0,02 lissait trop un disque mince : 4 % d’erreur au centre) ; Hermite bicubique ;
- hors de la boîte : le disque par son propre développement multipolaire.

Le repère du disque est donné par `axe` (moment cinétique des étoiles, passé par le film) ; sans `axe`, petit axe
d’inertie des particules de disque. `rayon_max` (rayon de marée) écarte les particules arrachées ; leur masse est rendue
dans `masse_hors`. Les traceurs sans masse (kind 9) sont ignorés.

## 3. Précision [Certain : `python pipeline/champ/test_champ.py`]

Galaxie d’essai : halo de Hernquist 10¹² M☉, bulbe 10¹⁰, disque de Miyamoto–Nagai 6 × 10¹⁰ (a 3, b 0,3 kpc), le tout
tourné ; puis la même avec un second disque incliné de 20° et décalé de 2 kpc (toutes les harmoniques excitées).
Écart de la force aux potentiels exacts, 500 000 particules par composante :

| | médiane | 95 % des points sous | pire |
|---|---|---|---|
| dans le disque (R 0,5–30 kpc, \|z\| < 1) | 0,65 % | 2,0 % | 6,2 % |
| dans le halo (r 1–300 kpc) | 0,55 % | 2,5 % | 6,8 % |
| galaxie décentrée, disque | 0,62 % | 2,1 % | 6,6 % |
| galaxie décentrée, halo | 0,53 % | 2,4 % | 5,5 % |

Cet écart est surtout **le bruit du tirage** : un nombre fini de particules n’a pas le champ du modèle lisse. Il baisse
comme 1/√N (halo seul, de 1 à 5 kpc : 6,9 % à 200 000 particules, 3,6 % à 800 000, 2,0 % à 3,2 M). Le N-corps sent le même
bruit : c’est le champ de ses particules que l’on veut, pas celui du modèle lisse.

Autres mesures : passage en nombres à 32 bits : au plus 0,0007 % ; C++ contre Python sur le même fichier : 2 × 10⁻¹⁴.

## 4. Coût [Certain sur ce conteneur, 4 cœurs ; le PC de Marc sera plus rapide]

| Particules de la galaxie | Temps par image |
|---|---|
| 1,6 M (500 000 par composante, cas d’essai) | 3 s |
| 4 M | 5 s (multipôles sur 1 M particules tirées au sort, masses remises à l’échelle ; 9 s sans tirage) |

Pour ~1 000 images × 5 galaxies : de l’ordre de 5 h de processeur [estimation]. La matrice du noyau (434 Mo, calculée en
6 s) est gardée dans `~/.cache/univers_champ` (ou `$CHAMP_CACHE`). Fichier : ~0,45 Mo par galaxie et par image, soit
~2 Go pour 1 000 images × 5 galaxies [estimation].

## 5. Pour le film (fil des galaxies de départ)

```python
import sys; sys.path.insert(0, 'pipeline/champ'); import champ_bfe as CB
C = CB.coefficients(pos_relatives_au_centre, m, kind, axe=L_etoiles, rayon_max=CB.rayon_jacobi(d, m_gal, m_hote))
CB.sauver(C, f'champ/{galaxie}_{i:05d}.npz')          # ou CB.sauver_bin(C, ...) pour l’appli
```

## 6. Ce qui manque

- **Pas encore essayé sur une vraie image du film** ni sur un modèle de `modeles_v2.py` (AGAMA ne s’installe pas dans ce
  conteneur) : à faire dès la première image du film.
- Le **branchement dans l’appli** (`orbites_pas.comp`) revient au fil qui possède ce shader. Sur la carte graphique, la
  forme la plus simple : les tableaux du fichier en tampons, et la même fonction que `champ_bfe.h`.
- **Interpolation dans le temps** entre deux images de champ : pas faite ici (linéaire sur les coefficients, dans le
  repère de chaque galaxie, suffit si les images sont à ≤ 10 Ma [Supposition]).
- `essai_champ_bfe` n’est pas ajouté à `natif/controle.sh` : il demande les fichiers de référence de `test_champ.py`.
