// Appli PC « Univers » : le cycle de vie d'une étoile (demande de Marc, 20/11/2026 : « je n'ai jamais vu le cycle de vie
// d'une étoile, ni le Soleil devenir une géante rouge »). Calcul sur le processeur, sans dépendance au reste de l'appli
// (contrôlé par essai_cycle). Le dessin est dans cycle_nebuleuse.h, la matière éjectée dans cycle_matiere.h.
//
// Modèles PUBLIÉS, signalés comme modèles à l'écran (fichier vie_cycle.bin, pipeline/natif/vie_cycle.py) :
//   - vie de l'étoile : trajectoires MIST v1.2 (Choi et al. 2016 ; Dotter 2016), [Fe/H] = 0, sans rotation ; entre deux
//     masses de la grille, interpolation point d'évolution par point d'évolution (EEP), comme MIST le fait lui-même ;
//   - naine blanche : refroidissement des modèles de Montréal (Bédard et al. 2020), raccordé à la fin de la trace MIST ;
//   - reste d'une supernova : recette « rapide » de Fryer et al. 2012 (ApJ 749, 91) d'après la masse finale et le cœur
//     de carbone-oxygène ; courbe de lumière moyenne d'une supernova de type II (Anderson et al. 2014, ApJ 786, 67) ;
//   - naissance : cœur dense de 0,1 pc (Bergin & Tafalla 2007) qui donne un tiers de sa masse à l'étoile (Alves, Lombardi
//     & Lada 2007) ; phase enfouie de 0,5 Ma (classes 0 et I, Evans et al. 2009). Ces trois valeurs sont des ordres de
//     grandeur publiés, pas des mesures de chaque étoile : [Probable] pour la littérature, [Supposition] pour leur usage ici.
//
// Masse conservée : à toute date, masse initiale du cœur = étoile (ou reste) + matière éjectée (vents, nébuleuse, restes
// de supernova) + gaz du nuage de naissance pas encore dispersé. Seule exception, dite à l'écran : l'énergie emportée par
// les neutrinos quand un cœur s'effondre (masse de l'étoile à neutrons ou du trou noir comptée en masse gravitationnelle).
// Aucune bascule de forme : rayon, température et éclat varient continûment ; l'explosion part du rayon de l'étoile.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "rayon_etoile.h"

