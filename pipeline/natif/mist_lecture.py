"""Lecture de mist_traces.bin (mist_gaia.py) et calcul d'une étoile à un âge donné. Même calcul que natif/src/vie_etoiles.h."""
import numpy as np

CHAMPS = ('age', 'G', 'C', 'V', 'BV', 'logL', 'logT', 'calme_lo', 'calme_hi')


class Traces:
    def __init__(self, chemin: str):
        b = np.fromfile(chemin, np.uint8)
        if bytes(b[:8]) != b'UNIVMST1':
            raise ValueError('mist_traces.bin : en-tête inconnu')
        self.n, self.n_eep = (int(x) for x in b[8:16].view('<u4'))
        o = 16
        self.masses = b[o:o + 4 * self.n].view('<f4').astype(np.float64); o += 4 * self.n
        self.utiles = b[o:o + 4 * self.n].view('<u4').astype(np.int64); o += 4 * self.n
        self.fins = b[o:o + self.n].copy(); o += self.n
        o += -o % 16
        n8, n4 = 3 * 8 * self.n_eep, 6 * 4 * self.n_eep
        bloc = n8 + n4 + self.n_eep
        corps = b[o:o + bloc * self.n].reshape(self.n, bloc)
        doubles = corps[:, :n8].copy().view('<f8').reshape(self.n, 3, self.n_eep)
        simples = corps[:, n8:n8 + n4].copy().view('<f4').reshape(self.n, 6, self.n_eep).astype(np.float64)
        # même ordre que CHAMPS : âge, G, C, V, BV, logL, logT, calme_lo, calme_hi
        self.t = np.concatenate([doubles[:, :1], simples, doubles[:, 1:]], 1)
        self.phase = corps[:, n8 + n4:].copy()
        self.lmin, self.lpas = np.log(self.masses[0]), np.log(self.masses[1] / self.masses[0])

    def champ(self, nom: str) -> np.ndarray:
        return self.t[:, CHAMPS.index(nom), :]

    def trace(self, masse: np.ndarray) -> np.ndarray:
        """Indice de la trace la plus proche en masse (pas de 0,4 %)."""
        return np.clip(np.rint((np.log(masse) - self.lmin) / self.lpas), 0, self.n - 1).astype(np.int64)

    def eep_a_age(self, tr: np.ndarray, age: np.ndarray) -> np.ndarray:
        """Point d'évolution (fractionnaire, base 0) à l'âge donné ; NaN avant la naissance ; > fin -> utiles - 1 + fraction."""
        ages = self.champ('age')
        out = np.empty(len(tr))
        for k in np.unique(tr):
            s = tr == k
            a = ages[k, :self.utiles[k]].astype(np.float64)
            x = age[s]
            j = np.clip(np.searchsorted(a, x, side='right') - 1, 0, len(a) - 2)
            f = (x - a[j]) / np.maximum(a[j + 1] - a[j], 1e-30)
            e = j + np.clip(f, 0, None)
            e = np.where(x < a[0], np.nan, np.where(x > a[-1], len(a) - 1 + (x - a[-1]) / max(a[-1], 1.0), e))
            out[s] = e
        return out

    def valeur(self, nom: str, tr: np.ndarray, eep: np.ndarray) -> np.ndarray:
        v = self.champ(nom)
        n = self.utiles[tr]
        e = np.clip(eep, 0, n - 1)
        j = np.minimum(np.floor(e).astype(np.int64), n - 2)
        f = e - j
        return (1 - f) * v[tr, j] + f * v[tr, j + 1]
