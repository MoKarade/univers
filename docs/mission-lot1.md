# Mission 1 — La page sur Firebase, chargée par zone

But : la même simulation qu'aujourd'hui, servie depuis Firebase en accès privé, qui ne télécharge que ce que l'on regarde. Pas de nouvelles données dans cette mission.

Mission finie quand : six vues de référence sont identiques entre la version du chat et la version Firebase, et la page télécharge moins de 30 Mo à l'ouverture au lieu de 135.

Chaque tâche vise 400 lignes modifiées au plus. Une tâche qui dépasse se découpe.

## T1 — Le dépôt se construit et se teste tout seul
- Avant : le code vient d'une conversation, aucun contrôle automatique.
- Après : chaque proposition de changement construit la page et lance les tests de calcul.
- Fini quand : le contrôle est vert sur la branche principale et exécute `python3 app/build.py && for f in app/test/*.test.js; do node "$f" || exit 1; done` avec un code de sortie 0.
- Fichiers touchés : configuration des contrôles du dépôt, `app/test/`.

## T2 — Page d'entrée privée sur Firebase
- Avant : la page n'existe que dans le chat.
- Après : l'adresse du projet montre une page d'entrée légère avec un bouton de connexion Google. Seul le compte autorisé voit la suite. L'application et ses données sont dans Storage, illisibles sans connexion.
- Fini quand :
  1. `curl -s -o /dev/null -w "%{http_code} %{size_download}" https://<projet>.web.app/` rend `200` et moins de 300 000 octets ;
  2. `curl -s -o /dev/null -w "%{http_code}" "https://firebasestorage.googleapis.com/v0/b/<bucket>/o/app%2Findex.html?alt=media"` rend `403` ;
  3. le test à l'écran `entree-privee` constate qu'aucune image 3D n'apparaît sans connexion ;
  4. Marc, connecté, voit la simulation (geste : une capture).
- Fichiers touchés : `web/` (page d'entrée), `infra/firebase.json`, `infra/storage.rules.tpl`, tâche de déploiement.
- Attend : gestes 1 à 7 de `docs/gestes-marc.md`.
- Conception : Hosting ne sait pas restreindre l'accès. La page d'entrée publique reste donc minuscule ; l'application est rangée dans Storage et chargée après connexion. Les règles exigent une adresse vérifiée et égale à `AUTHORIZED_EMAIL`.

## T3 — Format des tuiles et découpe des étoiles
- Avant : six fichiers d'étoiles, chargés en entier.
- Après : un outil découpe les 6,15 millions d'étoiles en zones avec niveaux de détail, et écrit un index.
- Fini quand : `python3 pipeline/tuiles_etoiles.py --verifier seed/ sortie/` affiche autant d'étoiles écrites que lues, zéro doublon, et aucune tuile de plus de 400 ko ; un test d'aller-retour sur un échantillon de 50 000 étoiles est vert dans les contrôles.
- Fichiers touchés : `pipeline/tuiles_etoiles.py`, `pipeline/test_tuiles.py`, `docs/format-tuiles.md`.

## T4 — Chargeur d'étoiles par zone
- Avant : `loadTile` charge des fichiers entiers ; `tilesTick` règle seulement la part dessinée.
- Après : la page lit l'index, ne télécharge que les zones utiles à la vue, respecte un budget mémoire et garde les tuiles en cache.
- Fini quand, test à l'écran `zones-etoiles` : moins de 30 Mo téléchargés à l'ouverture ; après « Aller à Sirius » puis recul à 500 années-lumière, plus de 300 000 étoiles affichées ; retour au système solaire sans nouveau téléchargement.
- Fichiers touchés : `app/src/60_app.js`, `app/src/40_render.js`.
- Attend : T3.

## T5 — Galaxies : découpe et chargeur par zone
- Même principe que T3 et T4 pour les 5,1 millions de galaxies en flux.
- Fini quand, test à l'écran `zones-galaxies` : en vue « Toile cosmique », plus de 500 000 galaxies affichées ; en vue « Système solaire », aucune tuile de galaxies téléchargée.
- Fichiers touchés : `pipeline/tuiles_galaxies.py`, `app/src/60_app.js`, `app/src/40_render.js`.
- Attend : T4.

## T6 — Envoi automatique des tuiles vers Storage
- Après : une tâche automatique découpe et envoie les tuiles, avec une durée de cache longue.
- Fini quand : la tâche `publier-tuiles` réussit et affiche le nombre d'objets envoyés, égal à celui de l'index ; en production, le test `tuiles-en-ligne` constate que la page charge ses tuiles depuis Storage.
- Attend : T2, T3, et le geste 9 (données de départ dans Storage).

## T7 — Astéroïdes et photos de galaxies depuis Storage
- Fini quand : « Aller à Cérès » et « Aller à M101 » donnent en production le même écran que la version du chat.
- Attend : T6.

## T8 — Mesure sur un vrai écran
- Après : un compteur optionnel affiche images par seconde, mémoire et Mo téléchargés.
- Fini quand : la tâche porte trois relevés lus par Marc sur son téléphone (geste). En dessous de 30 images par seconde en vue « Voie lactée », une tâche d'optimisation est ouverte ; elle ne fait pas partie de cette mission.
- Attend : T6.

## T9 — Parité avec la version du chat
- Fini quand : les six vues de référence (système solaire, Mars, étoiles proches, Voie lactée, M101, toile cosmique) donnent des captures équivalentes entre `dist/index.html` chargé seul et la version Firebase.