namespace cycle {

// ---------------------------------------------------------------- constantes
constexpr double kAgeSoleilAns = 4.5682e9;    // Bouvier & Wadhwa 2010 (Nature Geoscience 3, 637) [Probable]
constexpr double kAccretionAns = 0.5e6;       // phase enfouie (classes 0 et I), Evans et al. 2009 [Probable]
constexpr double kCondensationAns = 1.0e6;    // le cœur se resserre de 0,3 à 0,1 pc avant de s'effondrer [Supposition]
constexpr double kEfficacite = 1.0 / 3.0;     // part du cœur qui finit dans l'étoile, Alves et al. 2007 [Probable]
constexpr double kCoeurAl = 0.326156;         // 0,1 pc en années-lumière (taille d'un cœur dense, Bergin & Tafalla 2007)
constexpr double kDispersionKms = 1.0;        // gaz restant chassé par les jets de la jeune étoile [Supposition]
constexpr double kSuperAgbAns = 1.0e5;        // fin d'un super-AGB, enveloppe éjectée (MIST s'arrête avant) [Supposition]
constexpr double kContractionAns = 1.0e4;     // passage post-AGB vers la naine blanche à éclat constant [Probable]
constexpr double kRnsKm = 12.5;               // rayon d'une étoile à neutrons, NICER (Riley 2019, Miller 2019) [Probable]
constexpr double kTnsK = 1.0e6;               // température de surface d'une jeune étoile à neutrons [Probable]
constexpr double kMsunG = 1.98847e33, kRsunKm = 695700.0, kLsunErgS = 3.828e33;
constexpr double kGcgs = 6.674e-8, kCcgs = 2.99792458e10;
constexpr double kAnSec = 3.15576e7, kAlCm = 9.4607e17;
// Supernova de type II moyenne (Anderson et al. 2014) : plateau à M_V = -16,7 pendant 100 jours, chute de 2 magnitudes
// en 20 jours, puis déclin radioactif de 0,0098 magnitude par jour [Probable : valeurs moyennes, chaque supernova diffère].
constexpr double kSnPlateau = -16.7, kSnPlateauJours = 100.0, kSnChuteJours = 20.0, kSnChuteMag = 2.0, kSnDeclin = 0.0098;
constexpr double kSnTeff = 6000.0;            // photosphère du plateau : recombinaison de l'hydrogène [Probable]
constexpr double kSnEnergieErg = 1.0e51;      // énergie cinétique usuelle d'une supernova [Probable]

enum class Etape : uint8_t {
    Rien, Nuage, Enfouie, Contraction, Sequence, Geante, Helium, AGB, PostAGB, Nebuleuse, NaineBlanche,
    Supernova, EtoileNeutrons, TrouNoir, WolfRayet, AuDela
};

inline const char* nomEtape(Etape e, bool massive) {
    switch (e) {
        case Etape::Rien: return "pas encore là";
        case Etape::Nuage: return "cœur de nuage qui se resserre";
        case Etape::Enfouie: return "étoile qui naît, enfouie dans son nuage";
        case Etape::Contraction: return "jeune étoile qui se contracte";
        case Etape::Sequence: return "séquence principale (elle brûle son hydrogène)";
        case Etape::Geante: return massive ? "supergéante (hydrogène autour du cœur)" : "géante rouge (hydrogène autour du cœur)";
        case Etape::Helium: return "elle brûle son hélium";
        case Etape::AGB: return massive ? "supergéante rouge" : "géante rouge de la branche asymptotique";
        case Etape::PostAGB: return "son cœur se dénude et chauffe (post-AGB)";
        case Etape::Nebuleuse: return "nébuleuse planétaire : le cœur nu illumine l'enveloppe rejetée";
        case Etape::NaineBlanche: return "naine blanche";
        case Etape::Supernova: return "supernova";
        case Etape::EtoileNeutrons: return "étoile à neutrons";
        case Etape::TrouNoir: return "trou noir";
        case Etape::WolfRayet: return "étoile de Wolf-Rayet (elle a perdu son enveloppe)";
        case Etape::AuDela: return "au-delà du modèle";
    }
    return "";
}

// ---------------------------------------------------------------- couleur et éclat
// Correction bolométrique : Flower (1996) corrigé par Torres (2010) entre 3 300 et 40 000 K ; au-delà, corps noir raccordé
// au bord (le polynôme n'est pas fait pour les naines blanches très chaudes) [Supposition pour le raccord].
inline double planckV(double t) {      // éclat du corps noir à 550 nm divisé par σT⁴ (unité arbitraire)
    const double x = 1.4388e-2 / (550e-9 * t);
    return 1.0 / ((std::exp(std::min(x, 600.0)) - 1.0) * t * t * t * t);
}
inline double bcV(double t) {
    constexpr double lo = 3300.0, hi = 40000.0;
    if (t >= lo && t <= hi) return rayon_etoile::correctionBolometrique(t);
    const double edge = t < lo ? lo : hi;
    return rayon_etoile::correctionBolometrique(edge) + 2.5 * std::log10(planckV(t) / planckV(edge));
}
inline double magV(double lSun, double teff) { return rayon_etoile::kMbolSoleil - 2.5 * std::log10(std::max(lSun, 1e-30)) - bcV(teff); }
// B-V d'une température : inverse de la formule de Ballesteros (2012) utilisée pour la couleur ; bornée à [-0,4 ; 2,6].
inline double bvDeT(double t) {
    double lo = -0.4, hi = 2.6;
    if (t >= rayon_etoile::temperatureBv(lo)) return lo;
    if (t <= rayon_etoile::temperatureBv(hi)) return hi;
    for (int i = 0; i < 50; ++i) {
        const double m = 0.5 * (lo + hi);
        (rayon_etoile::temperatureBv(m) > t ? lo : hi) = m;
    }
    return 0.5 * (lo + hi);
}

// ---------------------------------------------------------------- tables
struct Trace {
    float m0 = 0;
    uint32_t n = 0;
    uint8_t fin = 0;      // 0 naine blanche ; 1 super-AGB coupé ; 2 effondrement du cœur ; 3 coupée en séquence principale
    const double* age = nullptr;
    const float *mass = nullptr, *logL = nullptr, *logT = nullptr, *logR = nullptr, *co = nullptr;
    const int8_t* phase = nullptr;
};
struct TableNaine {
    float m = 0;
    uint32_t n = 0;
    const double* age = nullptr;
    const float *teff = nullptr, *logg = nullptr, *mbol = nullptr;
};

class Grille {
public:
    bool ready = false;
    std::vector<Trace> traces;
    std::vector<TableNaine> naines;

