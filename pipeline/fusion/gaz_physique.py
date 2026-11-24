#!/usr/bin/env python3
"""Physique du gaz hors hydrodynamique : refroidissement exact et explosions d'étoiles à énergie conservée. [Modèle]

Écrit le 24/11/2026 (fil « Physique du gaz »), pour remplacer à terme le cœur de gaz_galaxie.GazThermique (branche
film-3), écrit le 19/11 et jamais exécuté. Chaque fonction marche avec numpy (contrôles sur le processeur) ou cupy
(calcul sur la carte) : on passe le module en argument `xp`.

1. Composition et température [Probable : abondances solaires d'Asplund et al. 2009, ARA&A 47, 481]
   X = 0,7381 (hydrogène), Y = 0,2485 (hélium), Z = 0,0134 (métaux), en masse. Gaz entièrement ionisé :
   mu = 1 / (2X + 3Y/4 + Z/2) = 0,599 ; n_H = X rho / m_p ; n_e = (X + Y/2) rho / m_p ; ions n_i = (X + Y/4) rho / m_p.

2. Courbe de refroidissement [Modèle publié ; voir la note sur la normalisation]
   Ajustement par morceaux d'une courbe d'équilibre d'ionisation par collisions, composition solaire, calculée avec
   Cloudy, tel qu'il est codé dans Cholla (fonction CIE_cool de src/cooling/cooling_cuda.cu, dépôt cholla-hydro/cholla,
   lu le 24/11/2026 ; décrite dans Schneider & Robertson 2018, ApJ 860, 135, § 2.2.3, sans coefficients) :
     log L = -1,3 (log T - 5,25)² - 21,25   pour 4 <= log T < 5,9
     log L =  0,7 (log T - 7,1)²  - 22,8    pour 5,9 <= log T < 7,4
     log L =  0,45 log T - 26,065           au-delà ; L = 0 sous 10^4 K.
   NORMALISATION (point important, [Probable]) : Cholla multiplie L par n² avec n = rho / (0,6 m_p). Or ces valeurs
   tombent sur celles des tables de référence normalisées par n_e n_i (Sutherland & Dopita 1993, ApJS 88, 253 :
   log L_N ≈ -21,9 à 10^6 K, pic ≈ -21,2 vers 10^5,3 K, de mémoire). Avec n² on refroidirait environ 4 fois trop vite.
   Choix ici : perte par volume = n_e n_i L (convention de Sutherland & Dopita) ; l'autre convention reste disponible
   (`normalisation='cholla'`) pour comparer. [À vérifier contre une table de Sutherland & Dopita ou Gnat & Sternberg 2007]
   Rien sous 10^4 K (ni gaz froid, ni chauffage par la lumière des étoiles) : plancher de température à 10^4 K.

3. Intégration exacte du refroidissement [Certain pour la méthode : Townsend 2009, ApJS 181, 391, éq. 24-26, lue le
   24/11/2026 sur arxiv.org/html/0901.3146]
   À densité fixée pendant le pas, dT/dt = -A L(T) avec A = (gamma - 1) mu m_p n_e n_i / (k_B rho). On tabule
   G(T) = intégrale de 10^4 K à T de dT'/L(T'), exacte car L est pris en loi de puissance entre deux points de la table
   (4 005 points de 10^4 à 10^9,5 K, raccords de l'ajustement compris). Le pas donne G(T_fin) = G(T_début) - A dt, puis on
   inverse G exactement. Aucun sous-pas, aucune troncature, quel que soit dt (l'ancien code s'arrêtait après 24
   sous-pas de 20 % et laissait du gaz chaud qui aurait dû se refroidir).

4. Explosions d'étoiles [Modèle publié]
   - Répartition des masses à la naissance : Chabrier 2003 (PASP 115, 763, étoiles individuelles, éq. 17 : log-normale
     de masse caractéristique 0,079 M☉ et sigma 0,69 sous 1 M☉, puis dN/dlog M ∝ M^-1,3), de 0,1 à 100 M☉. [Probable ;
     elle redonne à 0,006 % le nombre de supernovæ publié par Dalla Vecchia & Schaye 2012 pour Chabrier]
   - Supernovæ à effondrement : étoiles de 8 à 100 M☉ [Supposition courante ; Dalla Vecchia & Schaye 2012 prennent
     6-100 M☉ : 1,736 × 10^-2 par M☉ formée, éq. 1, contrôle de essai_gaz_physique.py], 10^51 erg chacune.
   - Instant de l'explosion = durée de vie de l'étoile, Raiteri, Villata & Navarro 1996 (A&A 315, 105), éq. 4-7 telles
     que reproduites par Poulhazan et al. 2018 (arXiv:1808.00007, § 2.2, lue le 24/11/2026) :
     log t[an] = a0 + a1 log M + a2 (log M)², a0 = 10,13 + 0,07547 log Z - 0,008084 (log Z)²,
     a1 = -4,424 - 0,7939 log Z - 0,1187 (log Z)², a2 = 1,262 + 0,3385 log Z + 0,05417 (log Z)² ; Z de 0,0004 à 0,05.
   - Supernovæ thermonucléaires (Ia) : 1,3 × 10^-3 par M☉ formée en un temps de Hubble, délai ∝ 1/t à partir de 40 Ma
     (Maoz & Mannucci 2012, PASA 29, 447 ; Maoz & Graur 2017, ApJ 848, 25) [Probable], 10^51 erg chacune.
   - Dépôt : chauffage thermique « stochastique » de Dalla Vecchia & Schaye 2012 (MNRAS 426, 140), saut de 10^7,5 K,
     avec la même probabilité moyenne que l'article (énergie du pas / énergie d'un saut), mais tirée sur une RÉSERVE
     par particule d'étoiles (énergie libérée moins énergie déposée) : le registre est exact (libérée = déposée +
     réserve) et l'écart par particule reste sous un saut (voir nombre_de_chauffes). [Choix d'ici, même esprit.]
     À masses égales, une particule d'étoiles ne libère en tout qu'environ un saut (1,3 × 10^49 erg/M☉ contre
     1,3 × 10^49 erg par M☉ chauffé de 10^7,5 K : Dalla Vecchia & Schaye 2012, éq. 8, ⟨N_heat⟩ ≈ 1,3) : sans tirage, la
     chauffe n'arriverait qu'après les Ia, des milliards d'années trop tard ; d'où le tirage.
   Ce qui n'est pas calculé (à dire) : vents des étoiles massives, pression de la lumière, gaz froid sous 10^4 K, champ
   magnétique, rayons cosmiques, noyau actif, métaux (Z fixe, solaire).
"""
import math

