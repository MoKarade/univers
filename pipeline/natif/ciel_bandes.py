#!/usr/bin/env python3
"""Cartes du ciel dans toutes les longueurs d'onde : télécharge un relevé publié (tuiles HiPS en FITS, valeurs mesurées)
et l'écrit en une carte HEALPix emboîtée pour l'appli PC (fichier ciel_<nom>.bin, lu par natif/src/ciel_bandes.h).

Pourquoi HiPS : c'est le format commun des relevés du ciel entier (norme IVOA HiPS 1.0, Fernique et al. 2017). Les
tuiles FITS gardent la valeur mesurée (kelvins, MJy/sr, coups par seconde...), pas une image retouchée. Chaque niveau
de tuiles est la moyenne des quatre pixels du niveau en dessous : la vue lointaine est déjà la somme du mesuré.

Aucune valeur n'est modifiée : seuls BSCALE et BZERO du fichier sont appliqués. Un pixel vide (NaN ou BLANK) reste vide :
c'est un trou de couverture du relevé, montré comme tel à l'écran. Les tuiles absentes du serveur (relevé partiel, par
exemple eROSITA DR1 qui ne couvre que la moitié ouest de la Galaxie) sont des trous aussi.

Usage : python ciel_bandes.py <dossier_sortie> <nom> [--ordre N | --nside-max 2048] [--simultanes 8] [--cache <dossier>]
        python ciel_bandes.py <dossier_sortie> --liste
Le <nom> est une clé de RELEVES ci-dessous. Par défaut, l'ordre HiPS le plus fin sans dépasser Nside 2048 (1,7 minute d'arc).
"""
import sys as _sys
_sys.stdout.reconfigure(encoding='utf-8')
import argparse, concurrent.futures as cf, json, math, os, struct, sys, time, urllib.error, urllib.parse, urllib.request
import numpy as np

MOC = 'https://alasky.cds.unistra.fr/MocServer/query'