    bool load(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f) return false;
        data_.assign(std::istreambuf_iterator<char>(f), {});
        return parse();
    }
    bool parse() {
        const uint8_t* b = data_.data();
        const size_t size = data_.size();
        if (size < 16 || std::memcmp(b, "UNIVCYC1", 8) != 0) return false;
        uint32_t nt = 0, nn = 0;
        std::memcpy(&nt, b + 8, 4);
        std::memcpy(&nn, b + 12, 4);
        size_t o = 16;
        auto pad = [&]() { o += (8 - o % 8) % 8; };
        for (uint32_t i = 0; i < nt; ++i) {
            if (o + 12 > size) return false;
            Trace t;
            std::memcpy(&t.m0, b + o, 4);
            std::memcpy(&t.n, b + o + 4, 4);
            t.fin = b[o + 8];
            o += 12;
            pad();
            if (o + t.n * (8ull + 5 * 4 + 1) > size) return false;
            t.age = reinterpret_cast<const double*>(b + o);
            o += 8ull * t.n;
            const float** cols[5] = {&t.mass, &t.logL, &t.logT, &t.logR, &t.co};
            for (auto c : cols) {
                *c = reinterpret_cast<const float*>(b + o);
                o += 4ull * t.n;
            }
            t.phase = reinterpret_cast<const int8_t*>(b + o);
            o += t.n;
            pad();
            traces.push_back(t);
        }
        for (uint32_t i = 0; i < nn; ++i) {
            if (o + 8 > size) return false;
            TableNaine w;
            std::memcpy(&w.m, b + o, 4);
            std::memcpy(&w.n, b + o + 4, 4);
            o += 8;
            if (o + w.n * 20ull > size) return false;
            w.age = reinterpret_cast<const double*>(b + o);
            o += 8ull * w.n;
            w.teff = reinterpret_cast<const float*>(b + o);
            o += 4ull * w.n;
            w.logg = reinterpret_cast<const float*>(b + o);
            o += 4ull * w.n;
            w.mbol = reinterpret_cast<const float*>(b + o);
            o += 4ull * w.n;
            pad();
            naines.push_back(w);
        }
        ready = traces.size() >= 2 && !naines.empty();
        return ready;
    }

private:
    std::vector<uint8_t> data_;
};

// ---------------------------------------------------------------- état à une date
struct Etat {
    Etape etape = Etape::Rien;
    double age = 0;           // âge du modèle (ans) ; négatif avant le début de la contraction (nuage, phase enfouie)
    double masse = 0;         // masse de l'étoile ou de son reste (M☉)
    double lum = 0;           // L/L☉ (bolométrique)
    double teff = 0;          // K
    double rayon = 0;         // R☉ (0 : rien à dessiner)
    bool trouNoir = false;    // le rayon est celui de l'ombre (2,6 rayons de Schwarzschild)
    double magV = 99;         // magnitude absolue V (99 : rien de visible)
    double bv = 0.65;
};

// Recette « rapide » de Fryer et al. 2012 (éq. 15 à 17) : masse du reste d'après la masse finale et le cœur CO.
struct Reste {
    double baryons = 0, gravite = 0;
    bool trouNoir = false, explose = true;
};
inline Reste resteFryer(double mFin, double mCo) {
    constexpr double proto = 1.0;
    double fb;
    if (mCo < 2.5) fb = 0.2;
    else if (mCo < 6.0) fb = 0.286 * mCo - 0.514;
    else if (mCo < 7.0) fb = mFin - proto;
    else if (mCo < 11.0) {
        const double a1 = 0.25 - 1.275 / (mFin - proto), b1 = -11.0 * a1 + 1.0;
        fb = std::clamp(a1 * mCo + b1, 0.0, 1.0) * (mFin - proto);
    } else fb = mFin - proto;
    Reste r;
    r.baryons = std::min(proto + fb, mFin);
    r.explose = r.baryons < mFin - 1e-3;      // tout retombe : effondrement direct, sans explosion
    // Masse gravitationnelle : étoile à neutrons (éq. 13 de Fryer et al. 2012), trou noir : 90 % des baryons. Seuil :
    // 3 M☉ de baryons [Supposition : seuil courant dans les codes qui reprennent cette recette].
    r.trouNoir = r.baryons >= 3.0;
    r.gravite = r.trouNoir ? 0.9 * r.baryons : (std::sqrt(1.0 + 0.3 * r.baryons) - 1.0) / 0.15;
    return r;
}

// Vie d'une étoile de masse initiale donnée : trace interpolée, fin, refroidissement.
struct Vie {
    double m0 = 0;
    uint8_t fin = 0;
    std::vector<double> age;
    std::vector<float> mass, logL, logT, logR, co;
    std::vector<int8_t> phase;
    double ageAujourdhui = 0;      // âge du modèle aujourd'hui (ans)
    int source = 0;                // 0 aucune ; 1 Soleil (âge mesuré) ; 2 placée par l'éclat et la couleur mesurés
    double mBas = 0, mHaut = 0, finBas = 0, finHaut = 0;      // fourchettes (16e à 84e centile) : masse et temps restant (ans)
    // Aujourd'hui, mesuré (rayon_etoile) et calculé : l'écran montre mesuré × (modèle à la date / modèle aujourd'hui).
    double lumMes = 1, teffMes = 5772, rayonMes = 1;
    Reste reste;
    double masseNaine = 0, coolOffset = 0;      // naine blanche : masse, âge de refroidissement au bout de la trace
    std::vector<double> nAge;                   // refroidissement interpolé à la masse de la naine
    std::vector<float> nTeff, nLogg, nMbol;