import numpy as np

# Constantes (cgs)
M_P = 1.67262192e-24          # g
K_B = 1.380649e-16            # erg/K
M_SOL = 1.98841e33            # g
KPC = 3.0856776e21            # cm
E51 = 1.0e51                  # erg
UNITE_TEMPS_S = KPC / 1.0e5   # s : unité de temps du calcul, kpc / (km/s)
UNITE_TEMPS_AN = UNITE_TEMPS_S / 3.15576e7
RHO_CGS = M_SOL / KPC ** 3    # g/cm³ pour 1 M☉/kpc³

# Composition solaire (Asplund et al. 2009)
X, Y, Z_SOL = 0.7381, 0.2485, 0.0134
GAMMA = 5.0 / 3.0
MU = 1.0 / (2.0 * X + 0.75 * Y + 0.5 * Z_SOL)          # 0,599, entièrement ionisé
NE_PAR_RHO = (X + 0.5 * Y) / M_P                       # électrons par gramme
NI_PAR_RHO = (X + 0.25 * Y) / M_P                      # ions (H et He) par gramme
N_PAR_RHO_CHOLLA = 1.0 / (0.6 * M_P)
K_PAR_U = (GAMMA - 1.0) * MU * M_P * 1.0e10 / K_B      # kelvins par (km/s)² d'énergie interne : 48,3
T_PLANCHER = 1.0e4
DT_CHAUFFE = 10 ** 7.5                                  # kelvins

# ------------------------------------------------------------------------------------------------------------------
# Refroidissement


def lambda_cie(T):
    """Courbe de refroidissement (erg cm³/s) de Cholla, numpy. Nulle sous 10^4 K."""
    lt = np.log10(np.maximum(np.asarray(T, float), 1.0))
    L = np.where(lt < 5.9, -1.3 * (lt - 5.25) ** 2 - 21.25,
                 np.where(lt < 7.4, 0.7 * (lt - 7.1) ** 2 - 22.8, 0.45 * lt - 26.065))
    return np.where(lt < 4.0, 0.0, 10.0 ** L)


