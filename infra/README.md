# Brouillons de configuration Firebase

Écrits sans accès à un projet Firebase : rien ici n'a été exécuté [À vérifier]. À brancher dans la tâche T2.
- `firebase.json` : hébergement de la page d'entrée et règles de stockage.
- `storage.rules.tpl` : lecture réservée au compte autorisé. `__AUTHORIZED_EMAIL__` est remplacé au déploiement par le secret du même nom (le fichier généré `infra/storage.rules` est ignoré par Git).
- `cors.json.tpl` : modèle CORS à instancier avec `FIREBASE_PROJECT_ID` (`cors.json` est conservé comme référence).
- `deploiement.exemple.yml` : trame de tâche automatique durcie (vérification des secrets, substitution Python sans `sed`, `firebase-tools` épinglé, contrôle HTTP 403 sans connexion). Formule Blaze sans plafond strict : garder privé jusqu'à mesure sous tuilage spatial (< 30 Mo à l'ouverture).