    bool ok() const { return age.size() >= 2; }
    double ageFin() const { return age.empty() ? 0 : age.back(); }
    bool massive() const { return m0 >= 8.0; }
    double masseCoeur() const { return m0 / kEfficacite; }
    // Date (âge du modèle) où l'étoile meurt : fin de la trace (supernova) ou entrée sur la suite des naines blanches.
    double ageMort() const { return ageFin() + (fin == 1 ? kSuperAgbAns + kContractionAns : 0.0); }

    template <class T>
    static double lin(const T* v, double e, size_t n) {
        const double c = std::clamp(e, 0.0, static_cast<double>(n - 1));
        const size_t j = std::min(static_cast<size_t>(c), n - 2);
        const double f = c - static_cast<double>(j);
        return (1 - f) * v[j] + f * v[j + 1];
    }
    double eepA(double a) const {      // point d'évolution (fractionnaire) à l'âge a, dans la trace
        const size_t n = age.size();
        if (a <= age[0]) return 0;
        if (a >= age[n - 1]) return static_cast<double>(n - 1);
        const size_t hi = static_cast<size_t>(std::upper_bound(age.begin(), age.end(), a) - age.begin());
        const size_t lo = hi - 1;
        const double d = age[hi] - age[lo];
        return static_cast<double>(lo) + (d > 0 ? (a - age[lo]) / d : 0.0);
    }
    // Masse de matière déjà rendue au milieu par les vents (M☉) à l'âge a (dans la trace ; au-delà : tout ce qui n'est pas le reste).
    double massePerdue(double a) const;
    Etat etat(double a) const;
    // Date (âge du modèle) du début de chaque grande étape, pour les boutons du panneau ; -1 si l'étape n'existe pas.
    double debutEtape(Etape e) const;
};

// Refroidissement d'une naine blanche : table de Montréal la plus proche en masse, interpolation linéaire entre deux.
inline void naineInterpolee(const Grille& g, double m, Vie& v) {
    size_t k = 0;
    while (k + 2 < g.naines.size() && g.naines[k + 1].m < m) ++k;
    const TableNaine &a = g.naines[k], &b = g.naines[k + 1];
    const double w = std::clamp((m - a.m) / (b.m - a.m), 0.0, 1.0);
    // Âges communs : ceux de la table a, valeurs de b lues au même âge.
    v.nAge.assign(a.age, a.age + a.n);
    v.nTeff.resize(a.n);
    v.nLogg.resize(a.n);
    v.nMbol.resize(a.n);
    for (uint32_t i = 0; i < a.n; ++i) {
        const double t = a.age[i];
        const size_t hi = std::min<size_t>(static_cast<size_t>(std::upper_bound(b.age, b.age + b.n, t) - b.age), b.n - 1);
        const size_t lo = hi > 0 ? hi - 1 : 0;
        const double f = b.age[hi] > b.age[lo] ? std::clamp((t - b.age[lo]) / (b.age[hi] - b.age[lo]), 0.0, 1.0) : 0.0;
        auto at = [&](const float* c) { return (1 - f) * c[lo] + f * c[hi]; };
        v.nTeff[i] = static_cast<float>((1 - w) * a.teff[i] + w * at(b.teff));
        v.nLogg[i] = static_cast<float>((1 - w) * a.logg[i] + w * at(b.logg));
        v.nMbol[i] = static_cast<float>((1 - w) * a.mbol[i] + w * at(b.mbol));
    }
}

