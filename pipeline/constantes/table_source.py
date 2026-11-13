#!/usr/bin/env python3
"""Table unique des constantes de l'appli et des calculs (étape 0 du plan B+, docs/refonte-simulations-pro.md).

Ce fichier est la SEULE source écrite à la main. `construire.py` en tire :
- `pipeline/constantes/univers.json` : lu par les scripts Python (`constantes.py`) ;
- `natif/physique/constantes_univers.h` : lu par l'appli.
Les deux fichiers sont générés : ne pas les éditer à la main.

Chaque bloc porte sa source (`src`) et son statut : « mesuré » (publié, avec son erreur), « modèle » (choix d'un modèle
publié ou réglé ici), « adopté » (pas de mesure : valeur prise faute de mieux, à dire à l'écran).

Valeurs des galaxies : reprises de `pipeline/fusion/modeles_v2.py` et `docs/parametres-galaxies.md` (branche
`modeles-depart`, 13 publications relues le 13/11/2026). Observables (distances, mouvements propres, vitesses
radiales) : Sawala et al. 2025 (Extended Data Table 1) et Wu et al. 2025/2026 pour Andromède et le Triangle.

Unités : kpc, km/s, masses solaires, Ga, µas/an pour les mouvements propres, degrés pour les angles.
"""

# ---------------------------------------------------------------------------------------------------------------
# Repère et Soleil. Repère phys::galaxie (natif/physique/galaxie_orbites.h) : centre de la Voie lactée à l'origine,
# axes parallèles aux axes galactiques héliocentriques (x vers l = 0, b = 0 ; y vers l = 90° ; z vers le nord
# galactique), Soleil en −R0 · SGRA (SGRA = direction de Sagittarius A* vue du Soleil).
# ---------------------------------------------------------------------------------------------------------------
REPERE = dict(
    R0=8.20, R0_err=0.09,
    src_R0='McMillan 2017 (MNRAS 465, 76), résumé : R0 = 8,20 ± 0,09 kpc ; identique à l’appli (kR0) et au repère attendu par le fil Voie lactée',
    sgra=[0.9999992, -0.00097327, -0.00080564],
    src_sgra='direction de Sagittarius A* en coordonnées galactiques (DATA.SGRA_GAL de la page, kSgra de l’appli)',
    v0=232.8, v0_err=3.0,
    src_v0='McMillan 2017, résumé : vitesse circulaire au Soleil 232,8 ± 3,0 km/s (meilleur modèle, table 3 : 233,1). '
           'L’appli utilise 230 (kV0) : écart signalé dans le grand livre',
    soleil_particulier=[11.1, 12.24, 7.25],
    src_soleil_particulier='Schönrich, Binney et Dehnen 2010 (MNRAS 403, 1829), mouvement propre du Soleil (U, V, W)',
    statut='mesuré',
)

# ---------------------------------------------------------------------------------------------------------------
# Cosmologie (celle de l'appli : natif/src/cosmologie.h, Planck 2018) et énergie noire dans le Groupe local.
# ---------------------------------------------------------------------------------------------------------------
COSMOLOGIE = dict(
    H0=67.4, omega_m=0.315, omega_lambda=0.685, w0=-1.0, wa=0.0,
    src='Planck 2018 VI (A&A 641, A6), comme natif/src/cosmologie.h ; énergie noire dans le Groupe local : a = H0² Ω_Λ (x − x_cm) '
        '(pipeline/fusion/energie_noire.py ; Partridge, Lahav et Hoffman 2013 ; Peñarrubia et al. 2014)',
    statut='mesuré',
)

