// Appli PC « Univers » : la matière qu'une étoile rend au milieu (vents, nébuleuse planétaire, reste de supernova) et le
// nuage dont elle naît, en couches sphériques. Masse conservée : chaque gramme perdu par l'étoile (cycle_etoile.h) part
// dans une couche, à la vitesse de son vent ; rien n'apparaît ni ne disparaît, la matière se dilue en s'étendant.
// Sans dépendance au reste de l'appli (contrôlé par essai_cycle).
//
// Modèles (signalés à l'écran) :
//   - vitesse des vents : étoiles chaudes 2,6 × la vitesse de libération au-dessus de 21 000 K, 1,3 × entre 10 000 et
//     21 000 K (Lamers, Snow & Lindholm 1995) ; vents froids des géantes : 15 km/s (Höfner & Olofsson 2018) [Probable] ;
//   - freinage par le milieu interstellaire (1 atome d'hydrogène par cm³ [Supposition : moyenne du disque]) : chasse-neige
//     à quantité de mouvement conservée pour les vents, Sedov-Taylor pour une supernova (énergie 10⁵¹ erg) [Probable] ;
//   - poussière : dans les vents froids (Teff < 4 000 K) et le nuage de naissance ; opacité visible 209 cm²/g de gaz pour
//     le milieu interstellaire (Bohlin, Savage & Drake 1978), moitié dans les vents (rapport poussière/gaz 1/200) [Probable] ;
//   - lumière : gaz ionisé par l'étoile (photons de plus de 13,6 eV d'un corps noir, recombinaisons cas B à 10⁴ K,
//     α_B = 2,59e-13 cm³/s, Osterbrock & Ferland 2006) ; lumière de l'étoile diffusée par la poussière (albédo 0,6) ;
//     énergie des photons absorbés rendue à 30 % en lumière visible [Supposition] ;
//     choc d'une supernova : 10⁻⁴ du flux d'énergie cinétique en lumière visible [Supposition : ordre de grandeur].
//     Teintes des raies (Hα rouge, [O III] vert-bleu) et part de [O III] : [Supposition].
#pragma once
#include "cycle_etoile.h"