// Vie d'une étoile de masse m0 (M☉) : interpolation entre les deux traces voisines de même fin, sinon la plus proche.
inline Vie vieDe(const Grille& g, double m0) {
    Vie v;
    if (!g.ready) return v;
    v.m0 = m0;
    size_t k = 0;
    while (k + 2 < g.traces.size() && g.traces[k + 1].m0 < m0) ++k;
    const Trace *a = &g.traces[k], *b = &g.traces[k + 1];
    double w = std::clamp(std::log(m0 / a->m0) / std::log(b->m0 / a->m0), 0.0, 1.0);
    if (a->fin != b->fin || a->n != b->n) {      // fins différentes : pas de mélange, la trace la plus proche
        if (w > 0.5) a = b;
        w = 0;
        b = a;
        v.m0 = a->m0;
    }
    const uint32_t n = a->n;
    v.fin = a->fin;
    v.age.resize(n);
    v.mass.resize(n);
    v.logL.resize(n);
    v.logT.resize(n);
    v.logR.resize(n);
    v.co.resize(n);
    v.phase.resize(n);
    for (uint32_t i = 0; i < n; ++i) {
        // âge : interpolé en logarithme (les durées de vie varient en loi de puissance avec la masse)
        v.age[i] = std::exp((1 - w) * std::log(std::max(a->age[i], 1.0)) + w * std::log(std::max(b->age[i], 1.0)));
        v.mass[i] = static_cast<float>((1 - w) * a->mass[i] + w * b->mass[i]);
        v.logL[i] = static_cast<float>((1 - w) * a->logL[i] + w * b->logL[i]);
        v.logT[i] = static_cast<float>((1 - w) * a->logT[i] + w * b->logT[i]);
        v.logR[i] = static_cast<float>((1 - w) * a->logR[i] + w * b->logR[i]);
        v.co[i] = static_cast<float>((1 - w) * a->co[i] + w * b->co[i]);
        v.phase[i] = w < 0.5 ? a->phase[i] : b->phase[i];
    }
    for (uint32_t i = 1; i < n; ++i) v.age[i] = std::max(v.age[i], v.age[i - 1]);      // âge croissant malgré l'arrondi
    if (v.fin == 2) v.reste = resteFryer(v.mass.back(), v.co.back());
    if (v.fin == 0 || v.fin == 1) {
        v.masseNaine = v.fin == 0 ? v.mass.back() : std::clamp(static_cast<double>(v.co.back()), 1.0, 1.35);
        naineInterpolee(g, v.masseNaine, v);
        // raccord : âge de refroidissement où la table a l'éclat de la fin de la trace (fin 0) ; fin 1 : début de la table
        v.coolOffset = v.nAge.front();
        if (v.fin == 0) {
            const double mbolFin = rayon_etoile::kMbolSoleil - 2.5 * v.logL.back();
            for (size_t i = 0; i + 1 < v.nAge.size(); ++i)
                if (v.nMbol[i] <= mbolFin && v.nMbol[i + 1] >= mbolFin) {
                    const double f = (mbolFin - v.nMbol[i]) / std::max(1e-9, static_cast<double>(v.nMbol[i + 1] - v.nMbol[i]));
                    v.coolOffset = v.nAge[i] + f * (v.nAge[i + 1] - v.nAge[i]);
                    break;
                }
        }
    }
    return v;
}

inline double Vie::massePerdue(double a) const {
    if (a <= age.front()) return 0;
    if (a <= ageFin()) return m0 - lin(mass.data(), eepA(a), mass.size());
    const double mFin = mass.back();
    if (fin == 1) {      // super-AGB : enveloppe éjectée à rythme constant pendant kSuperAgbAns
        const double f = std::clamp((a - ageFin()) / kSuperAgbAns, 0.0, 1.0);
        return m0 - (mFin + f * (masseNaine - mFin));
    }
    if (fin == 2) return m0 - mFin;      // l'éjecta de la supernova est compté à part (cycle_matiere.h)
    return m0 - mFin;
}

