#!/usr/bin/env python3
"""Film du Groupe local, format 3 (docs/format-film-v3.md) : écrivain (pour rencontre.py, mode « futur ») et lecteur.

Familles de traceurs, chacune dans un ordre fixe : P (principaux : étoiles visibles, matière du calcul, Soleil ; une
image tous les 20 Ma) ; trois classes de cadence ENTRE deux images P, disjointes, choisies parmi P par fréquence de tour
décroissante : C (tous les 2 Ma), M (tous les 4 Ma), L (tous les 10 Ma) ; G (Gaia, tous les 10 Ma jusqu'à +1 Ga).
Mesuré le 22/11/2026 : avec une image tous les 20 Ma seulement, l'interpolation se trompe de 0,7 à 1,2 kpc sous 1 kpc
du centre, de 0,5 kpc entre 1 et 2 kpc, de 90 à 330 pc entre 2 et 3,5 kpc ; d'où les classes.
Un enregistrement = 18 octets, petit-boutiste : position x, y, z en entiers 32 bits signés (unité 0,01 pc), vitesse
x, y, z en entiers 16 bits signés (unité 0,05 km/s, saturée), RELATIVES au centre et à la vitesse d'ensemble de la
galaxie d'origine du traceur à la date de l'image. Entre deux images : Hermite cubique en (x, y, z) (fonction hermite ;
en rayon et angle c'est pire dans le bulbe, mesuré) ; le centre de la galaxie s'interpole de la même façon, avec la
vitesse de centre de l'index, sinon son bruit (10 à 50 pc) passe dans toutes les étoiles.

Fichiers du dossier du film :
  film.json          lisible : version, unités, blocs, cadences, classes (effectif, rayon couvert par galaxie), décalages
  film_index.bin     index binaire (disposition ci-dessous)
  p_NNNNN.bin, c_NNNNN.bin, m_NNNNN.bin, l_NNNNN.bin, g_NNNNN.bin   enregistrements, sans en-tête ; NNNNN = rang de la
                     date dans l'index (une date tous les 2 Ma). À une date P, seul p_ existe (il contient tout le monde).
  centraux.bin, moyens.bin, lents.bin   rang dans P de chaque traceur des classes C, M, L (entiers 32 bits non signés)
  matiere.bin        une ligne de 8 octets par particule du bloc « matière du calcul » : nature à t = 0 (octet : 0 gaz,
                     1 étoile), sorte du calcul (octet), galaxie (entier 16 bits), masse en M☉ (flottant 32 bits)
  evenements.bin     lignes de 16 octets, triées par date : rang dans le bloc matière (entier 32 bits), nouvelle nature
                     (octet : 0 gaz, 1 étoile), 3 octets nuls, date en Ga (flottant 64 bits)

film_index.bin :
  en-tête, 80 octets : « UNIVFLM3 » (8), version (u32 = 3), galaxies (u32), blocs (u32), dates (u32), traceurs P (u64),
                       C (u64), G (u64), M (u64), L (u64), pas de base en Ma (f64), taille d'un enregistrement (u32 = 18),
                       réserve (u32)
  blocs, 32 octets chacun : famille (u8 : 0 P, 1 C, 2 G, 3 M, 4 L), type (u8 : 0 mélange, voir le fichier de rangs ;
                       1 étoiles visibles, 2 matière du calcul, 3 Soleil, 4 naine, 5 Gaia), galaxie d'origine (u16,
                       65535 = aucune), réserve (u32), premier rang (u64), nombre (u64), réserve (u64)
  décalage à t = 0 : par galaxie, 6 f64 (place calculée moins place mesurée en kpc, puis vitesse en km/s) ;
                       puis 6 f64 pour le Soleil (place et vitesse du film moins mesurées)
  Gaia, 16 octets : taille du gaia.bin utilisé (u64), CRC32 (u32), réserve (u32) ; zéros si pas de famille G
  dates : par date, t en Ga (f64), familles présentes (u32 : bit 0 P, 1 C, 2 G, 3 M, 4 L), réserve (u32), puis par
                       galaxie centre (3 f64, kpc) et vitesse (3 f64, km/s) relatifs à la Voie lactée, puis écart
                       d'énergie (f64)
"""
import json
import os
import struct

import numpy as np

