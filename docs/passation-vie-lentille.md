# Passation : vie des étoiles et lumière déviée (13/11/2026)

Branche `etoiles-vie` (clone `C:\dev\univers-etoiles`, base `appli-pc`). Build à part : `C:\tmp\natif\build-vie`.
Données : `C:\tmp\natif\donnees\vie\`.

## Fait et vérifié
- **Vie des étoiles** (`natif/src/vie_etoiles.h`, `shaders/vie_ecrire.comp`) : éclat et couleur mesurés + changement
  calculé (MIST v1.2) jusqu'à la date montrée ; naissance (absente avant), supernova (courbe moyenne type II puis rien),
  naine blanche (modèles de Montréal). Calcul sur le processeur en fil de fond, seuls les mots changés partent à la carte
  (0 Go de mémoire graphique en plus). Tri des feuilles Gaia et lumière sautée corrigés (`gaia.h`, `setLife`).
  Fiche : âge, fourchette, masse, étape, fin (`interface_temps.h`). Ligne « Éclat et couleur des étoiles » dans la liste
  mesuré/calculé. Vu à l'écran : Bételgeuse disparaît après sa supernova (+229 ka).
- Tables : `pipeline/natif/mist_gaia.py` -> `mist_traces.bin` (2000 masses, G, BP-RP, V, B-V) ;
  `naines_blanches.py` -> `naines_blanches.bin` ; placement `etoiles_vie.py` (Gaia FLAME, sinon diagramme lissé
  + poussière mesurée) ; contrôles `test_vie_etoiles.py` (Soleil, fenêtres calmes, Sirius, Véga, Antarès, Bételgeuse PASSE).
- `vie_principal.bin` fait (58 580 étoiles brillantes placées, poussière Edenhofer retirée).
- Numéros Gaia dans l'ordre des fichiers : `gaia_ids.py` -> `C:\tmp\natif\gaia\gaia_ids.bin`, `gaia_b_ids.bin`
  (contrôlés octet pour octet contre gaia.bin et gaia_b.bin).
- **Lumière déviée** (`lentille.h`, `deviation.h`, `trous_noirs.h`, `shaders/lentille.frag`) : passe sur l'image des
  étoiles avant planètes et Soleil ; Soleil, Jupiter, Saturne (champ faible exact) ; 6 trous noirs mesurés (Sgr A*, M87*,
  Gaia BH1-3, Cygnus X-1) avec rayon suivi pas à pas (Schwarzschild) et ombre. Trous noirs cherchables (Kind::Hole) avec
  fiche. `essai_lentille` PASSE (1,7512″ au Soleil, champ faible à 0,3 %, 3√3, Sgr A* 53,3 µas, M87* 39,7 µas).

## Tourne encore
- Téléchargement ESA des paramètres Gaia (`pipeline/natif/gaia_ap.py`, journal `C:\tmp\natif\gaia\ap.log`,
  sortie `C:\tmp\natif\gaia\ap\*.parquet`, ~3 386 fichiers, pause si cod.exe). Reprise possible en relançant la même commande.

## Reste à faire
1. Quand le téléchargement finit : `python pipeline/natif/etoiles_vie.py gaia mist_traces.bin gaia.bin gaia_ids.bin ap vie_a.bin`
   (idem jeu B -> `vie_b.bin`), dans `C:\tmp\natif\donnees\vie\`.
2. Nouvelle règle de Marc (modèles permis, signalés) : placer aussi les étoiles sans couleur (éclat seul) et les naines
   blanches (refroidissement de Montréal) au lieu de « inconnu ».
3. Supernovas historiques (1006, 1054, 1572, 1604, 1987A) ; essais Hyades et Pléiades (âges d'amas).
4. Lentilles fortes cataloguées (distances avec la cosmologie réglable, énergie noire comprise) ; noms des astres
   déviés (une étiquette peut tomber dans l'ombre d'un trou noir) ; ciel complet autour d'un trou noir (aujourd'hui :
   noir là où la source est hors de l'écran).
5. Relectures (critiques), mesure de fluidité, installation (`natif/installer.ps1`), PR vers `appli-pc`.