inline Etat Vie::etat(double a) const {
    Etat s;
    s.age = a;
    if (!ok()) return s;
    if (a < -kAccretionAns) {
        s.etape = a < -kAccretionAns - 5.0 * kCondensationAns ? Etape::Rien : Etape::Nuage;
        return s;
    }
    if (a < 0) {      // phase enfouie : la jeune étoile grossit en avalant son nuage ; éclat de l'accrétion G M Ṁ / R
        s.etape = Etape::Enfouie;
        const double f = (a + kAccretionAns) / kAccretionAns;
        s.masse = m0 * f;
        s.rayon = std::pow(10.0, logR.front());
        const double mdot = m0 * kMsunG / (kAccretionAns * kAnSec);
        s.lum = kGcgs * s.masse * kMsunG * mdot / (s.rayon * kRsunKm * 1e5) / kLsunErgS;
        s.teff = rayon_etoile::kTsoleil * std::pow(s.lum / (s.rayon * s.rayon), 0.25);
    } else if (a <= ageFin()) {
        const double e = eepA(a);
        const size_t n = age.size();
        s.masse = lin(mass.data(), e, n);
        s.lum = std::pow(10.0, lin(logL.data(), e, n));
        s.teff = std::pow(10.0, lin(logT.data(), e, n));
        s.rayon = std::pow(10.0, lin(logR.data(), e, n));
        const int ph = phase[std::min(static_cast<size_t>(e + 0.5), n - 1)];
        switch (ph) {
            case -1: s.etape = Etape::Contraction; break;
            case 0: s.etape = Etape::Sequence; break;
            case 2: s.etape = Etape::Geante; break;
            case 3: s.etape = Etape::Helium; break;
            case 4: case 5: s.etape = Etape::AGB; break;
            case 6: s.etape = s.lum < 10.0 ? Etape::NaineBlanche : s.teff < 2.5e4 ? Etape::PostAGB : Etape::Nebuleuse; break;      /* cœur nu : froid, puis assez chaud pour ioniser, puis naine blanche */
            case 9: s.etape = Etape::WolfRayet; break;
            default: s.etape = Etape::Sequence;
        }
        if (fin == 3 && a >= ageFin()) s.etape = Etape::AuDela;
    } else if (fin == 3) {
        s.etape = Etape::AuDela;
        return s;
    } else if (fin == 2) {
        const double jours = (a - ageFin()) * 365.25;
        const double rFin = std::pow(10.0, logR.back());
        if (!reste.explose) {      // effondrement direct : l'étoile s'éteint, un trou noir reste
            s.etape = Etape::TrouNoir;
        } else if (jours < kSnPlateauJours + kSnChuteJours + 30.0) {
            // Photosphère : l'enveloppe part du rayon de l'étoile à la vitesse de la photosphère (~4 000 km/s), puis
            // l'éjecta devient transparent et la photosphère recule vers le centre en 30 jours [Probable : ordres de grandeur].
            s.etape = Etape::Supernova;
            const double mv = jours < kSnPlateauJours ? kSnPlateau
                            : jours < kSnPlateauJours + kSnChuteJours ? kSnPlateau + kSnChuteMag * (jours - kSnPlateauJours) / kSnChuteJours
                                                                      : kSnPlateau + kSnChuteMag + kSnDeclin * (jours - kSnPlateauJours - kSnChuteJours);
            s.teff = kSnTeff;
            s.lum = std::pow(10.0, -0.4 * (mv + bcV(kSnTeff) - rayon_etoile::kMbolSoleil));
            const double rMax = rFin + 4000.0 * (kSnPlateauJours + kSnChuteJours) * 86400.0 / kRsunKm;
            const double recul = std::clamp((jours - kSnPlateauJours - kSnChuteJours) / 30.0, 0.0, 1.0);
            s.rayon = jours < kSnPlateauJours + kSnChuteJours ? rFin + 4000.0 * jours * 86400.0 / kRsunKm : rMax * (1.0 - recul);
            s.masse = reste.gravite;
            s.magV = mv;
            s.bv = bvDeT(s.teff);
            if (s.rayon <= 0) s.rayon = 0;
            return s;
        } else {
            // étoile à neutrons ou trou noir ; l'éclat de la queue radioactive continue jusqu'à se perdre
            s.etape = reste.trouNoir ? Etape::TrouNoir : Etape::EtoileNeutrons;
            const double mv = kSnPlateau + kSnChuteMag + kSnDeclin * (jours - kSnPlateauJours - kSnChuteJours);
            if (mv < 20.0) {
                s.magV = mv;
                s.bv = bvDeT(kSnTeff);
            }
        }
        s.masse = reste.explose ? reste.gravite : 0.9 * mass.back();
        if (s.etape == Etape::TrouNoir) {
            s.trouNoir = true;
            s.rayon = 2.6 * 2.0 * kGcgs * s.masse * kMsunG / (kCcgs * kCcgs) / 1e5 / kRsunKm;      // ombre : 2,6 r_s
            s.lum = 0;
            s.teff = 0;
            return s;
        }
        s.rayon = kRnsKm / kRsunKm;
        s.teff = kTnsK;
        s.lum = s.rayon * s.rayon * std::pow(s.teff / rayon_etoile::kTsoleil, 4.0);
        if (s.magV >= 99) s.magV = magV(s.lum, s.teff);
        s.bv = bvDeT(s.teff);
        return s;
    } else {
        // naine blanche (fin 0) ; fin 1 : enveloppe éjectée, puis contraction à éclat constant, puis naine blanche
        double dt = a - ageFin();
        const double lFin = std::pow(10.0, logL.back()), rFin = std::pow(10.0, logR.back());
        auto naine = [&](double tCool, Etat& o) {
            const size_t m = nAge.size();
            size_t hi = static_cast<size_t>(std::upper_bound(nAge.begin(), nAge.end(), tCool) - nAge.begin());
            hi = std::clamp<size_t>(hi, 1, m - 1);
            const size_t lo = hi - 1;
            const double f = std::clamp((tCool - nAge[lo]) / std::max(1.0, nAge[hi] - nAge[lo]), 0.0, 1.0);
            o.teff = (1 - f) * nTeff[lo] + f * nTeff[hi];
            const double logg = (1 - f) * nLogg[lo] + f * nLogg[hi];
            const double mbol = (1 - f) * nMbol[lo] + f * nMbol[hi];
            o.lum = std::pow(10.0, -0.4 * (mbol - rayon_etoile::kMbolSoleil));
            o.rayon = std::sqrt(kGcgs * masseNaine * kMsunG / std::pow(10.0, logg)) / 1e5 / kRsunKm;
        };
        s.masse = masseNaine;
        if (fin == 1 && dt < kSuperAgbAns) {
            s.etape = Etape::AGB;
            s.masse = mass.back() + std::clamp(dt / kSuperAgbAns, 0.0, 1.0) * (masseNaine - mass.back());
            s.lum = lFin;
            s.rayon = rFin;
            s.teff = std::pow(10.0, logT.back());
        } else if (fin == 1 && dt < kSuperAgbAns + kContractionAns) {
            Etat w;
            naine(coolOffset, w);
            const double f = (dt - kSuperAgbAns) / kContractionAns;
            s.lum = std::exp((1 - f) * std::log(lFin) + f * std::log(std::max(w.lum, 1e-9)));
            s.rayon = std::exp((1 - f) * std::log(rFin) + f * std::log(w.rayon));
            s.teff = rayon_etoile::kTsoleil * std::pow(s.lum / (s.rayon * s.rayon), 0.25);
            s.etape = s.teff < 2.5e4 ? Etape::PostAGB : Etape::Nebuleuse;
        } else {
            if (fin == 1) dt -= kSuperAgbAns + kContractionAns;
            s.etape = Etape::NaineBlanche;
            naine(coolOffset + dt, s);
        }
    }
    s.magV = magV(s.lum, s.teff);
    s.bv = bvDeT(s.teff);
    return s;
}


