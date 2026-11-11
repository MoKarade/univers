# Brouillons de configuration Firebase

Écrits sans accès à un projet Firebase : rien ici n'a été exécuté [À vérifier]. À brancher dans la tâche T2.
- `firebase.json` : hébergement de la page d'entrée et règles de stockage.
- `storage.rules.tpl` : lecture réservée au compte autorisé. `__AUTHORIZED_EMAIL__` est remplacé au déploiement par le secret du même nom.
- `cors.json` : autorise la page à lire le stockage depuis le navigateur.
- `deploiement.exemple.yml` : trame de tâche automatique.