MAGIE = b'UNIVFLM3'
UNITE_POS_KPC = 1e-5          # 0,01 pc
UNITE_VIT_KMS = 0.05
FAM_P, FAM_C, FAM_G, FAM_M, FAM_L = 0, 1, 2, 3, 4
# Classes de cadence entre deux images P : (famille, lettre du fichier, fichier des rangs dans P, une date sur combien)
CLASSES = ((FAM_C, 'c', 'centraux.bin', 1), (FAM_M, 'm', 'moyens.bin', 2), (FAM_L, 'l', 'lents.bin', 5))
TYPE_VISIBLES, TYPE_MATIERE, TYPE_SOLEIL, TYPE_NAINE, TYPE_GAIA = 1, 2, 3, 4, 5
DT_ENREG = np.dtype([('p', '<i4', 3), ('v', '<i2', 3)])
assert DT_ENREG.itemsize == 18
DT_MATIERE = np.dtype([('nature', 'u1'), ('sorte', 'u1'), ('galaxie', '<u2'), ('masse', '<f4')])
DT_EVENEMENT = np.dtype([('rang', '<u4'), ('nature', 'u1'), ('vide', 'u1', 3), ('date', '<f8')])
SORTE_GAZ = 3


def coder(pos_kpc, vel_kms):
    """Positions (kpc) et vitesses (km/s) relatives -> enregistrements de 18 octets."""
    e = np.empty(len(pos_kpc), DT_ENREG)
    e['p'] = np.clip(np.rint(pos_kpc / UNITE_POS_KPC), -2 ** 31 + 1, 2 ** 31 - 1).astype('<i4')
    e['v'] = np.clip(np.rint(vel_kms / UNITE_VIT_KMS), -32767, 32767).astype('<i2')
    return e


def ecrire_fichier(chemin, tableau):
    tableau.tofile(chemin + '.tmp'); os.replace(chemin + '.tmp', chemin)