inline double Vie::debutEtape(Etape e) const {
    if (!ok()) return -1;
    switch (e) {
        case Etape::Nuage: return -kAccretionAns - kCondensationAns;
        case Etape::Enfouie: return -kAccretionAns;
        case Etape::Supernova: return fin == 2 && reste.explose ? ageFin() : -1;
        case Etape::EtoileNeutrons: return fin == 2 && reste.explose && !reste.trouNoir ? ageFin() + (kSnPlateauJours + kSnChuteJours + 30.0) / 365.25 : -1;
        case Etape::TrouNoir: return fin == 2 && reste.trouNoir ? ageFin() + (reste.explose ? (kSnPlateauJours + kSnChuteJours + 30.0) / 365.25 : 0.0) : -1;
        case Etape::NaineBlanche:
            if (fin == 1) return ageMort();
            if (fin != 0) return -1;
            break;
        default: break;
    }
    for (size_t i = 0; i < age.size(); ++i) {      // première date du modèle à cette étape
        const Etat x = etat(age[i]);
        if (x.etape == e) return age[i];
    }
    if (e == Etape::NaineBlanche && fin == 0) return ageFin();
    return -1;
}

// Place d'une étoile sur la grille d'après son éclat et sa température mesurés (diagramme de Hertzsprung-Russell).
// Probabilité de chaque point (masse, point d'évolution) : écart aux mesures (σ log L = 0,1 ; σ log T = 0,03 [Supposition :
// incertitudes typiques de l'éclat et de la couleur]) × temps passé à ce point × fonction de masse de Salpeter (pente
// -2,35) × pas de la grille. La masse et l'âge retenus sont ceux du point le plus probable ; les fourchettes (16e et
// 84e centiles) sont dites à l'écran : une étoile de même éclat et de même couleur peut être à plusieurs étapes.
struct Placement {
    double m0 = 0, age = 0;
    double mBas = 0, mHaut = 0, finBas = 0, finHaut = 0;
    bool ok = false;
};
inline Placement placer(const Grille& g, double logL, double logT) {
    Placement p;
    struct Pt { double w, m, reste; };
    std::vector<Pt> pts;
    double best = -1;
    for (size_t k = 0; k < g.traces.size(); ++k) {
        const Trace& t = g.traces[k];
        if (t.fin == 3 && t.m0 >= 0.6) continue;
        const double dm = (k + 1 < g.traces.size() ? g.traces[k + 1].m0 : t.m0) - (k > 0 ? g.traces[k - 1].m0 : t.m0);
        const double mort = t.age[t.n - 1];
        for (uint32_t i = 1; i + 1 < t.n; ++i) {
            if (t.phase[i] == -1 || t.phase[i] == 6) continue;      // ni contraction de jeunesse, ni cœur nu : étoiles nommées visibles à l'œil
            const double dl = (t.logL[i] - logL) / 0.1, dT = (t.logT[i] - logT) / 0.03;
            const double chi2 = dl * dl + dT * dT;
            if (chi2 > 50) continue;
            const double dt = 0.5 * (t.age[i + 1] - t.age[i - 1]);
            const double w = std::exp(-0.5 * chi2) * dt * std::pow(t.m0, -2.35) * std::max(dm, 1e-3);
            pts.push_back({w, t.m0, mort - t.age[i]});
            if (w > best) {
                best = w;
                p.m0 = t.m0;
                p.age = t.age[i];
            }
        }
    }
    if (pts.empty()) return p;
    auto quant = [&](auto key, double q) {
        std::vector<std::pair<double, double>> v;
        double tot = 0;
        for (const Pt& x : pts) { v.push_back({key(x), x.w}); tot += x.w; }
        std::sort(v.begin(), v.end());
        double c = 0;
        for (const auto& [val, w] : v) {
            c += w;
            if (c >= q * tot) return val;
        }
        return v.back().first;
    };
    p.mBas = quant([](const Pt& x) { return x.m; }, 0.16);
    p.mHaut = quant([](const Pt& x) { return x.m; }, 0.84);
    p.finBas = quant([](const Pt& x) { return x.reste; }, 0.16);
    p.finHaut = quant([](const Pt& x) { return x.reste; }, 0.84);
    p.ok = true;
    return p;
}

