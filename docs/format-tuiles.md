# Format de tuiles — proposition, à valider dans la tâche T3

Principe : l'espace est découpé en cubes emboîtés (un cube se divise en huit). Chaque cube porte les objets les plus brillants de son volume qui ne sont pas déjà dans un cube parent. De loin, on ne charge que les grands cubes ; en s'approchant, on descend.

- Étoiles : cube racine centré sur le Soleil. Critère de rang : l'éclat intrinsèque, pour que les étoiles lumineuses lointaines apparaissent avant les faibles proches.
- Galaxies : même arbre, en coordonnées comobiles (distances corrigées de l'expansion).
- Une tuile vise 100 à 400 ko. Elle contient, par objet : position quantifiée dans le cube, éclat, couleur, mouvement propre pour les étoiles.
- Un index JSON liste les cubes présents, leur nombre d'objets et leur rang le plus faible.
- Côté page : on charge un cube si sa taille apparente dépasse un seuil et s'il coupe le champ ; on libère les plus anciens au-delà du budget mémoire.
- Les noms de fichiers portent une version (`v1/…`) pour pouvoir remplacer les données sans casser le cache.