class Refroidissement:
    """Intégration exacte (Townsend 2009) du refroidissement à densité fixée. u en (km/s)², rho en M☉/kpc³, dt en
    unités du calcul. `normalisation` : 'ne_ni' (défaut, voir l'en-tête) ou 'cholla' (n² avec mu = 0,6)."""

    def __init__(self, normalisation='ne_ni', n_points=4001, log_t_max=9.5):
        if normalisation not in ('ne_ni', 'cholla'):
            raise ValueError(f'normalisation inconnue : {normalisation}')
        self.normalisation = normalisation
        # les raccords de l'ajustement (10^5,9 et 10^7,4 K, où la courbe saute de ~0,01 dex) sont des points de la table
        lt = np.linspace(math.log10(T_PLANCHER), log_t_max, n_points)
        lt = np.unique(np.concatenate([lt, [5.9 - 1e-9, 5.9, 7.4 - 1e-9, 7.4]]))
        T = 10.0 ** lt
        L = lambda_cie(T)
        a = np.diff(np.log(L)) / np.diff(np.log(T))          # pente de la loi de puissance sur chaque segment
        # intégrale exacte de dT/L sur chaque segment, L = L_k (T / T_k)^a
        T0, T1, L0 = T[:-1], T[1:], L[:-1]
        un = np.abs(a - 1.0) < 1e-9
        seg = np.where(un, T0 / L0 * np.log(T1 / T0),
                       T0 / (L0 * (1.0 - np.where(un, 0.5, a))) * ((T1 / T0) ** (1.0 - np.where(un, 0.5, a)) - 1.0))
        self.T, self.L, self.a = T, L, a
        self.G = np.concatenate([[0.0], np.cumsum(seg)])     # G(T_k), en K / (erg cm³ s⁻¹)
        if normalisation == 'ne_ni':
            self.k_dens = NE_PAR_RHO * NI_PAR_RHO
        else:
            self.k_dens = N_PAR_RHO_CHOLLA ** 2
        self._cache = {}

    def coefficient_A(self, rho):
        """A tel que dT/dt = -A L(T), en (K / s) / (erg cm³ s⁻¹), pour rho en M☉/kpc³."""
        rho_cgs = rho * RHO_CGS
        return (GAMMA - 1.0) * MU * M_P * self.k_dens * rho_cgs / K_B

    def _tables(self, xp):
        if xp not in self._cache:
            self._cache[xp] = tuple(xp.asarray(t) for t in (self.T, self.L, self.a, self.G))
        return self._cache[xp]

    def _G_de(self, T, xp):
        Tt, Lt, at, Gt = self._tables(xp)
        T = xp.clip(T, Tt[0], Tt[-1] * (1 - 1e-12))
        k = xp.clip(xp.searchsorted(Tt, T, side='right') - 1, 0, len(at) - 1)
        T0, L0, a = Tt[k], Lt[k], at[k]
        un = xp.abs(a - 1.0) < 1e-9
        b = xp.where(un, 0.5, 1.0 - a)
        part = xp.where(un, T0 / L0 * xp.log(T / T0), T0 / (L0 * b) * ((T / T0) ** b - 1.0))
        return Gt[k] + part

    def _T_de(self, G, xp):
        Tt, Lt, at, Gt = self._tables(xp)
        G = xp.clip(G, 0.0, Gt[-1])
        k = xp.clip(xp.searchsorted(Gt, G, side='right') - 1, 0, len(at) - 1)
        T0, L0, a = Tt[k], Lt[k], at[k]
        reste = G - Gt[k]
        un = xp.abs(a - 1.0) < 1e-9
        b = xp.where(un, 0.5, 1.0 - a)
        # reste = T0/(L0 b) ((T/T0)^b - 1)  =>  T = T0 (1 + reste L0 b / T0)^(1/b)
        base = xp.maximum(1.0 + reste * L0 * b / T0, 1e-300)
        return xp.where(un, T0 * xp.exp(reste * L0 / T0), T0 * base ** (1.0 / b))

    def refroidir(self, u, rho, dt, xp=np):
        """Énergie interne après dt de refroidissement à densité fixée. Exacte ; jamais sous le plancher de 10^4 K. Le
        gaz au-dessus de 10^9,5 K suit la dernière loi de puissance (freinage)."""
        u = xp.asarray(u, dtype=xp.float64)      # en simple précision, l'inversion de G perd toute précision
        T = u * K_PAR_U
        chaud = T > self.T[-1]
        A = self.coefficient_A(rho)
        dts = dt * UNITE_TEMPS_S
        # au-delà de la table : loi de puissance L ∝ T^0,45 exacte jusqu'à retomber dans la table
        a_h = 0.45; L_h = 10 ** (0.45 * math.log10(self.T[-1]) - 26.065)
        b_h = 1.0 - a_h
        G_haut = xp.where(chaud, self.T[-1] / (L_h * b_h) * ((xp.maximum(T, self.T[-1]) / self.T[-1]) ** b_h - 1.0), 0.0)
        G = xp.where(chaud, self.G[-1] + G_haut, self._G_de(xp.maximum(T, T_PLANCHER), xp)) - A * dts
        T_haut = self.T[-1] * xp.maximum(1.0 + (G - self.G[-1]) * L_h * b_h / self.T[-1], 1e-300) ** (1.0 / b_h)
        T_fin = xp.where(G > self.G[-1], T_haut, self._T_de(G, xp))
        T_fin = xp.where(T <= T_PLANCHER, T, xp.maximum(T_fin, T_PLANCHER))      # sous le plancher : rien ne change
        return T_fin / K_PAR_U

    def temps_de_refroidissement(self, T, rho):
        """t = T / (A L(T)), en unités du calcul (pour les contrôles et l'affichage)."""
        return T / (self.coefficient_A(rho) * lambda_cie(T)) / UNITE_TEMPS_S