class Ecrivain:
    """Écrit le film au fil du calcul. `rangs` : pour chaque famille, les rangs de ses traceurs dans les tableaux du
    calcul, dans l'ordre du film ; `origine` : galaxie d'origine de chaque traceur ; `blocs` : liste de
    dict(famille, type, galaxie, premier, nombre). Reprise : relit film.json et ne garde que les dates <= t0."""

    def __init__(self, dossier, galaxies, rangs, origine, blocs, pas_base_ma=2.0, pas_p_ma=20.0, pas_g_ma=10.0, fin_g_ga=1.0,
                 infos=None, t0=0.0):
        self.dossier, self.galaxies = dossier, list(galaxies)
        self.rangs, self.origine, self.blocs = rangs, origine, blocs
        self.pas_base_ma, self.pas_p_ma, self.pas_g_ma, self.fin_g_ga = pas_base_ma, pas_p_ma, pas_g_ma, fin_g_ga
        self.chaque_p = int(round(pas_p_ma / pas_base_ma)); self.chaque_g = int(round(pas_g_ma / pas_base_ma))
        os.makedirs(dossier, exist_ok=True)
        f_json = os.path.join(dossier, 'film.json')
        if t0 > 1e-9 and os.path.exists(f_json):      # reprise après un arrêt : les dates d'après la sauvegarde sont refaites
            self.meta = json.load(open(f_json, encoding='utf-8'))
            self.meta['dates'] = [d for d in self.meta['dates'] if d['t'] <= t0 + 1e-9]
            f_ev = os.path.join(dossier, 'evenements.bin')
            if os.path.exists(f_ev):
                ev = np.fromfile(f_ev, DT_EVENEMENT); ecrire_fichier(f_ev, ev[ev['date'] <= t0 + 1e-9])
        else:
            self.meta = dict(version=3, galaxies=self.galaxies, pas_base_ma=pas_base_ma, pas_p_ma=pas_p_ma, pas_g_ma=pas_g_ma, fin_g_ga=fin_g_ga,
                             unites="positions : entiers 32 bits, 0,01 pc ; vitesses : entiers 16 bits, 0,05 km/s ; relatives au centre et à la "
                                    "vitesse d'ensemble de la galaxie d'origine ; centres en kpc et km/s relatifs à la Voie lactée ; dates en Ga",
                             traceurs={'P': int(len(rangs[FAM_P])), 'C': int(len(rangs[FAM_C])), 'G': int(len(rangs[FAM_G])),
                                       'M': int(len(rangs[FAM_M])), 'L': int(len(rangs[FAM_L]))},
                             blocs=blocs, dates=[], **(infos or {}))
            open(os.path.join(dossier, 'evenements.bin'), 'wb').close()
        self.nature = None      # nature (gaz ou étoile) des particules de matière à la dernière date écrite

    def numero(self):
        return len(self.meta['dates'])

    def date(self, t, pos, vel, centres, vitesses, energie, sortes_matiere=None):
        """Écrit la date suivante. pos, vel : fonctions rangs -> tableaux numpy (kpc, km/s) du calcul ; centres, vitesses :
        (galaxies, 3), repère du calcul ; sortes_matiere : sorte de chaque particule du bloc matière à cette date."""
        k = self.numero(); familles = 0
        ecrit_p = k % self.chaque_p == 0
        a_ecrire = [(FAM_P, 'p')] if ecrit_p else [(fam, lettre) for fam, lettre, _, chaque in CLASSES if len(self.rangs[fam]) and k % chaque == 0]
        if len(self.rangs[FAM_G]) and k % self.chaque_g == 0 and t <= self.fin_g_ga + 1e-9: a_ecrire.append((FAM_G, 'g'))
        for fam, lettre in a_ecrire:
            r = self.rangs[fam]; o = self.origine[fam]
            e = coder(pos(r) - centres[o], vel(r) - vitesses[o])
            ecrire_fichier(os.path.join(self.dossier, f'{lettre}_{k:05d}.bin'), e)
            familles |= 1 << fam
        if sortes_matiere is not None:      # naissances (gaz -> étoile) et retours au gaz (étoile -> gaz) depuis la date d'avant
            nature = (np.asarray(sortes_matiere) != SORTE_GAZ).astype(np.uint8)
            if self.nature is not None:
                change = np.where(nature != self.nature)[0]
                if len(change):
                    ev = np.zeros(len(change), DT_EVENEMENT); ev['rang'] = change; ev['nature'] = nature[change]; ev['date'] = t
                    with open(os.path.join(self.dossier, 'evenements.bin'), 'ab') as f: ev.tofile(f)
            self.nature = nature
        self.meta['dates'].append(dict(t=round(float(t), 6), familles=familles,
                                       centres=(np.asarray(centres) - np.asarray(centres)[0]).round(5).tolist(),
                                       vitesses=(np.asarray(vitesses) - np.asarray(vitesses)[0]).round(4).tolist(), energie=float(energie)))
        if ecrit_p or k % 25 == 0: self.sauver()

    def sauver(self):
        f = os.path.join(self.dossier, 'film.json')
        json.dump(self.meta, open(f + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False); os.replace(f + '.tmp', f)
        ecrire_index(self.dossier, self.meta)


def ecrire_index(dossier, meta):
    ng = len(meta['galaxies']); blocs = meta['blocs']; dates = meta['dates']
    b = bytearray()
    b += struct.pack('<8sIIIIQQQQQdII', MAGIE, 3, ng, len(blocs), len(dates), meta['traceurs']['P'], meta['traceurs']['C'], meta['traceurs']['G'],
                     meta['traceurs']['M'], meta['traceurs']['L'], float(meta['pas_base_ma']), DT_ENREG.itemsize, 0)
    for x in blocs:
        b += struct.pack('<BBHIQQQ', x['famille'], x['type'], x['galaxie'] if x['galaxie'] is not None else 0xFFFF, 0, x['premier'], x['nombre'], 0)
    dec = meta.get('decalage_a_t0', {})
    for nom in meta['galaxies']:
        d = dec.get(nom, {}); b += struct.pack('<6d', *(list(d.get('position', [0, 0, 0])) + list(d.get('vitesse', [0, 0, 0]))))
    s = meta.get('soleil', {}); b += struct.pack('<6d', *(list(s.get('ecart_position', [0, 0, 0])) + list(s.get('ecart_vitesse', [0, 0, 0]))))
    ga = meta.get('gaia', {}); b += struct.pack('<QII', int(ga.get('taille', 0)), int(ga.get('crc32', 0)), 0)
    for d in dates:
        b += struct.pack('<dII', d['t'], d['familles'], 0)
        for g in range(ng): b += struct.pack('<6d', *(list(d['centres'][g]) + list(d['vitesses'][g])))
        b += struct.pack('<d', d['energie'])
    f = os.path.join(dossier, 'film_index.bin')
    with open(f + '.tmp', 'wb') as h: h.write(bytes(b))
    os.replace(f + '.tmp', f)


class Film:
    """Lecteur (contrôles et mesures). Positions en kpc, vitesses en km/s, relatives à la galaxie d'origine."""

    def __init__(self, dossier):
        self.dossier = dossier
        self.meta = json.load(open(os.path.join(dossier, 'film.json'), encoding='utf-8'))
        self.dates = self.meta['dates']; self.t = np.array([d['t'] for d in self.dates])
        self.blocs = self.meta['blocs']
        lire = lambda nom: np.fromfile(os.path.join(dossier, nom), '<u4') if os.path.exists(os.path.join(dossier, nom)) else np.zeros(0, '<u4')
        self.centraux, self.moyens, self.lents = lire('centraux.bin'), lire('moyens.bin'), lire('lents.bin')

    def image(self, k, famille='p'):
        e = np.memmap(os.path.join(self.dossier, f'{famille}_{k:05d}.bin'), DT_ENREG, mode='r')
        return e['p'].astype(np.float64) * UNITE_POS_KPC, e['v'].astype(np.float64) * UNITE_VIT_KMS

    def dates_de(self, famille):
        bit = {'p': 1, 'c': 2, 'g': 4, 'm': 8, 'l': 16}[famille]
        return [k for k, d in enumerate(self.dates) if d['familles'] & bit]

    def bloc(self, famille, type_, galaxie=None):
        for x in self.blocs:
            if x['famille'] == famille and x['type'] == type_ and (galaxie is None or x['galaxie'] == galaxie): return slice(x['premier'], x['premier'] + x['nombre'])
        return slice(0, 0)


def hermite(p0, v0, p1, v1, h_ga, u):
    """Position à la fraction u (0..1) entre deux images séparées de h_ga ; vitesses en km/s (1 km/s = 1,0227 kpc/Ga)."""
    k = 1.0227121650456 * h_ga
    return (2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * k * v0 + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * k * v1


def ajouter_traceurs(p, positions, vitesses):
    """Ajoute des traceurs sans masse (sorte 9) de la Voie lactée à la fin des particules du calcul (étoiles Gaia, puis
    le Soleil en tout dernier). positions (n, 3) en kpc, vitesses (n, 3) en km/s, repère du calcul."""
    positions = np.atleast_2d(np.asarray(positions, float)); n = len(positions)
    plus = dict(pos=positions, vel=np.atleast_2d(np.asarray(vitesses, float)), m=np.full(n, 1e-6), eps=np.full(n, 0.05), kind=np.full(n, 9, np.int8),
                gid=np.zeros(n, np.int8), h_gaz=np.full(n, 0.2, np.float32), naissance=np.full(n, np.nan), age0=np.full(n, np.nan, np.float32), u_gaz=np.zeros(n, np.float32))
    return {k: np.concatenate([v, np.asarray(plus[k], dtype=v.dtype)]) for k, v in p.items()}


def preparer(dossier, S, p, galaxies, t0, infos, n_centraux, G, n_gaia=0, n_naines=0):
    """Range les traceurs du film dans leur ordre fixe et choisit les centraux. Rend (écrivain, rangs sur la carte).
    Ordre de P : étoiles visibles galaxie par galaxie, puis matière du calcul (étoiles et gaz) galaxie par galaxie, puis
    les galaxies naines (un point chacune, rapportées à la Voie lactée), puis le Soleil. Centraux : les traceurs P de plus grande fréquence de tour, sqrt(G M(<r) / r³), autour de leur galaxie."""
    cp = S.cp
    kind, gid = p['kind'], p['gid']
    idx9 = np.where(kind == 9)[0]; soleil = idx9[-1:]      # ordre des traceurs dans le calcul : étoiles visibles, Gaia, naines, Soleil
    n9 = len(idx9); naines = idx9[n9 - 1 - n_naines:n9 - 1]; gaia = idx9[n9 - 1 - n_naines - n_gaia:n9 - 1 - n_naines]; vis = idx9[:n9 - 1 - n_naines - n_gaia]
    blocs, r_p, matiere, premier = [], [], [], 0

    def bloc(type_, g, r):
        nonlocal premier
        if not len(r): return
        blocs.append(dict(famille=FAM_P, type=type_, galaxie=g, premier=premier, nombre=int(len(r)))); r_p.append(r); premier += len(r)

    for g in range(len(galaxies)): bloc(TYPE_VISIBLES, g, vis[gid[vis] == g])
    for g in range(len(galaxies)):
        r = np.where((kind != 0) & (kind != 9) & (gid == g))[0]; bloc(TYPE_MATIERE, g, r); matiere.append(r)
    bloc(TYPE_NAINE, 0, naines)
    bloc(TYPE_SOLEIL, 0, soleil)
    P = np.concatenate(r_p); matiere = np.concatenate(matiere); origine = gid[P].astype(int)
    chemins = [os.path.join(dossier, nom) for _, _, nom, _ in CLASSES]
    nombres = list(n_centraux) + [0] * (len(CLASSES) - len(n_centraux))
    if t0 > 1e-9 and os.path.exists(chemins[0]):
        classes = [np.fromfile(f, '<u4').astype(np.int64) if os.path.exists(f) else np.zeros(0, np.int64) for f in chemins]
    else:
        centres, _ = S.centres(); pos = cp.asnumpy(S.pos); omega = np.zeros(len(P)); rayon = np.zeros(len(P))
        for g in range(len(galaxies)):
            lourd = np.where((gid == g) & (kind != 9))[0]
            d = np.linalg.norm(pos[lourd] - centres[g], axis=1); o = np.argsort(d); ds = d[o]; cumul = np.cumsum(p['m'][lourd][o])
            t = np.where(origine == g)[0]
            r = np.maximum(np.linalg.norm(pos[P[t]] - centres[g], axis=1), 0.05)
            omega[t] = np.sqrt(G * cumul[np.clip(np.searchsorted(ds, r) - 1, 0, len(cumul) - 1)] / r ** 3); rayon[t] = r
        ordre = np.argsort(-omega); classes, debut = [], 0
        for n in nombres:      # les plus rapides d'abord : 2 Ma, puis 4 Ma, puis 10 Ma
            n = max(0, min(int(n), len(P) // 2 - debut)); classes.append(np.sort(ordre[debut:debut + n])); debut += n
        os.makedirs(dossier, exist_ok=True)
        infos = dict(infos or {}); infos['classes'] = {}
        for (fam, lettre, nom, chaque), f, cl in zip(CLASSES, chemins, classes):
            ecrire_fichier(f, cl.astype('<u4'))
            infos['classes'][lettre] = dict(fichier=nom, cadence_ma=2.0 * chaque, nombre=int(len(cl)),
                                            tours_par_ga_au_bord=round(float(omega[cl].min() * 1.0227121650456 / (2 * np.pi)), 2) if len(cl) else 0.0,
                                            rayon_kpc={nom_g: round(float(rayon[cl][origine[cl] == g].max()), 3) for g, nom_g in enumerate(galaxies) if (origine[cl] == g).any()})
        m = np.zeros(len(matiere), DT_MATIERE); m['nature'] = kind[matiere] != SORTE_GAZ; m['sorte'] = kind[matiere]; m['galaxie'] = gid[matiere]; m['masse'] = p['m'][matiere]
        ecrire_fichier(os.path.join(dossier, 'matiere.bin'), m)
    blocs = blocs + [dict(famille=fam, type=0, galaxie=None, premier=0, nombre=int(len(cl))) for (fam, _, _, _), cl in zip(CLASSES, classes) if len(cl)]
    if len(gaia): blocs = blocs + [dict(famille=FAM_G, type=TYPE_GAIA, galaxie=0, premier=0, nombre=int(len(gaia)))]
    rangs = {FAM_P: cp.asarray(P), FAM_G: cp.asarray(gaia)}; orig = {FAM_P: origine, FAM_G: np.zeros(len(gaia), int)}
    for (fam, _, _, _), cl in zip(CLASSES, classes): rangs[fam] = cp.asarray(P[cl]); orig[fam] = origine[cl]
    ecr = Ecrivain(dossier, galaxies, rangs, orig, blocs, infos=infos, t0=t0)
    ecr.nature = (cp.asnumpy(S.kind_g[cp.asarray(matiere)]) != SORTE_GAZ).astype(np.uint8)
    return ecr, cp.asarray(matiere)