# ---------------------------------------------------------------------------------------------------------------
# Galaxies. Pour chacune :
#   modele    : la forme de masse utilisée par le calcul N-corps (même syntaxe que GALAXIES de modeles_v2.py) ;
#   loi_masse : loi de la masse totale pour l'ensemble Monte-Carlo (centre = masse du modèle ci-dessus, pour que le film
#               soit UN tirage de l'ensemble ; largeur = incertitude publiée) ;
#   observe   : ce qui place la galaxie aujourd'hui (direction, distance, mouvement propre, vitesse radiale) ;
#   disque    : orientation du disque aujourd'hui (inclinaison, angle de position de la ligne des nœuds, côté proche,
#               sens de rotation vu de la Terre).
# ---------------------------------------------------------------------------------------------------------------
GALAXIES = {
    'voie_lactee': dict(
        nom='Voie lactée',
        modele=dict(
            halo=dict(rho0=8.54e6, rs=19.6, coupure=250.0),
            bulbe=dict(rho0=9.84e10, r0=0.075, puissance=1.8, coupure=2.1, q=0.5),
            disques=[
                dict(kind=1, sigma0=8.96e8, rd=2.50, hz=0.30, sigma_soleil=35.0, r_soleil=8.20),
                dict(kind=4, sigma0=1.83e8, rd=3.02, hz=0.90, sigma_soleil=50.0, r_soleil=8.20),
                dict(kind=3, masse=1.22e10, rd=7.0, hz=0.085, q_min=1.5),
            ],
            src='McMillan 2017 (MNRAS 465, 76), table 3, meilleur modèle ; agitation au Soleil : Bland-Hawthorn et Gerhard 2016 § 5.4 ; '
                'gaz HI + H2 pris comme un disque froid (modeles_v2.py)',
            barre=dict(demi_longueur=5.0, omega=39.0, angle_aujourdhui=28.0,
                       src='Wegg, Gerhard et Portail 2015 ; Portail et al. 2017 (39,0 ± 3,5 km/s/kpc) ; angle avec la direction Soleil-centre'),
        ),
        loi_masse=dict(centre=None, sigma=0.30e12,
                       src='centre = masse totale du modèle (halo coupé à 250 kpc compris) ; largeur : McMillan 2017, résumé, masse du viriel '
                           '1,30 ± 0,30 × 10¹² M☉ (Sawala 2025 prend 1,0 ± 0,2 : variante « sawala2025 »)'),
        statut='mesuré',
    ),
    'andromede': dict(
        nom='Andromède (M31)',
        modele=dict(
            halo=dict(rho0=1.10e7, rs=16.5, coupure=207.0),
            bulbe=dict(masse=3.1e10, a=0.55),
            disques=[
                dict(kind=1, masse=5.6e10, rd=5.3, hz=0.6, q_min=1.5),
                dict(kind=3, masse=5.6e9, rd=6.0, hz=0.15, q_min=1.5),
            ],
            src='Tamm et al. 2012 (A&A 546, A4), tables 2 et 4 (halo NFW, disque 5,6 × 10¹⁰ borne basse) ; disque 5,3 kpc : Courteau et al. 2011 ; '
                'bulbe 3,1 × 10¹⁰ : Blaña Díaz et al. 2018 ; gaz : Chemin et al. 2009 × 1,33 ; hauteurs [modèle]',
            barre=dict(demi_longueur=4.0, omega=40.0, angle_aujourdhui=54.7, src='Blaña Díaz et al. 2018 (40 ± 5 km/s/kpc ; 54,7 ± 3,8°)'),
        ),
        loi_masse=dict(centre=None, sigma=0.25e12,
                       src='centre = masse du modèle (Tamm 2012 : 1,04 × 10¹² dans 207 kpc) ; largeur 0,25 × 10¹² pour couvrir 0,8 (Kafle 2018) à 1,3 '
                           '(Sawala 2025) [modèle : choix fait ici]'),
        observe=dict(ra=10.6847083, dec=41.26875, dmod=24.407, dmod_err=0.032, pmra=45.9, pmra_err=8.1, pmdec=-20.5, pmdec_err=6.6,
                     vr=-301.0, vr_err=1.0,
                     src='direction : Sesame ; module de distance 24,407 ± 0,032 (761 kpc, Li et al. 2021) via Sawala 2025 ED table 1 ; '
                         'mouvement propre : Wu et al. 2025 (A&A 701, A265, supergéantes Gaia DR3) via Wu et al. 2026 (arXiv:2603.22863) ; '
                         'vitesse radiale : Sawala 2025',
                     variante_sawala2025=dict(pmra=48.9, pmra_err=10.5, pmdec=-36.9, pmdec_err=8.1)),
        disque=dict(inclinaison=77.0, pa_noeuds=38.0, sens_vu_terre='antihoraire', bout_approche_pa=218.0,
                    src='Blaña Díaz et al. 2018 § 2.2 (77°, 38°) ; sens : van der Marel et al. 2019 (V_rot = −206 ± 86 km/s, antihoraire) ; '
                        'côté sud-ouest en approche (bien établi) ; côté proche déduit des deux (attendu : nord-ouest)'),
        statut='mesuré',
    ),
    'triangle': dict(
        nom='Triangle (M33)',
        modele=dict(
            halo=dict(rho0=5.08e6, rs=16.7, coupure=160.0),
            bulbe=None,
            disques=[
                dict(kind=1, masse=4.8e9, rd=1.8, hz=0.3, q_min=1.5),
                dict(kind=3, masse=3.0e9, rd=4.0, hz=0.15, q_min=1.5),
            ],
            src='Corbelli et al. 2014 (A&A 572, A23) : étoiles 4,8 × 10⁹, 1,8 kpc, halo NFW 4,3 × 10¹¹ (c = 9,5) ; gaz : Kam et al. 2017 et '
                'Corbelli 2014 × 1,33 ; hauteurs [modèle]',
        ),
        loi_masse=dict(centre=None, sigma=1.0e11,
                       src='centre = masse du modèle (Corbelli 2014 : 4,3 ± 1,0 × 10¹¹) ; Sawala 2025 prend 3 ± 1 × 10¹¹ (variante « sawala2025 »)'),
        observe=dict(ra=23.46206906218, dec=30.66017511198, dmod=24.67, dmod_err=0.07, pmra=30.6, pmra_err=5.7, pmdec=19.0, pmdec_err=5.7,
                     vr=-179.2, vr_err=1.8,
                     src='direction : Sesame ; module de distance 24,67 ± 0,07 (859 kpc) : Sawala 2025 ED table 1 ; mouvement propre : moyenne '
                         'pondérée Wu et al. 2025 et VLBA (Brunthaler), via Wu 2026 ; vitesse radiale : Sawala 2025',
                     variante_sawala2025=dict(pmra=31.0, pmra_err=19.0, pmdec=-29.0, pmdec_err=16.0)),
        disque=dict(inclinaison=55.0, pa_noeuds=22.0, sens_vu_terre='horaire', bout_approche_pa=22.0,
                    src='Corbelli et Schneider 1997 (22°, 55°), comme le fil Voie lactée (Kam et al. 2017 : 52 ± 3°, 22,5°) ; sens : van der '
                        'Marel et al. 2019 (80 ± 52 km/s, horaire) ; côté nord-est en approche (fil Voie lactée) ; côté proche déduit des deux'),
        statut='mesuré',
    ),
    'grand_nuage': dict(
        nom='Grand Nuage de Magellan',
        modele=dict(
            halo=dict(hernquist=2.29e11, a=25.8, coupure=100.0),
            bulbe=None,
            disques=[dict(kind=1, masse=2.7e9, rd=1.5, hz=0.3, q_min=1.5)],
            src='masse totale 1,38 × 10¹¹ M☉ (Erkal et al. 2019) APRÈS la coupure à 100 kpc, et 1,7 × 10¹⁰ M☉ dans 8,7 kpc (van der Marel et '
                'Kallivayalil 2014) : les deux fixent la normalisation (2,29 × 10¹¹ avant coupure) et l’échelle (25,8 kpc) du Hernquist [calculé ici ; '
                'modeles_v2.py avait 1,38 × 10¹¹ et 16,1 kpc AVANT coupure, soit 0,97 × 10¹¹ seulement après] ; étoiles : van der Marel 2006',
        ),
        loi_masse=dict(centre=None, sigma=0.25e11,
                       src='centre = masse du modèle, réglée sur Erkal 2019 (1,38 +0,27 −0,24 × 10¹¹) ; Sawala 2025 prend 1,5 ± 0,5 × 10¹¹'),
        observe=dict(ra=80.89417, dec=-69.75611, dmod=18.477, dmod_err=0.026, pmra=1910.0, pmra_err=20.0, pmdec=229.0, pmdec_err=47.0,
                     vr=262.2, vr_err=3.4,
                     src='Sawala 2025 ED table 1 (distance : Pietrzyński et al. 2019 ; mouvement propre : Kallivayalil et al. 2013, '
                         'van der Marel et Kallivayalil 2014)'),
        disque=dict(inclinaison=34.7, pa_noeuds=139.1, sens_vu_terre='horaire', cote_proche_pa=49.1,
                    src='van der Marel et Kallivayalil 2014 (139,1 ± 4,1° ; 34,7°, comme le fil Voie lactée) ; côté proche au nord-est [Probable] ; '
                        'sens : horaire vu de la Terre (van der Marel et Kallivayalil 2014) [À vérifier : le fil Voie lactée le donne à confirmer]'),
        statut='mesuré',
    ),
    'petit_nuage': dict(
        nom='Petit Nuage de Magellan',
        modele=dict(
            halo=dict(hernquist=3.09e9, a=1.73, coupure=10.0),
            bulbe=None,
            disques=[dict(kind=1, masse=3.1e8, rd=1.0, hz=0.8, q_min=2.5),
                     dict(kind=3, masse=5.6e8, rd=2.0, hz=0.3, q_min=1.5)],
            src='MODÈLE réglé ici, pas un modèle publié. Contraintes lues : matière noire dans 4 kpc 1 à 1,5 × 10⁹ M☉ (Di Teodoro et al. 2019, '
                'résumé : halo dominant toujours requis) → 1,5 × 10⁹ retenu ; vitesse circulaire ~55 km/s à 2,8 kpc (même source ; le modèle donne '
                '~50 km/s, calcul sphérique approché) ; masse dynamique 2,4 × 10⁹ M☉ dans ~3 kpc (Stanimirović et al. 2004, qui concluaient sans '
                'matière noire : avis contraire) ; gaz : HI 4,2 × 10⁸ M☉ (Stanimirović et al. 2004, table 1) × 1,33 pour l’hélium ; étoiles : '
                'L_V 3,1 × 10⁸ L☉ et M/L ≈ 1 (même source). Masse totale gardée à 3 × 10⁹ (valeur adoptée), d’où 2,13 × 10⁹ de halo après la '
                'coupure à 10 kpc (rayon de marée face au Grand Nuage, ordre de grandeur) [Supposition]. Longueurs, épaisseurs et agitation '
                'minimale : choisies, non relues (disque stellaire épais et chaud : le Petit Nuage est très perturbé) [Supposition]',
        ),
        loi_masse=dict(centre=None, sigma=1.0e9,
                       src='centre = masse du modèle (3,0 × 10⁹ M☉), ADOPTÉE et non mesurée : aucune masse totale publiée relue ; seules les masses '
                           'dans 3 à 4 kpc le sont (voir le modèle). Largeur adoptée [Supposition]'),
        observe=dict(ra=13.1866, dec=-72.8286, dmod=18.977, dmod_err=0.032, pmra=772.0, pmra_err=63.0, pmdec=-1117.0, pmdec_err=61.0,
                     vr=145.6, vr_err=0.6,
                     src='mouvement propre et vitesse radiale : Kallivayalil et al. 2013 (0,772 ; −1,117 mas/an ; 145,6 km/s), comme le Grand Nuage '
                         'et le fil Voie lactée (Zivick et al. 2018 : 0,82 ; −1,21, compatible) ; distance : Graczyk et al. 2020 ; direction : '
                         'centre optique (Sesame) [Probable]'),
        disque=None,
        statut='adopté (modèle réglé sur des masses internes mesurées)',
    ),
}

# Ordre des galaxies dans les calculs et les fichiers (le film et l'ensemble utilisent le même).
ORDRE = ['voie_lactee', 'andromede', 'triangle', 'grand_nuage', 'petit_nuage']

# Réglages de l'ensemble Monte-Carlo (groupe_local_reference.py) : ceux de Sawala 2025, gardés.
ENSEMBLE = dict(
    concentration=dict(centre=10.0, sigma=2.0, src='Sawala 2025 (c = 10 ± 2) pour les galaxies sans halo NFW publié'),
    adoucissement_kpc=20.0, seuil_fusion_kpc=20.0, pas_ga=0.001 * 0.97779, coupure_sigma=2.0,
    src='Sawala et al. 2025 (arXiv:2408.00064) : saute-mouton à pas de 1 Ma, forces adoucies de 20 kpc, frottement de Chandrasekhar, '
        'fusion à moins de 20 kpc, tirages normaux tronqués à ±2σ',
)