# ------------------------------------------------------------------------------------------------------------------
# Étoiles : répartition des masses, durées de vie, nombre de supernovæ

M_BAS, M_HAUT = 0.1, 100.0
M_SN_BAS, M_SN_HAUT = 8.0, 100.0
NIA_PAR_MSOL = 1.3e-3
T_IA_DEBUT = 4.0e7          # ans
T_HUBBLE = 1.37e10          # ans


def chabrier_dn_dm(m):
    """Répartition des masses de Chabrier 2003 (étoiles individuelles, éq. 17), non normalisée : dN/dM."""
    m = np.asarray(m, float)
    bas = 0.158 / (m * math.log(10)) * np.exp(-(np.log10(m) - math.log10(0.079)) ** 2 / (2 * 0.69 ** 2))
    # raccord continu à 1 M☉ : A M^-1,3 en dN/dlog M
    a1 = 0.158 * math.exp(-(0.0 - math.log10(0.079)) ** 2 / (2 * 0.69 ** 2))
    haut = a1 * m ** -1.3 / (m * math.log(10))
    return np.where(m < 1.0, bas, haut)


def _integrale(f, a, b, n=20001):
    x = np.logspace(math.log10(a), math.log10(b), n)
    y = f(x)
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def nombre_sn_par_masse(m_bas=M_SN_BAS, m_haut=M_SN_HAUT):
    """Supernovæ à effondrement par M☉ formée : N(m_bas..m_haut) / M(0,1..100)."""
    masse = _integrale(lambda m: m * chabrier_dn_dm(m), M_BAS, M_HAUT)
    return _integrale(chabrier_dn_dm, m_bas, m_haut) / masse


def duree_de_vie(m, z=Z_SOL):
    """Durée de vie (ans) d'une étoile de masse m (M☉), Raiteri et al. 1996 (Z de 0,0004 à 0,03 ici : au-delà, la
    formule n'est plus décroissante vers 100 M☉)."""
    if not 4e-4 <= z <= 0.03:
        raise ValueError(f'métallicité hors du domaine utilisé : {z}')
    lz = math.log10(z)
    a0 = 10.13 + 0.07547 * lz - 0.008084 * lz ** 2
    a1 = -4.424 - 0.7939 * lz - 0.1187 * lz ** 2
    a2 = 1.262 + 0.3385 * lz + 0.05417 * lz ** 2
    lm = np.log10(np.asarray(m, float))
    return 10.0 ** (a0 + a1 * lm + a2 * lm ** 2)


