// Appli PC « Univers », bibliothèque univers_physique : voir systeme_solaire.h.
#include "systeme_solaire.h"

#include <array>
#include <cmath>
#include <limits>
#include <new>
#include <stdexcept>

namespace phys {

namespace {

constexpr std::array<int, static_cast<size_t>(nb::kN)> kCodes = {
    kMercure, kVenus, kTerreLune, kMars, kJupiter, kSaturne, kUranus,
    kNeptune, kPluton, kCeres,    kVesta, kPallas,  kHygie};
constexpr double kKmS = kAuKm / kJourS;  // UA/jour -> km/s

int indexOf(int naif) {
    for (size_t i = 0; i < kCodes.size(); ++i) {
        if (kCodes[i] == naif) return static_cast<int>(i);
    }
    return -1;
}

// Vitesse barycentrique du Soleil dans les coordonnées démocratiques : la quantité de mouvement totale est nulle.
std::array<double, 3> sunVel(const nb::State& s) {
    double px = 0.0, py = 0.0, pz = 0.0;
    for (size_t i = 0; i < static_cast<size_t>(nb::kN); ++i) {
        const double g = nbody_donnees::kGm[i];
        px += g * s.V[3 * i];
        py += g * s.V[3 * i + 1];
        pz += g * s.V[3 * i + 2];
    }
    return {-px / nb::kGmSun, -py / nb::kGmSun, -pz / nb::kGmSun};
}

}  // namespace

bool SystemeSolaire::construire(const SourceDe440& de440, double ansDirects) {
    avant_.clear();
    apres_.clear();
    debutDirect_ = 0.0;
    finDirect_ = 0.0;
    if (!de440 || !std::isfinite(ansDirects) || ansDirects <= 0.0 || ansDirects > 1e9) return false;
    auto failBuild = [&]() {
        avant_.clear();
        apres_.clear();
        debutDirect_ = 0.0;
        finDirect_ = 0.0;
        return false;
    };

    for (int side = 0; side < 2; ++side) {
        const double jdB = side ? kDe440Fin : kDe440Debut;
        // Les quatre astéroïdes ne sont pas dans DE440 : ils viennent du calcul parti de JPL Horizons au 10/11/2026.
        nb::Integrator ast;
        ast.advanceTo(jdB);
        double bary[3 * (nb::kN + 1)];
        ast.barycentric(bary);
        Vec3 ps, vs;
        if (!de440(kSoleil, jdB, ps, vs)) return failBuild();
        const double sP[3] = {ps.x / kAuKm, ps.y / kAuKm, ps.z / kAuKm};
        const double sV[3] = {vs.x / kKmS, vs.y / kKmS, vs.z / kKmS};
        nb::State s;
        s.jd = jdB;
        for (size_t i = 0; i < static_cast<size_t>(nb::kN); ++i) {
            double r[3], v[3];
            if (i < 9) {  // planètes et Pluton : barycentres de DE440
                Vec3 p, w;
                if (!de440(kCodes[i], jdB, p, w)) return failBuild();
                r[0] = p.x / kAuKm;
                r[1] = p.y / kAuKm;
                r[2] = p.z / kAuKm;
                v[0] = w.x / kKmS;
                v[1] = w.y / kKmS;
                v[2] = w.z / kKmS;
            } else {
                for (size_t c = 0; c < 3; ++c) {
                    r[c] = bary[3 * (i + 1) + c];
                    v[c] = ast.state().V[3 * i + c];
                }
            }
            for (size_t c = 0; c < 3; ++c) {
                s.Q[3 * i + c] = r[c] - sP[c];
                s.V[3 * i + c] = v[c];
            }
        }
        /* Calage du pas de 4 jours : l'intégrateur déplace un peu le mouvement moyen (surtout Mercure), d'une quantité qui
           dépend de la position sur l'orbite au départ. On ajuste donc ici, à chaque borne, la vitesse héliocentrique de
           chaque planète pour que sa longitude retrouve DE440 400 ans à l'intérieur de la plage (méthode de Newton, gain de la
           troisième loi de Kepler) ; astéroïdes : facteurs de la page. */
        {
            const double jdT = jdB + (side ? -400.0 : 400.0) * 365.25;
            double tgt[9];
            Vec3 tp, tv, ts, tsv;
            if (!de440(kSoleil, jdT, ts, tsv)) return failBuild();
            for (size_t i = 0; i < 9; ++i) {
                if (!de440(kCodes[i], jdT, tp, tv)) return failBuild();
                tgt[i] = std::atan2(tp.y - ts.y, tp.x - ts.x);
            }
            const nb::State base = s;
            double sc[static_cast<size_t>(nb::kN)];
            for (size_t i = 0; i < static_cast<size_t>(nb::kN); ++i) {
                sc[i] = nbody_donnees::kScale[i];
            }
            auto apply = [&](nb::State& o) {
                o = base;
                for (size_t i = 0; i < static_cast<size_t>(nb::kN); ++i) {
                    for (size_t c = 0; c < 3; ++c) {
                        o.V[3 * i + c] = sV[c] + (base.V[3 * i + c] - sV[c]) * (1.0 + sc[i]);
                    }
                }
            };
            for (int iter = 0; iter < 8; ++iter) {
                nb::State o;
                apply(o);
                nb::Integrator it(o);
                it.advanceTo(jdT);
                for (size_t i = 0; i < 9; ++i) {
                    const double* q = &it.state().Q[3 * i];
                    double e = std::atan2(q[1], q[0]) - tgt[i];
                    e = std::atan2(std::sin(e), std::cos(e));
                    const double* r0 = &base.Q[3 * i];
                    double vv[3];
                    for (size_t c = 0; c < 3; ++c) {
                        vv[c] = base.V[3 * i + c] - sV[c];
                    }
                    const double rn = std::sqrt(r0[0] * r0[0] + r0[1] * r0[1] + r0[2] * r0[2]);
                    const double v2 = vv[0] * vv[0] + vv[1] * vv[1] + vv[2] * vv[2];
                    const double a = 1.0 / (2.0 / rn - v2 / nb::kGmSun);
                    const double gain =
                        -3.0 * std::sqrt(nb::kGmSun / (a * a * a)) * a * v2 / nb::kGmSun * (jdT - jdB);  /* dλ/ds */
                    sc[i] -= e / gain;
                }
            }
            apply(s);
        }
        // Points de reprise, de la borne vers l'extérieur.
        auto& cps = side ? apres_ : avant_;
        const double dir = side ? 1.0 : -1.0;
        const double stepsD = std::ceil(ansDirects * 365.25 / kPasReprise);
        if (!std::isfinite(stepsD) || stepsD > static_cast<double>(std::numeric_limits<long>::max() / 2)) {
            return failBuild();
        }
        const long n = static_cast<long>(stepsD);
        /* Mémoire réservée d'un coup : un manque de mémoire rend false au lieu de lever une exception dans le fil de
           calcul de fenetre.cpp (qui terminerait le programme). */
        try {
            cps.reserve(static_cast<size_t>(n) + 1);
        } catch (const std::bad_alloc&) {
            return failBuild();
        } catch (const std::length_error&) {
            return failBuild();
        }
        nb::Integrator it(s);
        cps.push_back(it.state());
        for (long k = 1; k <= n; ++k) {
            it.advanceTo(jdB + dir * static_cast<double>(k) * kPasReprise);
            cps.push_back(it.state());
        }
    }
    debutDirect_ = kDe440Debut - static_cast<double>(avant_.size() - 1) * kPasReprise;
    finDirect_ = kDe440Fin + static_cast<double>(apres_.size() - 1) * kPasReprise;
    return true;
}

bool SystemeSolaire::chargerTable(const std::string& chemin) { return table_.load(chemin); }

Plage SystemeSolaire::plageTable() const {
    if (!table_.loaded()) return {0.0, 0.0};
    return {table_.firstJd(), table_.lastJd()};
}

bool SystemeSolaire::etatDirect(double jd, nb::State& s) const {
    const bool apres = jd > kDe440Fin;
    const auto& cps = apres ? apres_ : avant_;
    if (cps.empty()) return false;
    const double jdB = apres ? kDe440Fin : kDe440Debut;
    const double d = std::fabs(jd - jdB);
    const long k = static_cast<long>(std::llround(d / kPasReprise));
    if (k < 0 || static_cast<size_t>(k) >= cps.size()) return false;
    nb::Integrator it(cps[static_cast<size_t>(k)]);
    it.advanceTo(jd);
    s = it.state();
    return true;
}

bool SystemeSolaire::etat(int naif, double jd, Vec3& pos, Vec3& vit, Statut& statut) const {
    if (!std::isfinite(jd) || (jd >= kDe440Debut && jd <= kDe440Fin)) return false;  // plage de la NASA
    statut = Statut::Calcule;
    if ((!avant_.empty() && jd >= debutDirect_ && jd < kDe440Debut) ||
        (!apres_.empty() && jd > kDe440Fin && jd <= finDirect_)) {
        nb::State s;
        if (!etatDirect(jd, s)) return false;
        if (naif == kSoleil) {
            pos = {};
            vit = {};
            return true;
        }
        const int i = indexOf(naif);
        if (i < 0) return false;
        const size_t ui = static_cast<size_t>(i);
        const auto sv = sunVel(s);
        pos = {s.Q[3 * ui] * kAuKm, s.Q[3 * ui + 1] * kAuKm, s.Q[3 * ui + 2] * kAuKm};
        vit = {(s.V[3 * ui] - sv[0]) * kKmS, (s.V[3 * ui + 1] - sv[1]) * kKmS, (s.V[3 * ui + 2] - sv[2]) * kKmS};
        return true;
    }
    if (!table_.loaded() || naif < kMercure || naif > kPluton) return false;  // table : 8 planètes et Pluton
    double a[3], b[3], c[3];
    if (!table_.position(naif - 1, jd, a) || !table_.position(naif - 1, jd - 0.5, b) ||
        !table_.position(naif - 1, jd + 0.5, c)) {
        return false;
    }
    pos = {a[0] * kAuKm, a[1] * kAuKm, a[2] * kAuKm};
    vit = {(c[0] - b[0]) * kKmS, (c[1] - b[1]) * kKmS, (c[2] - b[2]) * kKmS};  // dérivée centrée sur un jour
    return true;
}

bool SystemeSolaire::positions(double jd, std::span<Vec3> out) const {
    if (out.size() < static_cast<size_t>(nb::kN)) return false;
    if (!std::isfinite(jd) || (jd >= kDe440Debut && jd <= kDe440Fin)) return false;
    if ((!avant_.empty() && jd >= debutDirect_ && jd < kDe440Debut) ||
        (!apres_.empty() && jd > kDe440Fin && jd <= finDirect_)) {
        nb::State s;
        if (!etatDirect(jd, s)) return false;
        for (size_t i = 0; i < static_cast<size_t>(nb::kN); ++i) {
            out[i] = {s.Q[3 * i] * kAuKm, s.Q[3 * i + 1] * kAuKm, s.Q[3 * i + 2] * kAuKm};
        }
        return true;
    }
    if (!table_.loaded()) return false;
    for (size_t i = 0; i < 9; ++i) {
        double a[3];
        if (!table_.position(static_cast<int>(i), jd, a)) return false;
        out[i] = {a[0] * kAuKm, a[1] * kAuKm, a[2] * kAuKm};
    }
    constexpr double kNan = std::numeric_limits<double>::quiet_NaN();
    for (size_t i = 9; i < static_cast<size_t>(nb::kN); ++i) {
        out[i] = {kNan, kNan, kNan};  // la table ne donne pas les astéroïdes : inconnus (NaN), jamais devinés
    }
    return true;
}

std::span<const int> SystemeSolaire::corps() { return {kCodes.data(), kCodes.size()}; }

}  // namespace phys
