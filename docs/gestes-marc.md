# Gestes de Marc

Uniquement des clics dans un navigateur. Les libellés peuvent avoir changé [À vérifier].

1. Créer le projet. Sur console.firebase.google.com : « Créer un projet », nom `univers`, sans Google Analytics.
2. Passer en formule Blaze. Roue dentée, « Utilisation et facturation », « Détails et paramètres », « Modifier la formule », Blaze, puis associer une carte.
3. Poser l'alerte de budget. Sur console.cloud.google.com : « Facturation », « Budgets et alertes », « Créer un budget », projet `univers`, 10 $, alertes à 50, 90 et 100 %. C'est une alerte, pas un plafond.
4. Activer la connexion Google. « Authentication », « Commencer », « Mode de connexion », Google, « Activer », choisir l'adresse d'assistance, « Enregistrer ».
5. Créer le stockage. « Storage », « Commencer », emplacement `us-central1` (zone à quota gratuit), mode production.
6. Activer l'hébergement. « Hosting », « Commencer », passer les étapes en ligne de commande : elles sont inutiles ici.
7. Donner la clé au dépôt. Roue dentée, « Paramètres du projet », « Comptes de service », « Générer une nouvelle clé privée » : un fichier JSON se télécharge. Dans le dépôt GitHub : « Settings », « Secrets and variables », « Actions », puis créer
   - le secret `FIREBASE_SERVICE_ACCOUNT` : tout le contenu du fichier JSON ;
   - le secret `AUTHORIZED_EMAIL` : l'adresse Google autorisée ;
   - la variable `FIREBASE_PROJECT_ID` : l'identifiant du projet.
   Cette clé donne la main sur le projet : jamais dans le dépôt, et à supprimer de l'ordinateur une fois collée.
8. Déposer le contenu de `univers-depot.zip` dans un dépôt privé `univers` : « uploading an existing file », glisser les dossiers (86 fichiers, 27 Mo).
9. Données de départ. Dans « Storage », créer le dossier `seed` et y glisser les 17 fichiers de `univers-donnees.zip`. Pas nécessaire avant la tâche T6.

Si un déploiement répond « permission denied » : sur console.cloud.google.com, « IAM », compte `firebase-adminsdk-…`, ajouter les rôles « Administrateur Firebase Hosting », « Administrateur de règles Firebase » et « Administrateur Storage » [À vérifier : les droits par défaut suffisent peut-être].


## Pour démarrer la mission 2 (le réel seulement)

Seul le geste 8 est nécessaire : déposer le contenu de `univers-depot.zip` dans le dépôt privé `univers`. Les lots C et A ne touchent pas à Firebase. Les gestes 1 à 7 ne deviennent nécessaires qu'avant les lots B et D.

Phrase à donner à Claude Code : « Lis CLAUDE.md, HANDOVER.md, docs/plan-reel.md et docs/mission-reel.md. Fais T1 de la mission 1, puis commence la mission 2 par R1. »