class Explosions:
    """Énergie libérée par les supernovæ d'une population née d'un coup, en fonction de son âge.
    Table cumulée E(âge) en erg par M☉ formée ; e(a, b) = E(b) - E(a)."""

    def __init__(self, z=Z_SOL, avec_ia=True):
        self.z = z
        masses = np.logspace(math.log10(M_SN_BAS), math.log10(M_SN_HAUT), 2001)
        ages = duree_de_vie(masses, z)
        if not np.all(np.diff(ages) < 0):
            raise ValueError('durées de vie non décroissantes avec la masse')
        masse_formee = _integrale(lambda m: m * chabrier_dn_dm(m), M_BAS, M_HAUT)
        # nombre cumulé de supernovæ à l'âge t = étoiles de masse > m(t)
        n_au_dessus = np.array([_integrale(chabrier_dn_dm, m, M_SN_HAUT, 2001) if m < M_SN_HAUT else 0.0 for m in masses])
        self.age_sn_debut, self.age_sn_fin = float(ages[-1]), float(ages[0])
        self._la = np.log(ages[::-1])                        # âges croissants
        self._nii = (n_au_dessus / masse_formee)[::-1]
        self.n_sn_ii = float(self._nii[-1])
        self.avec_ia = avec_ia

    def n_ii_cumule(self, age, xp=np):
        age = xp.asarray(age, dtype=xp.float64)
        la, nii = (self._la, self._nii) if xp is np else (xp.asarray(self._la), xp.asarray(self._nii))
        x = xp.log(xp.maximum(age, 1.0))
        out = xp.interp(x, la, nii)
        return xp.where(x < self._la[0], 0.0, xp.where(x > self._la[-1], self.n_sn_ii, out))

    def n_ia_cumule(self, age, xp=np):
        age = xp.asarray(age, dtype=xp.float64)
        if not self.avec_ia:
            return xp.zeros_like(age)
        return NIA_PAR_MSOL * xp.clip(xp.log(xp.maximum(age, T_IA_DEBUT) / T_IA_DEBUT) / math.log(T_HUBBLE / T_IA_DEBUT), 0.0, 1.0)

    def energie_cumulee(self, age, xp=np):
        """erg par M☉ formée, libérés entre la naissance et `age` (ans). numpy ou cupy (xp)."""
        return E51 * (self.n_ii_cumule(age, xp) + self.n_ia_cumule(age, xp))

    def energie_liberee(self, age, dt_ans, xp=np):
        """erg par M☉ formée, libérés entre age et age + dt_ans."""
        age = xp.asarray(age, dtype=xp.float64)
        return self.energie_cumulee(age + dt_ans, xp) - self.energie_cumulee(age, xp)


def energie_quantum(m_gaz):
    """Énergie (erg) pour chauffer une particule de gaz de masse m_gaz (M☉) de 10^7,5 K."""
    return m_gaz * M_SOL * K_B * DT_CHAUFFE / ((GAMMA - 1.0) * MU * M_P)


def nombre_de_chauffes(reserve, quantum, rng, xp=np):
    """Combien de voisines chauffer ce pas, pour chaque particule d'étoiles.

    Dalla Vecchia & Schaye 2012 (éq. 5) chauffent au hasard avec la probabilité (énergie du pas) / (énergie d'un saut) :
    les chauffes arrivent en moyenne au moment des explosions, mais l'énergie n'est conservée qu'en moyenne. Ici, la
    même probabilité est tirée sur la RÉSERVE (énergie libérée moins énergie déjà déposée, par particule) :
    n = partie entière de reserve / quantum, plus 1 avec la probabilité de la partie fractionnaire. En moyenne c'est la
    même règle ; en plus, la réserve garde la trace exacte de ce qui a été donné en avance (elle devient négative) ou en
    retard, et le tirage suivant compense. Écart entre énergie libérée et déposée : moins d'un saut par particule, à
    tout instant, et le registre (libérée = déposée + réserve) est exact."""
    x = xp.maximum(reserve, 0.0) / quantum
    n = xp.floor(x)
    return (n + (rng.random(x.shape) < (x - n))).astype(xp.int64)


def deposer(reserve, n_chauffes, voisines, m_gaz, u_gaz, rng):
    """Chauffe de 10^7,5 K, pour chaque particule d'étoiles s, n_chauffes[s] voisines de gaz différentes, tirées au hasard
    parmi ses candidates (comme Dalla Vecchia & Schaye 2012), et retire de sa réserve l'énergie exacte donnée.

    reserve (n_etoiles,) en erg, modifiée sur place ; voisines (n_etoiles, k) indices de gaz candidats (les plus proches,
    -1 si absent) ; m_gaz, u_gaz : masses (M☉) et énergies internes ((km/s)²) des particules de gaz, u_gaz modifiée sur
    place. Une voisine n'est chauffée qu'une fois par appel. Rend (nombre de chauffes, énergie déposée en erg).
    Version numpy : seules les quelques particules qui chauffent ce pas y passent."""
    du = DT_CHAUFFE / K_PAR_U
    chauffes, depose = 0, 0.0
    prises = set()
    for s in np.nonzero(n_chauffes > 0)[0]:
        cand = [j for j in dict.fromkeys(int(j) for j in voisines[s] if j >= 0) if j not in prises]
        rng.shuffle(cand)
        for j in cand[:int(n_chauffes[s])]:
            e = energie_quantum(m_gaz[j])
            reserve[s] -= e; u_gaz[j] += du; prises.add(j)
            chauffes += 1; depose += e
    return chauffes, depose