# Chaque relevé : identifiant HiPS (liste du CDS, https://aladin.cds.unistra.fr/hips/list, lue le 12 novembre 2026),
# bande, ce qu'il mesure, unité, résolution native, couverture, référence. La résolution et la couverture sont celles
# publiées par l'équipe du relevé ; la couverture réelle est recomptée sur les pixels téléchargés.
RELEVES = {
    'haslam408': dict(
        hips='ESAVO/P/Haslam408', bande='radio', libelle='Radio 408 MHz',
        mesure='Température de brillance à 408 MHz (rayonnement synchrotron des électrons de la Galaxie)',
        unite='K', resolution_arcmin=56.0, longueur_onde='73 cm',
        reference='Haslam et al. 1982, A&AS 47, 1 ; carte retraitée de Remazeilles et al. 2015, MNRAS 451, 4311',
        couverture_publiee='tout le ciel', echelle='log'),
    'hi4pi': dict(
        hips='CDS/P/HI4PI/NHI', bande='radio', libelle='Radio 21 cm (hydrogène)',
        mesure="Colonne d'hydrogène neutre intégrée sur la ligne de visée (raie à 21 cm, de -600 à +600 km/s)",
        unite='atomes/cm²', resolution_arcmin=16.2, longueur_onde='21 cm',
        reference='HI4PI Collaboration, Ben Bekhti et al. 2016, A&A 594, A116 (relevés EBHIS et GASS)',
        couverture_publiee='tout le ciel', echelle='log'),
    # --- Micro-ondes : Planck, 3e publication (PR3, 2018), cartes de la mission complète. Unités de l'archive de l'ESA
    # (Planck Legacy Archive) : K_CMB de 30 à 353 GHz, MJy/sr à 545 et 857 GHz. Sous 217 GHz, c'est surtout le fond
    # diffus cosmologique (valeurs autour de zéro, d'où l'échelle linéaire) ; au-dessus, la poussière de la Galaxie.
    'planck30': dict(
        hips='CDS/P/PLANCK/R3/LFI30', bande='micro-ondes', libelle='Micro-ondes 30 GHz (Planck)',
        mesure="Brillance du ciel à 30 GHz (surtout synchrotron et fond cosmologique)",
        unite='K_CMB', resolution_arcmin=32.3, longueur_onde='1 cm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='lin',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_030-field-IQU_1024_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_030-field-IQU_1024_R3.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_030_1024_R3.00_full.fits'])]),
    'planck44': dict(
        hips='CDS/P/PLANCK/R3/LFI44', bande='micro-ondes', libelle='Micro-ondes 44 GHz (Planck)',
        mesure="Brillance du ciel à 44 GHz",
        unite='K_CMB', resolution_arcmin=27.0, longueur_onde='6,8 mm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='lin',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_044-field-IQU_1024_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_044-field-IQU_1024_R3.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_044_1024_R3.00_full.fits'])]),
    'planck70': dict(
        hips='CDS/P/PLANCK/R3/LFI70', bande='micro-ondes', libelle='Micro-ondes 70 GHz (Planck)',
        mesure="Brillance du ciel à 70 GHz (fond diffus cosmologique)",
        unite='K_CMB', resolution_arcmin=13.2, longueur_onde='4,3 mm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='lin',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_070-field-IQU_1024_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_070-field-IQU_1024_R3.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/LFI_SkyMap_070_1024_R3.00_full.fits'])]),
    'planck100': dict(
        hips='CDS/P/PLANCK/R3/HFI100', bande='micro-ondes', libelle='Micro-ondes 100 GHz (Planck)',
        mesure="Brillance du ciel à 100 GHz (fond diffus cosmologique)",
        unite='K_CMB', resolution_arcmin=9.7, longueur_onde='3 mm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='lin',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_100-field-IQU_2048_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_100_2048_R3.01_full.fits'])]),
    'planck143': dict(
        hips='CDS/P/PLANCK/R3/HFI143', bande='micro-ondes', libelle='Micro-ondes 143 GHz (Planck)',
        mesure="Brillance du ciel à 143 GHz (fond diffus cosmologique)",
        unite='K_CMB', resolution_arcmin=7.3, longueur_onde='2,1 mm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='lin',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_143-field-IQU_2048_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_143_2048_R3.01_full.fits'])]),
    'planck217': dict(
        hips='CDS/P/PLANCK/R3/HFI217', bande='micro-ondes', libelle='Micro-ondes 217 GHz (Planck)',
        mesure="Brillance du ciel à 217 GHz",
        unite='K_CMB', resolution_arcmin=5.0, longueur_onde='1,4 mm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='lin',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_217-field-IQU_2048_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_217_2048_R3.01_full.fits'])]),
    'planck353': dict(
        hips='CDS/P/PLANCK/R3/HFI353', bande='micro-ondes', libelle='Micro-ondes 353 GHz (Planck)',
        mesure="Brillance du ciel à 353 GHz (surtout la poussière froide de la Galaxie)",
        unite='K_CMB', resolution_arcmin=4.9, longueur_onde='850 µm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_353-field-IQU_2048_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_353_2048_R3.01_full.fits'])]),
    'planck545': dict(
        hips='CDS/P/PLANCK/R3/HFI545', bande='micro-ondes', libelle='Micro-ondes 545 GHz (Planck)',
        mesure="Brillance du ciel à 545 GHz (poussière froide)",
        unite='MJy/sr', resolution_arcmin=4.8, longueur_onde='550 µm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_545-field-I_2048_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_545_2048_R3.01_full.fits'])]),
    'planck857': dict(
        hips='CDS/P/PLANCK/R3/HFI857', bande='micro-ondes', libelle='Micro-ondes 857 GHz (Planck)',
        mesure="Brillance du ciel à 857 GHz (poussière froide)",
        unite='MJy/sr', resolution_arcmin=4.6, longueur_onde='350 µm',
        reference='Planck Collaboration 2020, A&A 641, A1 (PR3) ; cartes HEALPix de la Planck Legacy Archive (ESA)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(fichiers=['https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_857-field-I_2048_R4.00_full.fits', 'https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/HFI_SkyMap_857_2048_R3.01_full.fits'])]),

    # --- Infrarouge lointain : AKARI, instrument FIS (JAXA), relevé du ciel entier.
    'akari90': dict(
        hips='CDS/P/AKARI/FIS/WideS', bande='infrarouge', libelle='Infrarouge lointain 90 µm (AKARI)',
        mesure='Brillance du ciel à 90 µm (poussière tiède chauffée par les étoiles)', unite='MJy/sr',
        resolution_arcmin=1.3, longueur_onde='90 µm',
        reference='Doi et al. 2015, PASJ 67, 50 (AKARI FIS, relevé du ciel entier)',
        couverture_publiee='98 % du ciel', echelle='log',
        secours=[dict(hips='ov-gso/P/AKARI/WideS', reference='Doi et al. 2015, PASJ 67, 50 (AKARI FIS, relevé du ciel entier) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
    'akari140': dict(
        hips='CDS/P/AKARI/FIS/WideL', bande='infrarouge', libelle='Infrarouge lointain 140 µm (AKARI)',
        mesure='Brillance du ciel à 140 µm (poussière froide)', unite='MJy/sr',
        resolution_arcmin=1.5, longueur_onde='140 µm',
        reference='Doi et al. 2015, PASJ 67, 50 (AKARI FIS, relevé du ciel entier)',
        couverture_publiee='98 % du ciel', echelle='log',
        secours=[dict(hips='ov-gso/P/AKARI/WideL', reference='Doi et al. 2015, PASJ 67, 50 (AKARI FIS, relevé du ciel entier) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
    # --- Infrarouge moyen et proche : WISE (NASA) et 2MASS. Valeurs en unités brutes du détecteur (DN), comme publiées.
    'wise12': dict(
        hips='CDS/P/allWISE/W3', bande='infrarouge', libelle='Infrarouge moyen 12 µm (WISE)',
        mesure='Brillance du ciel à 12 µm (grains de poussière chauds, molécules aromatiques)', unite='DN (unité du détecteur)',
        resolution_arcmin=6.5 / 60, longueur_onde='12 µm',
        reference='Wright et al. 2010, AJ 140, 1868 ; AllWISE (Cutri et al. 2013, IPAC)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(adresse='https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/W3', reference="Wright et al. 2010, AJ 140, 1868 ; AllWISE (Cutri et al. 2013, IPAC) ; tuiles HiPS du CDS, copie de l'IRSA")]),
    'wise22': dict(
        hips='CDS/P/allWISE/W4', bande='infrarouge', libelle='Infrarouge moyen 22 µm (WISE)',
        mesure='Brillance du ciel à 22 µm', unite='DN (unité du détecteur)',
        resolution_arcmin=12.0 / 60, longueur_onde='22 µm',
        reference='Wright et al. 2010, AJ 140, 1868 ; AllWISE (Cutri et al. 2013, IPAC)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(adresse='https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/W4', reference="Wright et al. 2010, AJ 140, 1868 ; AllWISE (Cutri et al. 2013, IPAC) ; tuiles HiPS du CDS, copie de l'IRSA")]),
    'wise3': dict(
        hips='CDS/P/allWISE/W1', bande='infrarouge', libelle='Infrarouge proche 3,4 µm (WISE)',
        mesure='Brillance du ciel à 3,4 µm (surtout la lumière des étoiles)', unite='DN (unité du détecteur)',
        resolution_arcmin=6.1 / 60, longueur_onde='3,4 µm',
        reference='Wright et al. 2010, AJ 140, 1868 ; AllWISE (Cutri et al. 2013, IPAC)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(adresse='https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/W1', reference="Wright et al. 2010, AJ 140, 1868 ; AllWISE (Cutri et al. 2013, IPAC) ; tuiles HiPS du CDS, copie de l'IRSA")]),
    '2massk': dict(
        hips='CDS/P/2MASS/K', bande='infrarouge', libelle='Infrarouge proche 2,2 µm (2MASS K)',
        mesure='Brillance du ciel en bande Ks (2,2 µm)', unite='DN (unité du détecteur)',
        resolution_arcmin=2.5 / 60, longueur_onde='2,2 µm',
        reference='Skrutskie et al. 2006, AJ 131, 1163 (2MASS)',
        couverture_publiee='tout le ciel', echelle='log'),
    # --- Visible : la raie Hα de l'hydrogène ionisé (les étoiles visibles sont déjà dessinées une à une par Gaia).
    'halpha': dict(
        hips='CDS/P/Finkbeiner', bande='visible', libelle='Visible : raie Hα (hydrogène ionisé)',
        mesure="Brillance de la raie Hα à 656 nm (gaz ionisé par les étoiles chaudes)", unite='R (rayleighs)',
        resolution_arcmin=6.0, longueur_onde='656 nm',
        reference='Finkbeiner 2003, ApJS 146, 407 (assemblage des relevés WHAM, VTSS et SHASSA)',
        couverture_publiee='tout le ciel', echelle='log'),
    # --- Ultraviolet : GALEX (NASA). Le plan de la Galaxie a été évité (étoiles trop brillantes pour les détecteurs).
    'galexfuv': dict(
        hips='CDS/P/GALEXGR6_7/FUV', bande='ultraviolet', libelle='Ultraviolet lointain 154 nm (GALEX)',
        mesure='Brillance du ciel en ultraviolet lointain (étoiles chaudes, lumière diffusée par la poussière)',
        unite='MJy/sr × 2,04', resolution_arcmin=4.2 / 60, longueur_onde='154 nm',
        reference='Martin et al. 2005, ApJ 619, L1 ; Bianchi et al. 2017, ApJS 230, 24 (GALEX GR6/7)',
        couverture_publiee='environ 2/3 du ciel, plan galactique évité', echelle='log',
        secours=[dict(adresse='https://irsa.ipac.caltech.edu/data/hips/CDS/GALEX/GR6-03-2014/AIS-FD', unite='unité du relevé (non précisée par la fiche)', reference="Martin et al. 2005, ApJ 619, L1 ; relevé AIS de GALEX GR6 (tuiles HiPS du CDS, copie de l'IRSA)")]),
    'galexnuv': dict(
        hips='CDS/P/GALEXGR6_7/NUV', bande='ultraviolet', libelle='Ultraviolet proche 231 nm (GALEX)',
        mesure='Brillance du ciel en ultraviolet proche', unite='MJy/sr × 0,72',
        resolution_arcmin=5.3 / 60, longueur_onde='231 nm',
        reference='Martin et al. 2005, ApJ 619, L1 ; Bianchi et al. 2017, ApJS 230, 24 (GALEX GR6/7)',
        couverture_publiee='environ 3/4 du ciel, plan galactique évité', echelle='log',
        secours=[dict(adresse='https://irsa.ipac.caltech.edu/data/hips/CDS/GALEX/GR6-03-2014/AIS-ND', unite='unité du relevé (non précisée par la fiche)', reference="Martin et al. 2005, ApJ 619, L1 ; relevé AIS de GALEX GR6 (tuiles HiPS du CDS, copie de l'IRSA)")]),
    # --- Rayons X.
    'rass': dict(
        hips='CDS/P/RASS', bande='X', libelle='Rayons X mous 0,1 à 2,4 keV (ROSAT)',
        mesure='Photons X comptés (gaz à un million de degrés, restes de supernovas, amas de galaxies)',
        unite='coups (unité du relevé)', resolution_arcmin=1.8, longueur_onde='0,5 à 12 nm',
        reference='Voges et al. 1999, A&A 349, 389 (ROSAT All-Sky Survey, MPE)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(hips='ov-gso/P/RASS', unite='coups/s', reference='Voges et al. 1999, A&A 349, 389 (ROSAT All-Sky Survey, MPE) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
    'erosita': dict(
        hips='erosita/dr1/rate/024', bande='X', libelle='Rayons X 0,2 à 2,3 keV (eROSITA DR1)',
        mesure='Taux de photons X comptés', unite='coups/s par pixel',
        resolution_arcmin=0.5, longueur_onde='0,5 à 6 nm',
        reference='Merloni et al. 2024, A&A 682, A34 (eROSITA-DE DR1, MPE)',
        couverture_publiee='moitié du ciel seulement : longitudes galactiques 180° à 360° (droits allemands)', echelle='log'),
    'integral': dict(
        hips='CDS/P/INTGAL/35', bande='X', libelle='Rayons X durs 17 à 35 keV (INTEGRAL)',
        mesure='Photons X durs comptés (trous noirs et étoiles à neutrons qui avalent de la matière)',
        unite='unité du relevé (non précisée par la fiche)', resolution_arcmin=12.0, longueur_onde='0,04 à 0,07 nm',
        reference='Krivonos et al. 2012, A&A 545, A27 (INTEGRAL/IBIS, plan galactique, IKI)',
        couverture_publiee='bande autour du plan de la Galaxie (31 % du ciel)', echelle='lin',
        secours=[dict(hips='ov-gso/P/INTEGRAL/17-35keV', unite='mCrab', reference='Krivonos et al. 2012, A&A 545, A27 (INTEGRAL/IBIS, plan galactique, IKI) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
    # --- Rayons gamma : Fermi-LAT (NASA), cartes de SkyView (HEASARC).
    'fermi1': dict(
        hips='CDS/P/Fermi/3', bande='gamma', libelle='Gamma 300 MeV à 1 GeV (Fermi-LAT)',
        mesure='Photons gamma comptés (300 MeV à 1 GeV)', unite='coups (unité du relevé)',
        resolution_arcmin=60.0, longueur_onde='moins de 1e-6 nm',
        reference='Atwood et al. 2009, ApJ 697, 1071 (Fermi-LAT) ; cartes SkyView (HEASARC, NASA)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(hips='ov-gso/P/Fermi/Band3', unite='coups/s/cm²/sr', resolution_arcmin=60.0, reference='Atwood et al. 2009, ApJ 697, 1071 (Fermi-LAT) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
    'fermi2': dict(
        hips='CDS/P/Fermi/4', bande='gamma', libelle='Gamma 1 à 3 GeV (Fermi-LAT)',
        mesure='Photons gamma comptés (1 à 3 GeV)', unite='coups (unité du relevé)',
        resolution_arcmin=30.0, longueur_onde='moins de 1e-6 nm',
        reference='Atwood et al. 2009, ApJ 697, 1071 (Fermi-LAT) ; cartes SkyView (HEASARC, NASA)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(hips='ov-gso/P/Fermi/Band4', unite='coups/s/cm²/sr', resolution_arcmin=24.0, reference='Atwood et al. 2009, ApJ 697, 1071 (Fermi-LAT) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
    'fermi3': dict(
        hips='CDS/P/Fermi/5', bande='gamma', libelle='Gamma 3 à 300 GeV (Fermi-LAT)',
        mesure='Photons gamma comptés (3 à 300 GeV)', unite='coups (unité du relevé)',
        resolution_arcmin=10.0, longueur_onde='moins de 1e-6 nm',
        reference='Atwood et al. 2009, ApJ 697, 1071 (Fermi-LAT) ; cartes SkyView (HEASARC, NASA)',
        couverture_publiee='tout le ciel', echelle='log',
        secours=[dict(hips='ov-gso/P/Fermi/Band5', unite='coups/s/cm²/sr', resolution_arcmin=12.0, reference='Atwood et al. 2009, ApJ 697, 1071 (Fermi-LAT) ; carte HEALPix de D. Paradis (IRAP/CADE, Toulouse)')]),
}


def lire_texte(url, essais=4):
    for k in range(essais):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:      # coupure réseau : on réessaie, de plus en plus lentement
            if k == essais - 1:
                raise
            time.sleep(2 ** k)


def proprietes(hips_id, adresse=None):
    """Fiche du relevé (fichier properties) : adresse du serveur, repère, largeur des tuiles, ordre maximal.
    adresse : serveur connu du relevé (copie publiée par un autre centre, par exemple l'IRSA) ; sa fiche est lue
    directement, sans passer par le registre du CDS."""
    if adresse:
        rec = lire_texte(adresse.rstrip('/') + '/properties') + f'\nhips_service_url = {adresse}\n'
    else:
        rec = lire_texte(MOC + '?' + urllib.parse.urlencode({'ID': hips_id, 'get': 'record'}))
    p = {}
    for ligne in rec.splitlines():
        if '=' in ligne and not ligne.lstrip().startswith('#'):
            k, v = ligne.split('=', 1)
            k, v = k.strip(), v.strip()
            p.setdefault(k, v)
    # hips_service_url, _1, _2... sont des miroirs : on garde le premier qui répond vraiment (le 12/11/2026 le serveur
    # du CDS répondait 404 à toutes les tuiles, ce qui faisait croire à un ciel vide).
    adresses = [p[k] for k in sorted(p) if k.startswith('hips_service_url')]
    for adr in adresses:
        try:
            with urllib.request.urlopen(adr.rstrip('/') + '/properties', timeout=30) as r:
                if r.status == 200:
                    p['hips_service_url'] = adr
                    break
        except Exception:
            continue
    else:
        raise SystemExit(f'{hips_id} : aucun serveur ne répond ({", ".join(adresses) or "aucune adresse dans la fiche"})')
    if 'fits' not in p.get('hips_tile_format', ''):
        raise SystemExit(f'{hips_id} : pas de tuiles FITS (formats : {p.get("hips_tile_format")})')
    return p


def lire_fits(octets):
    """Image FITS d'une tuile : tableau [ligne][colonne] en float64, NaN là où rien n'est mesuré. Ligne 0 = bas de l'image
    (premier pixel écrit dans le fichier, convention FITS)."""
    entete, i = {}, 0
    while True:
        bloc = octets[i:i + 2880]
        i += 2880
        fin = False
        for j in range(0, 2880, 80):
            carte = bloc[j:j + 80].decode('ascii', 'replace')
            cle = carte[:8].strip()
            if cle == 'END':
                fin = True
                break
            if carte[8:10] == '= ':
                v = carte[10:].split('/')[0].strip().strip("'").strip()
                entete[cle] = v
        if fin:
            break
    bitpix, nx, ny = int(entete['BITPIX']), int(entete['NAXIS1']), int(entete['NAXIS2'])
    typ = {8: '>u1', 16: '>i2', 32: '>i4', 64: '>i8', -32: '>f4', -64: '>f8'}[bitpix]
    a = np.frombuffer(octets, dtype=typ, count=nx * ny, offset=i).reshape(ny, nx).astype(np.float64)
    if bitpix > 0 and 'BLANK' in entete:
        a[a == float(entete['BLANK'])] = np.nan
    a = a * float(entete.get('BSCALE', 1)) + float(entete.get('BZERO', 0))
    return a


def tuile_vers_emboite(w):
    """Pour une tuile de w × w pixels : index HEALPix emboîté (dans la tuile) de chaque pixel [ligne][colonne].

    Norme HiPS 1.0, § 4.2 et code d'Aladin (cds.tools.pixtools) : le numéro emboîté du sous-pixel s'obtient en
    entrelaçant les bits de x (bits pairs) et de y (bits impairs). Placement retenu : la ligne FITS comptée depuis le
    haut est x, la colonne FITS est y. Mesuré le 12/11/2026 sur Haslam 408 MHz et HI4PI : c'est la seule des huit
    poses de tuile qui donne un ciel continu aux bords des tuiles (voir continuite() ; l'ancienne pose, ligne = y et
    colonne = x, laissait des coutures nettes à l'écran)."""
    n = np.arange(w * w, dtype=np.int64)
    x = np.zeros_like(n)
    y = np.zeros_like(n)
    for b in range(int(math.log2(w))):
        x |= ((n >> (2 * b)) & 1) << b
        y |= ((n >> (2 * b + 1)) & 1) << b
    table = np.empty((w, w), dtype=np.int64)
    table[w - 1 - x, y] = n      # ligne FITS comptée depuis le bas dans le tableau
    return table


def telecharger(adresse, ordre, n, cache):
    chemin = os.path.join(cache, f'Norder{ordre}', f'Npix{n}.fits')
    if os.path.exists(chemin):
        with open(chemin, 'rb') as f:
            return f.read()
    url = f'{adresse}/Norder{ordre}/Dir{(n // 10000) * 10000}/Npix{n}.fits'
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                octets = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:      # tuile absente : le relevé ne couvre pas ce morceau de ciel
                return b''         # pas mise en cache : un 404 passager du serveur ne doit pas devenir un trou permanent
            if k == 4:
                raise
            time.sleep(2 ** k)
        except Exception:
            if k == 4:
                raise
            time.sleep(2 ** k)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin + '.part', 'wb') as f:
        f.write(octets)
    os.replace(chemin + '.part', chemin)
    return octets


# --- HEALPix : direction vers numéro de pixel emboîté (Górski et al. 2005, ApJ 622, 759 ; même calcul que le shader
# natif/shaders/ciel_bandes.frag). Vérifié identique à healpy.ang2pix(nest=True) sur 2 millions de directions tirées au
# hasard, Nside 1 à 4096 (12 novembre 2026).
def spread(v):
    r = np.zeros_like(v)
    for b in range(30): r |= ((v >> b) & 1) << (2*b)
    return r
def ang2pix_nest(nside, theta, phi):
    z = np.cos(theta); za = np.abs(z)
    tt = np.mod(phi, 2*np.pi) / (np.pi/2)
    face = np.zeros(z.shape, np.int64); ix = np.zeros_like(face); iy = np.zeros_like(face)
    eq = za <= 2/3
    t1 = nside*(0.5+tt); t2 = nside*z*0.75
    jp = (t1-t2).astype(np.int64); jm = (t1+t2).astype(np.int64)
    ifp = jp // nside; ifm = jm // nside
    f_eq = np.where(ifp == ifm, ifp | 4, np.where(ifp < ifm, ifp, ifm + 8))
    ix_eq = jm & (nside-1); iy_eq = nside - (jp & (nside-1)) - 1
    ntt = np.minimum(tt.astype(np.int64), 3); tp = tt - ntt
    tmp = nside*np.sqrt(3*(1-za))
    jp2 = np.minimum((tp*tmp).astype(np.int64), nside-1); jm2 = np.minimum(((1-tp)*tmp).astype(np.int64), nside-1)
    f_p = np.where(z >= 0, ntt, ntt+8)
    ix_p = np.where(z >= 0, nside-jm2-1, jp2); iy_p = np.where(z >= 0, nside-jp2-1, jm2)
    face = np.where(eq, f_eq, f_p); ix = np.where(eq, ix_eq, ix_p); iy = np.where(eq, iy_eq, iy_p)
    return face*nside*nside + spread(ix) + 2*spread(iy)


# Équatorial (ICRS) vers galactique : matrice de Hipparcos (ESA 1997, vol. 1, § 1.5.3).
GAL = np.array([[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
                [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
                [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669]])


def contraste_plan(carte, nside, galactique):
    """Rapport entre la médiane des pixels près du plan de la Galaxie (|b| < 3°) et loin de lui (|b| > 40°). Pour une carte
    bien assemblée d'un relevé qui voit la Galaxie, le plan ressort nettement ; mal orientée, il se brouille."""
    rng = np.random.default_rng(0)
    l = rng.uniform(0, 2 * np.pi, 400_000)
    sb = rng.uniform(-1, 1, 400_000)
    b = np.arcsin(sb)
    v = np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), sb])
    if not galactique:
        v = GAL.T @ v      # galactique vers équatorial
    th = np.arccos(np.clip(v[2], -1, 1))
    ph = np.arctan2(v[1], v[0])
    val = carte[ang2pix_nest(nside, th, ph)]
    pres, loin = val[np.abs(b) < np.radians(3)], val[np.abs(b) > np.radians(40)]
    pres, loin = pres[np.isfinite(pres)], loin[np.isfinite(loin)]
    if len(pres) < 100 or len(loin) < 100:
        return float('nan')
    return float(np.median(pres) / np.median(loin))


def continuite(carte, nside):
    """Saut moyen du logarithme entre pixels voisins, face HEALPix par face. Le relevé est lissé à sa finesse (bien plus
    large qu'un pixel de la carte) : une tuile mal posée crée des coutures à ses bords et fait monter ce saut."""
    i = np.arange(nside, dtype=np.int64)
    ix, iy = np.meshgrid(i, i, indexing='ij')
    sous = spread(ix) + 2 * spread(iy)
    lg = np.log(np.maximum(carte.astype(np.float64), 1e-30))
    total = 0.0
    for f in range(12):
        im = lg[f * nside * nside + sous]
        total += np.nanmean(np.abs(np.diff(im, axis=0))) + np.nanmean(np.abs(np.diff(im, axis=1)))
    return total / 12


def orientations(w):
    """Les huit façons de poser une tuile (miroirs et transposée) ; 0 = celle de la norme."""
    t0 = tuile_vers_emboite(w)
    res = []
    for o in range(8):
        t = t0
        if o & 1: t = t[::-1, :]
        if o & 2: t = t[:, ::-1]
        if o & 4: t = t.T
        res.append(np.ascontiguousarray(t))
    return res


# --- Cartes HEALPix entières (FITS, table binaire), quand l'équipe du relevé publie la carte elle-même : Planck.
_JRLL = np.array([2,2,2,2,3,3,3,3,4,4,4,4]); _JPLL = np.array([1,3,5,7,0,2,4,6,1,3,5,7])
def ring_vers_emboite(nside, pix):
    """Numéro HEALPix « en anneaux » vers « emboîté » (algorithme de pix2xyf_ring, Górski et al. 2005, code C de HEALPix)."""
    pix = np.asarray(pix, dtype=np.int64)
    ncap = 2*nside*(nside-1); npix = 12*nside*nside; nl2 = 2*nside
    iring = np.zeros_like(pix); iphi = np.zeros_like(pix); kshift = np.zeros_like(pix); nr = np.zeros_like(pix); face = np.zeros_like(pix)
    n = (pix < ncap)
    ir = (1 + np.floor(np.sqrt(1 + 2*pix[n].astype(np.float64)))).astype(np.int64) >> 1
    ip = pix[n] - 2*ir*(ir-1) + 1  # 1-based in ring
    # correct possible float error
    iring[n] = ir; iphi[n] = ip; kshift[n] = 0; nr[n] = ir; face[n] = (ip-1)//ir
    e = (pix >= ncap) & (pix < npix-ncap)
    ip_ = pix[e] - ncap; tmp = ip_ // (4*nside)
    ir = tmp + nside; ph = ip_ - tmp*4*nside + 1
    ks = (ir + nside) & 1; nrr = np.full_like(ir, nside)
    ire = ir - nside + 1; irm = nl2 + 2 - ire
    ifm = (ph - ks//2 + nside - 1) // nside; ifp = (ph - irm//2 + nside - 1)//nside  # placeholder fixed below
    ifm = (ph - (ks + ire)//2 + nside - 1) // nside  # not used
    # use standard formulas
    ifm = (ph - (ire - ks)//2*0 - 1)  # dummy
    iring[e] = ir; iphi[e] = ph; kshift[e] = ks; nr[e] = nrr
    ire_ = ir - nside + 1; irm_ = nl2 + 2 - ire_
    ifm_ = (ph - ire_//2 + nside - 1) // nside
    ifp_ = (ph - irm_//2 + nside - 1) // nside
    face[e] = np.where(ifp_ == ifm_, (ifp_ | 4), np.where(ifp_ < ifm_, ifp_, ifm_ + 8))
    s = pix >= npix - ncap
    ip_ = npix - pix[s]
    ir = (1 + np.floor(np.sqrt(2*ip_.astype(np.float64) - 1))).astype(np.int64) >> 1
    ph = 4*ir + 1 - (ip_ - 2*ir*(ir-1))
    iring[s] = 2*nl2 - ir; iphi[s] = ph; kshift[s] = 0; nr[s] = ir; face[s] = (ph-1)//ir + 8
    irt = iring - _JRLL[face]*nside + 1
    ipt = 2*iphi - _JPLL[face]*nr - kshift - 1
    ipt = np.where(ipt >= nl2, ipt - 8*nside, ipt)
    ix = (ipt - irt) >> 1; iy = (-ipt - irt) >> 1
    return face*nside*nside + spread(ix) + 2*spread(iy)


def telecharger_fichier(url, chemin):
    """Téléchargement d'un gros fichier, reprise possible après coupure (en-tête Range). Renvoie False si absent (404)."""
    if os.path.exists(chemin):
        return True
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    part = chemin + '.part'
    for k in range(6):
        deja = os.path.getsize(part) if os.path.exists(part) else 0
        req = urllib.request.Request(url, headers={'Range': f'bytes={deja}-'} if deja else {})
        try:
            with urllib.request.urlopen(req, timeout=120) as rep, open(part, 'ab' if deja and rep.status == 206 else 'wb') as f:
                total = int(rep.headers.get('Content-Length', 0)) + (deja if rep.status == 206 else 0)
                t0, recu = time.time(), (deja if rep.status == 206 else 0)
                while True:
                    bloc = rep.read(1 << 22)
                    if not bloc:
                        break
                    f.write(bloc)
                    recu += len(bloc)
                    if time.time() - t0 > 20:
                        print(f'  {recu / 1e6:.0f} / {total / 1e6:.0f} Mo', flush=True)
                        t0 = time.time()
            os.replace(part, chemin)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if k == 5:
                raise
        except Exception:
            if k == 5:
                raise
        time.sleep(2 ** k)
    return False


def lire_table_healpix(chemin, nside_max):
    """Carte HEALPix d'un fichier FITS (1re extension, table binaire). Renvoie la 1re colonne (l'intensité, I_STOKES chez
    Planck) en ordre emboîté, ramenée à Nside <= nside_max par moyenne des pixels enfants (la somme du mesuré), avec
    son repère et son unité. Aucune autre valeur n'est modifiée."""
    with open(chemin, 'rb') as f:
        def entete():
            h = {}
            while True:
                bloc = f.read(2880)
                fin = False
                for j in range(0, 2880, 80):
                    carte = bloc[j:j + 80].decode('ascii', 'replace')
                    cle = carte[:8].strip()
                    if cle == 'END':
                        fin = True
                        break
                    if carte[8:10] == '= ':
                        h.setdefault(cle, carte[10:].split('/')[0].strip().strip("'").strip())
                if fin:
                    return h
        h0 = entete()
        taille0 = abs(int(h0.get('BITPIX', 8))) // 8 * (int(h0.get('NAXIS1', 0)) * int(h0.get('NAXIS2', 1)) if int(h0.get('NAXIS', 0)) else 0)
        f.seek((taille0 + 2879) // 2880 * 2880, 1)
        h = entete()
        debut = f.tell()
    codes = {'E': '>f4', 'D': '>f8', 'J': '>i4', 'I': '>i2', 'K': '>i8', 'B': 'u1'}
    champs = []
    for c in range(1, int(h['TFIELDS']) + 1):
        tf = h[f'TFORM{c}']
        n = int(tf[:-1]) if len(tf) > 1 else 1
        champs.append((f'c{c}', codes[tf[-1]], (n,)))
    lignes = int(h['NAXIS2'])
    table = np.memmap(chemin, dtype=np.dtype(champs), mode='r', offset=debut, shape=(lignes,))
    v = np.asarray(table['c1'], dtype=np.float32).ravel()
    nside = int(h['NSIDE'])
    if v.size != 12 * nside * nside:
        raise SystemExit(f'{chemin} : {v.size} pixels pour Nside {nside}')
    v[(v < -1.6e30) | ~np.isfinite(v)] = np.nan      # valeur conventionnelle « pas de mesure » de HEALPix : -1,6375e30
    if h.get('ORDERING', 'NESTED').upper().startswith('RING'):
        e = np.empty_like(v)
        for d in range(0, v.size, 1 << 24):
            idx = np.arange(d, min(d + (1 << 24), v.size), dtype=np.int64)
            e[ring_vers_emboite(nside, idx)] = v[idx]
        v = e
    while nside > nside_max:      # moyenne des 4 enfants (ordre emboîté) : un pixel vide reste vide si ses 4 enfants le sont
        v = np.nanmean(v.reshape(-1, 4), axis=1).astype(np.float32)
        nside //= 2
    coord = h.get('COORDSYS', 'G').upper()
    repere = 'galactic' if coord.startswith('G') else 'equatorial'
    return v, nside, repere, h.get('TUNIT1', '')


def carte_entiere(r, a):
    """Essaie les fichiers proposés dans l'ordre et lit le premier présent sur le serveur."""
    cache = os.path.join(a.sortie, 'cache_cartes')
    for url in r['fichiers']:
        chemin = os.path.join(cache, url.rsplit('/', 1)[1])
        print(f'  essai {url}', flush=True)
        if telecharger_fichier(url, chemin):
            with open(chemin, 'rb') as f:
                if f.read(6) != b'SIMPLE':      # page d'erreur du serveur au lieu d'un FITS : on la jette
                    print('  pas un fichier FITS : ignoré', flush=True)
                    f.close()
                    os.replace(chemin, chemin + '.pas_fits')
                    continue
            v, nside, repere, unite = lire_table_healpix(chemin, a.nside_max)
            print(f'  lu : Nside {nside}, repère {repere}, unité {unite!r}', flush=True)
            return v, nside, repere, unite, url
    raise SystemExit(f'{r["libelle"]} : aucun des fichiers proposés n\'est sur le serveur')


def reference_planck(url, ref):
    if 'R4.00' in url:
        return 'Planck Collaboration 2020, A&A 643, A42 (PR4, traitement NPIPE) ; cartes HEALPix de la Planck Legacy Archive (ESA), copie IRSA'
    return ref


def controle_ordre(adresse, ordre, w, cache, table, nb=16):
    """Compare la carte faite à l'ordre `ordre` avec l'ordre au-dessus ramené à la même finesse (moyenne des 4 enfants
    mesurés, ordre emboîté), sur `nb` tuiles réparties sur le ciel. Renvoie l'écart relatif des médianes (None si rien à
    comparer). Raison : le 12/11/2026 les tuiles d'ordre 2 de la copie IRSA de WISE W3 et W4 étaient identiques entre
    elles et sans rapport avec l'ordre 3 (moyenne 0,54 contre 273 et 103)."""
    ntuiles = 12 * 4 ** ordre
    gros, fins = [], []
    for n in np.linspace(0, ntuiles - 1, nb).astype(int):
        octets = telecharger(adresse, ordre, int(n), cache)
        enfants = [telecharger(adresse, ordre + 1, 4 * int(n) + k, cache) for k in range(4)]
        if not octets or not all(enfants):
            continue
        parent = np.full(w * w, np.nan)
        parent[table] = lire_fits(octets)
        fin = np.full(4 * w * w, np.nan)
        for k, e in enumerate(enfants):
            fin[k * w * w + table] = lire_fits(e)
        with np.errstate(all='ignore'):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                fin = np.nanmean(fin.reshape(-1, 4), axis=1)
        gros.append(parent); fins.append(fin)
    if not gros:
        print(f'  contrôle ordre {ordre} / {ordre + 1} : aucune tuile comparable')
        return None
    g, f = np.concatenate(gros), np.concatenate(fins)
    mg, mf, quoi = np.nanmedian(g), np.nanmedian(f), 'médianes'
    if mf == 0 or not np.isfinite(mf):       # carte de comptage presque vide : les médianes valent 0, on prend les moyennes
        mg, mf, quoi = np.nanmean(g), np.nanmean(f), 'moyennes'
    ecart = abs(mg - mf) / abs(mf) if mf else float('inf')
    print(f'  contrôle ordre {ordre} / {ordre + 1} (moyenne des 4 enfants), {len(gros)} tuiles : {quoi} {mg:.4g} et {mf:.4g}, '
          f'écart {ecart * 100:.1f} %')
    if ecart > 0.2:
        print(f'  ATTENTION : l’ordre {ordre} ne colle pas à l’ordre {ordre + 1} (écart {ecart * 100:.0f} %) : '
              f'relancer avec --depuis-ordre-plus-fin 1')
    return ecart


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sortie')
    ap.add_argument('nom', nargs='?')
    ap.add_argument('--ordre', type=int, help='ordre HiPS imposé (sinon : le plus fin sans dépasser --nside-max)')
    ap.add_argument('--nside-max', type=int, default=2048)
    ap.add_argument('--simultanes', type=int, default=8)
    ap.add_argument('--cache')
    ap.add_argument('--depuis-ordre-plus-fin', type=int, default=None, dest='plus_fin',
                    help="télécharge N ordres plus fins et ramène la carte à la finesse voulue par moyenne des 4 enfants "
                         "(sinon : 'ordre_source_plus' de la fiche, 0 par défaut)")
    ap.add_argument('--controle-seul', action='store_true', help="seulement comparer l'ordre choisi et l'ordre au-dessus")
    ap.add_argument('--liste', action='store_true')
    a = ap.parse_args()
    if a.liste or not a.nom:
        for k, r in RELEVES.items():
            print(f'{k:12s} {r["libelle"]:28s} {r["hips"]}')
        return
    # Relevé principal, puis ses copies publiées ailleurs (même relevé, même bande ; seuls l'unité ou la référence de
    # la copie changent, écrites dans 'secours'). Ajouté le 12/11/2026 : le serveur du CDS ne servait plus aucune tuile.
    p = None
    for r in [RELEVES[a.nom]] + [dict(RELEVES[a.nom], **s) for s in RELEVES[a.nom].get('secours', [])]:
        r.pop('secours', None)
        try:
            if r.get('fichiers'):      # carte HEALPix entière publiée par l'équipe du relevé (pas de tuiles)
                p = {}
                break
            p = proprietes(r['hips'], r.get('adresse'))
            break
        except (Exception, SystemExit) as e:   # proprietes() signale « aucun serveur » par SystemExit
            print(f'  {e} ; copie suivante', flush=True)
    if p is None:
        raise SystemExit(f'{a.nom} : aucune copie du relevé ne répond')
    if r.get('fichiers'):
        carte, nside, repere, unite, url = carte_entiere(r, a)
        r = dict(r, unite=unite or r['unite'], serveur=url, reference=reference_planck(url, r['reference']))
        r.pop('fichiers', None)
        ordre = ordre_max = w = absentes = None
        adresse = url
    else:
        adresse = p['hips_service_url'].rstrip('/')
        w = int(p.get('hips_tile_width', 512))
        ordre_max = int(p.get('hips_order', a.ordre))
        ordre = a.ordre if a.ordre is not None else max(0, min(ordre_max, int(math.log2(a.nside_max // w)) if a.nside_max >= w else 0))
        ordre = min(ordre, ordre_max)
        repere = p.get('hips_frame', 'equatorial')
        plus = a.plus_fin if a.plus_fin is not None else int(r.get('ordre_source_plus', 0))
        plus = max(0, min(plus, ordre_max - ordre))
        nside = w << ordre
        ordre_dl = ordre + plus
        ntuiles = 12 * 4 ** ordre_dl
        # une copie de secours a son propre cache : ses tuiles ne doivent jamais se mêler à celles du relevé principal
        sous = a.nom if r['hips'] == RELEVES[a.nom]['hips'] else a.nom + '__' + r['hips'].replace('/', '_')
        cache = a.cache or os.path.join(a.sortie, 'cache_hips', sous)
        print(f'{r["libelle"]} : {r["hips"]}, serveur {adresse}, repère {repere}, tuiles {w} px, ordre {ordre} '
              f'(maximum {ordre_max}), Nside {nside}, {ntuiles} tuiles'
              + (f' (téléchargées à l’ordre {ordre_dl}, puis moyenne des enfants mesurés)' if plus else ''))

        tables = orientations(w)
        table = tables[0]
        if a.controle_seul:
            controle_ordre(adresse, ordre, w, cache, table)
            return
        nside_dl = w << ordre_dl
        carte = np.full(12 * nside_dl * nside_dl, np.nan, dtype=np.float32)
        absentes = 0
        t0 = time.time()
        with cf.ThreadPoolExecutor(a.simultanes) as ex:
            futurs = {ex.submit(telecharger, adresse, ordre_dl, n, cache): n for n in range(ntuiles)}
            for k, fu in enumerate(cf.as_completed(futurs)):
                n = futurs[fu]
                octets = fu.result()
                if not octets:
                    absentes += 1
                    continue
                img = lire_fits(octets)
                if img.shape != (w, w):
                    raise SystemExit(f'tuile {n} : {img.shape}, attendu {w} × {w}')
                carte[n * w * w + table] = img.astype(np.float32)
                if k % 50 == 0:
                    print(f'  {k + 1}/{ntuiles} tuiles, {time.time() - t0:.0f} s', flush=True)
        if absentes == ntuiles:
            raise SystemExit('toutes les tuiles sont absentes : serveur en panne ? (vider le cache avant de relancer)')
        import warnings
        for _ in range(plus):      # ordre emboîté : les 4 enfants d'un pixel se suivent ; moyenne des seuls enfants mesurés
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)      # pixel sans aucun enfant mesuré : il reste vide (NaN)
                carte = np.nanmean(carte.reshape(-1, 4), axis=1).astype(np.float32)
        if plus:
            absentes = f'{absentes} (à l’ordre {ordre_dl})'
            ntuiles = 12 * 4 ** ordre      # la suite (contrôle des orientations) travaille sur les tuiles de l'ordre gardé
        else:
            controle_ordre(adresse, ordre, w, cache, table)
    mesure = np.isfinite(carte)
    couverture = float(mesure.mean())
    vals = carte[mesure]
    stats = dict(min=float(vals.min()), max=float(vals.max()),
                 p01=float(np.percentile(vals, 1)), p50=float(np.percentile(vals, 50)), p99=float(np.percentile(vals, 99)),
                 p999=float(np.percentile(vals, 99.9)))
    galactique = repere.startswith('gal')
    if w is None:      # carte entière : pas de tuiles à poser, un seul contrôle (le plan doit ressortir)
        contrastes, sauts = [contraste_plan(carte, nside, galactique)], [continuite(carte, nside)]
        print(f'  contraste plan / hautes latitudes : {contrastes[0]:.3g} ; saut moyen entre voisins : {sauts[0]:.4f}')
    else:
        # contrôle d'assemblage : le plan de la Galaxie doit ressortir mieux avec la convention de la norme qu'avec les sept
        # autres orientations des tuiles (réécrites ici à partir de la carte, sans retélécharger).
        contrastes, sauts = [], []
        t0r = tables[0].ravel()
        for o, t in enumerate(tables):
            if o == 0:
                c = carte
            else:
                c = np.empty_like(carte).reshape(ntuiles, w * w)
                c[:, t.ravel()] = carte.reshape(ntuiles, w * w)[:, t0r]
                c = c.ravel()
            contrastes.append(contraste_plan(c, nside, galactique))
            sauts.append(continuite(c, nside))
        print('  contraste plan / hautes latitudes, orientations 0 à 7 : ' + ', '.join(f'{x:.3g}' for x in contrastes))
        print('  saut moyen entre pixels voisins (log), orientations 0 à 7 : ' + ', '.join(f'{x:.4f}' for x in sauts))
        if int(np.argmin(sauts)) != 0:
            print(f'  ATTENTION : la pose {int(np.argmin(sauts))} est plus continue que la pose retenue (0) : tuiles mal posées')

    meta = dict(r, nom=a.nom, repere=repere, nside=nside, ordre_hips=ordre, ordre_hips_max=ordre_max,
                largeur_tuile=w, serveur=adresse, couverture_mesuree=couverture, tuiles_absentes=absentes,
                stats=stats, contraste_plan=contrastes, resolution_carte_arcmin=math.degrees(math.sqrt(4 * math.pi / (12 * nside * nside))) * 60,
                date=time.strftime('%Y-%m-%d'), outil='pipeline/natif/ciel_bandes.py')
    js = json.dumps(meta, ensure_ascii=False).encode('utf-8')
    os.makedirs(a.sortie, exist_ok=True)
    chemin = os.path.join(a.sortie, f'ciel_{a.nom}.bin')
    with open(chemin + '.part', 'wb') as f:
        f.write(b'UNIVSKY1')
        f.write(struct.pack('<IIII', nside, 1 if repere.startswith('gal') else 0, len(js), 0))
        f.write(js)
        f.write(b'\0' * ((-f.tell()) % 16))
        f.write(carte.tobytes())
    os.replace(chemin + '.part', chemin)
    print(f'Écrit {chemin} : Nside {nside}, couverture {couverture * 100:.2f} %, tuiles absentes {absentes}, '
          f'valeurs {stats["p01"]:.4g} à {stats["p999"]:.4g} {r["unite"]} (1 % à 99,9 %), contraste du plan {contrastes[0]:.3g}')


if __name__ == '__main__':
    main()
