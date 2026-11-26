# Univers — règles du dépôt

Simulation 3D de l'univers dans le navigateur (three.js 0.149.0), du système solaire à l'horizon cosmique, avec des données réelles et sourcées, complétée par une application PC C++20/Vulkan (`natif/`).

## À respecter
- Français. Chaque affirmation non évidente porte [Certain] / [Probable] / [Supposition] / [À vérifier].
- Côté web : aucune commande à faire lancer sur le PC de Marc ; tout passe par le dépôt et la CI. Exception approuvée le 12 novembre 2026 pour l'appli PC et les calculs GPU (`docs/plan-natif.md`) : outils portables sans administrateur (`C:\dev\outils-natif`), calculs GPU sans fenêtre qui cèdent la carte (`Carte.attendre`), contrôles GPU jamais comptés comme CI automatique.
- Rien qui coûte sans accord. Firebase est en formule Blaze, alerte de budget à 10 $ par mois. Le site est privé : un seul compte Google, lu dans le secret `AUTHORIZED_EMAIL`.
- Pas de faux contrôle. Ce qui n'a pas été vu ou mesuré est dit tel quel.
- Toute donnée affichée garde sa source et son statut : mesuré, calculé ici, ou supposé. Ne jamais présenter une supposition comme une mesure.
- `app/gen/` est généré. On ne l'édite pas à la main : on régénère avec `pipeline/`.

## Construire et tester
- Construire la page : `python3 app/build.py` écrit `dist/index.html` (page autonome).
- Tests de calcul JS (26 tests) : `printf '%s\n' app/test/*.test.js | xargs -P 4 -n 1 node`
- Tests à l'écran : `python3 app/test/shots.py desk '<spec JSON>'` (Playwright, rendu logiciel, pas de carte graphique).
- Physique C++20 & essais portables (Linux) : `cmake -S natif -B build-linux -DCMAKE_BUILD_TYPE=Release && cmake --build build-linux -j && ctest --test-dir build-linux --output-on-failure`
- Tests autonomes du pipeline : `python3 pipeline/test_pipeline_stdlib.py && python3 pipeline/sources/test_build_gw.py`
- Crochets de test dans la page : `window.__U` (état `S`, image `F`, rendu `Rr`, `goName`, `evGo`, `parseWhen`, `eclipseScan`…).

## Pièges déjà rencontrés
- Ne jamais ajouter un commentaire `//` au milieu d'une ligne de code qui continue : il coupe tout ce qui suit (erreur déjà survenue en production sur les étoiles Gaia). Utiliser `/* */` ou une ligne dédiée.
- Les nuages de points sont en simple précision : loin du Soleil, tout objet suivi de près doit être placé en double précision côté processeur (voir `updateNear`, `probeTab`).
- La perte du contexte graphique est gérée par rechargement (`onLost`). Toute nouvelle grosse couche doit s'allumer progressivement.
- Au-delà de ce que l'écran peut suivre, les orbites utilisent des horloges d'affichage bridées (`S.solOff`, `S.moonOff`). Ne pas lire une position réelle pendant ce régime.
- three.js `0.149.0` est chargé par balise `<script>` avec intégrité SRI depuis cdnjs, version figée.

## Où lire
- `HANDOVER.md` : état, architecture, sources, vérifié ou non.
- `docs/mission-lot1.md` : la mission en cours et ses tâches.
- `docs/gestes-marc.md` : ce que seul Marc peut faire.
- `docs/audit-qualite-github.md` : audit qualité approfondi et gouvernance GitHub.


## Orchestrateur et critiques

La session principale est l'orchestrateur. Elle ne déclare jamais un lot fini seule.

Boucle pour chaque lot de `docs/plan-reel.md` :
1. Reformuler le lot : avant, après, « fini quand », fichiers touchés. Poser toutes les questions d'un coup, avec une recommandation pour chacune.
2. Construire.
3. Lancer les quatre critiques, dans cet ordre : `critique-reel`, `critique-rendu`, `critique-usage`, `critique-preuves`. Ils ne modifient rien.
4. Si un critique rend BLOQUE : corriger, puis relancer ce critique. Trois échecs de suite sur le même point : s'arrêter et demander à Marc.
5. Résumé de fin de lot.

Pendant le travail : une ligne par lot. À la fin : Fait / Pourquoi / Fichiers touchés / Vérifications / Points d'attention / Suite / TL;DR.

Règle de vérité : à l'écran, une donnée est mesurée, calculée ou inconnue. Rien d'autre. Un fondu ne remplace jamais un phénomène.