namespace cycle {

constexpr double kPi = 3.14159265358979323846;
constexpr double kNismCm3 = 1.0;
constexpr double kMh = 1.6735e-24;
constexpr double kRhoIsm = kNismCm3 * 1.4 * kMh * (kAlCm * kAlCm * kAlCm) / kMsunG;      // M☉ / al³ (≈ 1,0e-3)
constexpr double kKappaIsm = 209.0 * kMsunG / (kAlCm * kAlCm);                            // al² / M☉
constexpr double kKappaVent = 0.5 * kKappaIsm;
constexpr double kAlbedo = 0.6;
constexpr double kAlphaB = 2.59e-13;
constexpr double kCkms = 299792.458;
constexpr double kChocVisible = 1.0e-4;
constexpr int kCouchesMax = 64;
constexpr double kVitesseCoquilleKms = 25.0;

struct Paquet {      // matière perdue entre deux dates de la vie (âges du modèle, ans)
    double t0, t1, masse, vKms;
    bool poussiere;
};

inline double vitesseVent(double masse, double rayon, double teff) {
    const double vlib = 617.7 * std::sqrt(std::max(masse, 1e-3) / std::max(rayon, 1e-3));      // km/s, M et R en unités solaires
    if (teff > 21000) return 2.6 * vlib;
    if (teff > 10000) return 1.3 * vlib;
    return 15.0;
}

// Paquets de matière perdue, du plus ancien au plus récent ; un paquet tous les 0,2 % de la masse initiale, ou à chaque
// changement d'étape (la vitesse change).
inline std::vector<Paquet> paquets(const Vie& v) {
    std::vector<Paquet> out;
    if (!v.ok()) return out;
    const double pas = 0.002 * v.m0;
    size_t i0 = 0;
    for (size_t i = 1; i < v.age.size(); ++i) {
        const double dm = v.mass[i0] - v.mass[i];
        const bool coupe = v.phase[i] != v.phase[i0] || i + 1 == v.age.size();
        if (dm < pas && !coupe) continue;
        if (dm > 1e-7) {
            const size_t mid = (i0 + i) / 2;
            const double teff = std::pow(10.0, v.logT[mid]);
            out.push_back({v.age[i0], v.age[i], dm, vitesseVent(v.mass[mid], std::pow(10.0, v.logR[mid]), teff), teff < 4000});
        }
        i0 = i;
    }
    if (v.fin == 1) out.push_back({v.ageFin(), v.ageFin() + kSuperAgbAns, v.mass.back() - v.masseNaine, 15.0, true});
    return out;
}

// Début du vent rapide qui suit le vent lent d'une géante : premier âge où l'étoile dépasse 21 000 K après sa dernière
// période froide (moins de 10 000 K, hors jeunesse) ; -1 s'il n'y en a pas.
inline double debutVentRapide(const Vie& v) {
    if (!v.ok()) return -1;
    size_t froid = 0;
    bool vu = false;
    for (size_t i = 0; i < v.age.size(); ++i)
        if (v.phase[i] >= 2 && v.logT[i] < 4.0) { froid = i; vu = true; }
    if (!vu) return -1;
    for (size_t i = froid; i < v.age.size(); ++i)
        if (v.logT[i] > std::log10(21000.0)) return v.age[i];
    if (v.fin == 1) return v.ageFin() + kSuperAgbAns + 0.5 * kContractionAns;
    return -1;
}

// Rayon atteint par une coquille lancée à v (al/an) depuis dt ans, qui balaie sa part (part) du milieu : m r + π/3 ρ r⁴ = m v dt.
inline double rayonChasseNeige(double m, double v, double dt, double part) {
    if (dt <= 0) return 0;
    const double c = kPi / 3.0 * kRhoIsm * part, P = m * v * dt;
    double r = std::min(v * dt, std::pow(P / std::max(c, 1e-300), 0.25));
    for (int k = 0; k < 40; ++k) {
        const double f = m * r + c * r * r * r * r - P, d = m + 4.0 * c * r * r * r;
        const double nr = std::max(r - f / d, 0.5 * r);
        if (std::fabs(nr - r) < 1e-12 * std::max(r, 1e-30)) break;
        r = nr;
    }
    return r;
}

struct Couche {
    double rIn, rOut;      // années-lumière
    double masse;          // M☉ (matière de l'étoile + milieu balayé)
    double masseEtoile;    // M☉ venus de l'étoile (ou du nuage de naissance)
    double kappa;          // al²/M☉ (0 : pas de poussière)
    double choc;           // lumière visible du choc (L☉), répartie dans la couche
    int genre;             // 0 vent ou nébuleuse ; 1 reste de supernova ; 2 nuage de naissance
};

struct Bilan {         // masses à l'écran (M☉) : tout ce que le cœur de nuage a donné est quelque part
    double coeur = 0, etoile = 0, nuage = 0, vents = 0, ejecta = 0, neutrinos = 0;
    double milieu = 0;    // part déjà mêlée au milieu interstellaire (plus distincte de lui, plus dessinée)
};

// Mélange avec le milieu : une coquille freinée sous la vitesse du son du milieu tiède (~10 km/s) se confond avec lui
// (critère de Cioffi, McKee & Bertschinger 1988 pour les restes de supernova) ; mélange progressif de 10 à 5 km/s
// [Supposition : largeur du passage]. Rend la part encore distincte.
constexpr double kMelangeHautKms = 10.0, kMelangeBasKms = 5.0;
inline double partDistincte(double vKms) { return std::clamp((vKms - kMelangeBasKms) / (kMelangeHautKms - kMelangeBasKms), 0.0, 1.0); }

// Couches de matière autour de l'étoile à l'âge a du modèle.
inline std::vector<Couche> couches(const Vie& v, const std::vector<Paquet>& pq, double a, Bilan* bilan = nullptr) {
    std::vector<Couche> out;
    if (!v.ok()) return out;
    const double mc = v.masseCoeur();
    Bilan b;
    b.coeur = mc;
    const Etat s = v.etat(a);
    // Nuage de naissance : le cœur se resserre (0,3 -> 0,1 pc, kCondensationAns), donne sa masse à l'étoile pendant la
    // phase enfouie, puis le reste (deux tiers) est chassé à kDispersionKms.
    if (a < -kAccretionAns - 5.0 * kCondensationAns) {
        b.nuage = mc;      // matière encore diffuse dans le grand nuage (pas dessinée : sa forme n'est pas connue)
    } else {
        double r, m;
        if (a < -kAccretionAns) {
            r = kCoeurAl * (1.0 + 2.0 * (-kAccretionAns - a) / kCondensationAns);
            m = mc;
        } else if (a < 0) {
            r = kCoeurAl;
            m = mc - v.m0 * (a + kAccretionAns) / kAccretionAns;
        } else {
            r = kCoeurAl + kDispersionKms / kCkms * a;
            m = mc - v.m0;
        }
        // le nuage se confond avec le milieu quand sa densité n'est plus que quelques fois la sienne (de 10 à 1 fois)
        const double dens = m / (4.0 / 3.0 * kPi * r * r * r) / kRhoIsm;
        const double garde = std::clamp((dens - 1.0) / 9.0, 0.0, 1.0);
        b.nuage = m * garde;
        b.milieu += m * (1.0 - garde);
        if (garde > 0) out.push_back({0.0, r, m * garde, m * garde, kKappaIsm, 0.0, 2});
    }
    // Vents : chaque paquet déjà lancé, en coquille entre le rayon de sa matière la plus ancienne et la plus récente. La
    // masse lancée suit exactement celle que l'étoile a perdue (le dernier paquet reçoit le reste).
    const double perdu = v.massePerdue(a);
    double cumul = 0;
    size_t dernier = 0;
    for (size_t i = 0; i < pq.size() && pq[i].t0 < a; ++i) dernier = i + 1;
    for (size_t i = 0; i + 1 < dernier; ++i) cumul += pq[i].masse;
    for (size_t i = 0; i < dernier; ++i) {
        const Paquet& p = pq[i];
        const double m = i + 1 < dernier ? p.masse : std::max(perdu - cumul, 0.0);
        if (m <= 0) continue;
        const double v0 = p.vKms / kCkms, part = m / std::max(perdu, 1e-12);
        const double rOut = rayonChasseNeige(m, v0, a - p.t0, part);
        const double rIn = rayonChasseNeige(m, v0, a - std::min(a, p.t1), part);
        const double balaye = 4.0 / 3.0 * kPi * rOut * rOut * rOut * kRhoIsm * part;
        const double garde = partDistincte(p.vKms * m / (m + balaye));      // vitesse du bord extérieur, freiné
        b.vents += m * garde;
        b.milieu += m * (1.0 - garde);
        if (garde > 0) out.push_back({rIn, std::max(rOut, rIn * 1.001 + 1e-12), (m + balaye) * garde, m * garde, p.poussiere ? kKappaVent : 0.0, 0.0, 0});
    }
    // Vents qui se rattrapent (Kwok, Purton & Fitzgerald 1978) : quand un vent rapide (> 200 km/s, cœur nu et chaud)
    // suit le vent lent d'une géante, il pousse ce vent lent en une coquille mince et dense : c'est la nébuleuse planétaire.
    // Vitesse de la coquille : 25 km/s, valeur typique mesurée des nébuleuses planétaires (20 à 40 km/s) [Probable] ;
    // épaisseur : 15 % du rayon [Supposition]. La matière balayée change de place, pas de masse.
    const double tRapide = debutVentRapide(v);
    if (tRapide > 0 && a > tRapide) {
        const double rs = kVitesseCoquilleKms / kCkms * (a - tRapide);
        Couche coq{0.85 * rs, rs, 0, 0, 0, 0, 0};
        double kapMasse = 0;
        for (Couche& c : out) {
            if (c.genre != 0 || c.rIn >= rs) continue;
            const double tot = c.rOut * c.rOut * c.rOut - c.rIn * c.rIn * c.rIn;
            const double rr = std::min(c.rOut, rs);
            const double f = tot > 0 ? std::clamp((rr * rr * rr - c.rIn * c.rIn * c.rIn) / tot, 0.0, 1.0) : 1.0;
            coq.masse += f * c.masse;
            coq.masseEtoile += f * c.masseEtoile;
            kapMasse += f * c.masse * c.kappa;
            c.masse *= 1.0 - f;
            c.masseEtoile *= 1.0 - f;
            c.rIn = std::max(c.rIn, rs);
            if (c.rOut <= c.rIn) c.rOut = c.rIn * 1.001 + 1e-12;
        }
        if (coq.masse > 0) {
            coq.kappa = kapMasse / coq.masse;
            out.push_back(coq);
        }
    }
    // Supernova : l'enveloppe part du rayon de l'étoile ; expansion libre puis Sedov-Taylor.
    if (v.fin == 2 && v.reste.explose && a > v.ageFin()) {
        const double mej = v.mass.back() - v.reste.baryons;
        const double t = (a - v.ageFin()) * kAnSec;
        const double vej = std::sqrt(10.0 * kSnEnergieErg / (3.0 * mej * kMsunG));      // cm/s
        const double rho = kNismCm3 * 1.4 * kMh;
        const double rLibre = vej * t, rSedov = 1.15 * std::pow(kSnEnergieErg * t * t / rho, 0.2);
        const double rCm = std::min(rLibre, rSedov) + std::pow(10.0, v.logR.back()) * kRsunKm * 1e5;
        const double vs = rLibre < rSedov ? vej : 0.4 * rSedov / std::max(t, 1.0);
        const double r = rCm / kAlCm;
        const double balaye = 4.0 / 3.0 * kPi * r * r * r * kRhoIsm;
        const double ep = std::clamp(1.0 / (1.0 + 4.0 * balaye / mej), 0.08, 1.0);
        const double choc = kChocVisible * 0.5 * rho * vs * vs * vs * 4.0 * kPi * rCm * rCm / kLsunErgS;
        const double garde = partDistincte(vs / 1e5);
        if (garde > 0) out.push_back({r * (1.0 - ep), r, (mej + balaye) * garde, mej * garde, 0.0, choc * garde, 1});
        b.ejecta = mej * garde;
        b.milieu += mej * (1.0 - garde);
        b.neutrinos = v.reste.baryons - v.reste.gravite;
    } else if (v.fin == 2 && !v.reste.explose && a > v.ageFin()) {
        b.neutrinos = v.mass.back() - 0.9 * v.mass.back();
    }
    b.etoile = s.masse;
    if (bilan) *bilan = b;
    return out;
}

// ---------------------------------------------------------------- lumière des couches
// Photons ionisants par seconde d'un corps noir de luminosité L (L☉) et de température T ; energie : leur énergie
// moyenne (erg), si demandée.
inline double photonsIonisants(double lSun, double teff, double* energie = nullptr) {
    if (energie) *energie = 0;
    if (teff < 8000 || lSun <= 0) return 0;
    const double k = 1.380649e-16, h = 6.62607e-27, sigma = 5.670374e-5;
    const double x0 = 13.6 * 1.602177e-12 / (k * teff);
    double integ = 0, integE = 0;
    const int n = 400;
    const double dx = 60.0 / n;
    for (int i = 0; i < n; ++i) {
        const double x = x0 + (i + 0.5) * dx;
        const double f = x * x / (std::exp(std::min(x, 600.0)) - 1.0) * dx;
        integ += f;
        integE += f * x;
    }
    if (energie && integ > 0) *energie = integE / integ * k * teff;
    const double parSurface = 2.0 * kPi / (kCcgs * kCcgs) * std::pow(k * teff / h, 3.0) * integ;
    const double surface = lSun * kLsunErgS / (sigma * std::pow(teff, 4.0));
    return parSurface * surface;
}

struct Profil {
    int n = 0;
    float r[kCouchesMax + 1] = {};       // bords des anneaux (années-lumière)
    float rgb[kCouchesMax][3] = {};      // émissivité (L☉ par al³), en couleur
    float ext[kCouchesMax] = {};         // extinction visible (par al)
    double lumiere = 0;                  // lumière visible totale (L☉)
    double ionise = 0;                   // masse ionisée (M☉)
};

// Teintes (lumière linéaire) : Hα à 656 nm, [O III] à 501 nm [Supposition : teintes approchées].
constexpr float kHalpha[3] = {1.0f, 0.06f, 0.10f}, kOiii[3] = {0.08f, 1.0f, 0.75f};

inline Profil profil(const std::vector<Couche>& cs, const Etat& centre, const float couleurEtoile[3]) {
    Profil p;
    double rMax = 0, rMin = 1e300;
    for (const Couche& c : cs) {
        rMax = std::max(rMax, c.rOut);
        if (c.rOut > 0) rMin = std::min(rMin, std::max(c.rIn, c.rOut * 0.02));
    }
    if (rMax <= 0) return p;
    rMin = std::clamp(rMin, rMax * 1e-5, rMax * 0.5);
    const int n = kCouchesMax;
    p.n = n;
    p.r[0] = 0.0f;
    for (int k = 1; k <= n; ++k) p.r[k] = static_cast<float>(rMin * std::pow(rMax / rMin, (k - 1.0) / (n - 1.0)));
    double rho[kCouchesMax] = {}, kap[kCouchesMax] = {}, choc[kCouchesMax] = {};
    for (const Couche& c : cs) {
        const double vc = c.rOut * c.rOut * c.rOut - c.rIn * c.rIn * c.rIn;
        if (vc <= 0) continue;
        for (int k = 0; k < n; ++k) {
            const double a = std::max<double>(p.r[k], c.rIn), b = std::min<double>(p.r[k + 1], c.rOut);
            if (b <= a) continue;
            const double vk = static_cast<double>(p.r[k + 1]) * p.r[k + 1] * p.r[k + 1] - static_cast<double>(p.r[k]) * p.r[k] * p.r[k];
            const double part = (b * b * b - a * a * a) / vc;
            rho[k] += c.masse * part / (4.0 / 3.0 * kPi * vk);
            kap[k] += c.kappa * c.masse * part / (4.0 / 3.0 * kPi * vk);
            choc[k] += c.choc * part / (4.0 / 3.0 * kPi * vk);
        }
    }
    // Ionisation du dedans vers le dehors, tant que l'étoile fournit des photons ; poussière : lumière diffusée.
    // Chaque photon absorbé apporte son énergie au gaz, qui la rend surtout en raies ; part visible : 30 % [Supposition :
    // ordre de grandeur, Hα et [O III] dominent le refroidissement d'une nébuleuse ionisée].
    double eMoy = 0;
    double q = centre.lum > 0 ? photonsIonisants(centre.lum, centre.teff, &eMoy) : 0.0;
    const double rOiii = centre.teff > 50000 ? 3.0 : centre.teff > 30000 ? 1.0 : 0.2;
    const double eRaie = 0.3 * eMoy / kLsunErgS;      // L☉ visibles par recombinaison/s
    const double lv = centre.lum > 0 && centre.teff > 0 ? std::pow(10.0, -0.4 * (magV(centre.lum, centre.teff) - 4.83)) : 0.0;
    double tau = 0;
    for (int k = 0; k < n; ++k) {
        const double vk = 4.0 / 3.0 * kPi * (static_cast<double>(p.r[k + 1]) * p.r[k + 1] * p.r[k + 1] - static_cast<double>(p.r[k]) * p.r[k] * p.r[k]);
        const double rm = 0.5 * (p.r[k] + p.r[k + 1]);
        double e[3] = {0, 0, 0};
        if (rho[k] > 0 && q > 0) {
            const double nh = 0.7 * rho[k] * kMsunG / (kAlCm * kAlCm * kAlCm) / kMh;      // atomes d'H par cm³
            const double rec = kAlphaB * 1.1 * nh * nh * vk * (kAlCm * kAlCm * kAlCm);    // recombinaisons par seconde
            const double f = std::min(1.0, q / std::max(rec, 1e-300));
            q -= f * rec;
            p.ionise += f * rho[k] * vk;
            const double lum = f * rec * eRaie;
            for (int c = 0; c < 3; ++c) e[c] += lum / vk * (kHalpha[c] + rOiii * kOiii[c]) / (1.0 + rOiii);
        }
        if (kap[k] > 0 && lv > 0) {
            const double d = kAlbedo * kap[k] * lv / (4.0 * kPi * rm * rm) * std::exp(-tau);
            for (int c = 0; c < 3; ++c) e[c] += d * couleurEtoile[c];
        }
        if (choc[k] > 0)
            for (int c = 0; c < 3; ++c) e[c] += choc[k] * kHalpha[c];
        tau += kap[k] * (p.r[k + 1] - p.r[k]);
        for (int c = 0; c < 3; ++c) {
            p.rgb[k][c] = static_cast<float>(e[c]);
            p.lumiere += e[c] * vk / 3.0;
        }
        p.ext[k] = static_cast<float>(kap[k]);
    }
    return p;
}

}  // namespace cycle