// Vie d'une étoile nommée : le Soleil (masse 1, âge mesuré), ou placée par son éclat (M_V) et sa couleur (B-V) mesurés.
inline Vie vieEtoile(const Grille& g, bool soleil, double absMagV, double bv) {
    if (soleil) {
        Vie v = vieDe(g, 1.0);
        v.ageAujourdhui = kAgeSoleilAns;
        v.source = 1;
        v.mBas = v.mHaut = 1.0;
        v.finBas = v.finHaut = v.ageMort() - kAgeSoleilAns;
        v.lumMes = 1.0;
        v.teffMes = rayon_etoile::kTsoleil;
        v.rayonMes = 1.0;
        return v;
    }
    const double r = rayon_etoile::rayonKm(absMagV, bv);
    if (r <= 0) return {};
    const double t = rayon_etoile::temperatureBv(bv);
    const double l = std::pow(10.0, -0.4 * (absMagV + rayon_etoile::correctionBolometrique(t) - rayon_etoile::kMbolSoleil));
    const Placement p = placer(g, std::log10(l), std::log10(t));
    if (!p.ok) return {};
    Vie v = vieDe(g, p.m0);
    v.ageAujourdhui = p.age;
    v.source = 2;
    v.mBas = p.mBas;
    v.mHaut = p.mHaut;
    v.finBas = p.finBas;
    v.finHaut = p.finHaut;
    v.lumMes = l;
    v.teffMes = t;
    v.rayonMes = r / kRsunKm;
    return v;
}

// Ce que l'écran montre à une date : mesuré aujourd'hui × (modèle à la date / modèle aujourd'hui) pour l'étoile elle-même
// (aujourd'hui, exactement la mesure) ; le reste (naine, étoile à neutrons, trou noir) et la supernova : le modèle seul.
struct Vu {
    Etat modele;
    double rayonKm = 0, teff = 0, magV = 99, bv = 0.65;
    bool etoile = true;      // vrai tant que c'est l'étoile elle-même (avant sa mort) : le rapport mesuré / modèle s'applique
};
inline Vu vuA(const Vie& v, double ansDepuisAujourdhui) {
    Vu o;
    if (!v.ok()) return o;
    const Etat now = v.etat(v.ageAujourdhui);
    o.modele = v.etat(v.ageAujourdhui + ansDepuisAujourdhui);
    const Etat& s = o.modele;
    o.etoile = s.age >= 0 && s.age <= v.ageMort() && s.etape != Etape::NaineBlanche;
    if (s.rayon <= 0 && s.magV >= 99) return o;
    if (o.etoile && now.rayon > 0 && s.rayon > 0) {
        o.rayonKm = v.rayonMes * kRsunKm * s.rayon / now.rayon;
        o.teff = v.teffMes * s.teff / now.teff;
        const double lum = v.lumMes * s.lum / now.lum;
        o.magV = magV(lum, o.teff);
    } else {
        o.rayonKm = s.rayon * kRsunKm;
        o.teff = s.teff;
        o.magV = s.magV;
    }
    o.bv = o.teff > 0 ? bvDeT(o.teff) : s.bv;
    return o;
}

}  // namespace cycle
