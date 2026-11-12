// Appli PC « Univers », bibliothèque univers_physique : voir systeme_solaire.h.
#include "systeme_solaire.h"

#include <array>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>

namespace phys {

namespace {
bool empreinte(const SourceDe440& de440, double out[18]);      // plus bas

constexpr std::array<int, nb::kN> kCodes = {kMercure, kVenus, kTerreLune, kMars, kJupiter, kSaturne, kUranus, kNeptune, kPluton, kCeres, kVesta, kPallas, kHygie};
constexpr double kKmS = kAuKm / kJourS;      // UA/jour -> km/s

int indexOf(int naif) {
    for (int i = 0; i < nb::kN; i++) if (kCodes[i] == naif) return i;
    return -1;
}

// Vitesse barycentrique du Soleil dans les coordonnées démocratiques : la quantité de mouvement totale est nulle.
std::array<double, 3> sunVel(const nb::State& s) {
    double px = 0, py = 0, pz = 0;
    for (int i = 0; i < nb::kN; i++) { const double g = nbody_donnees::kGm[i]; px += g * s.V[3 * i]; py += g * s.V[3 * i + 1]; pz += g * s.V[3 * i + 2]; }
    return {-px / nb::kGmSun, -py / nb::kGmSun, -pz / nb::kGmSun};
}

}  // namespace

bool SystemeSolaire::construire(const SourceDe440& de440, double ansDirects) {
    avant_.clear(); apres_.clear();
    if (!empreinte(de440, empreinte_)) return false;
    for (int side = 0; side < 2; side++) {
        const double jdB = side ? kDe440Fin : kDe440Debut;
        // Les quatre astéroïdes ne sont pas dans DE440 : ils viennent du calcul parti de JPL Horizons au 10/11/2026.
        nb::Integrator ast; ast.advanceTo(jdB);
        double bary[3 * (nb::kN + 1)]; ast.barycentric(bary);
        Vec3 ps, vs;
        if (!de440(kSoleil, jdB, ps, vs)) return false;
        const double sP[3] = {ps.x / kAuKm, ps.y / kAuKm, ps.z / kAuKm}, sV[3] = {vs.x / kKmS, vs.y / kKmS, vs.z / kKmS};
        nb::State s; s.jd = jdB;
        for (int i = 0; i < nb::kN; i++) {
            double r[3], v[3];
            if (i < 9) {      // planètes et Pluton : barycentres de DE440
                Vec3 p, w; if (!de440(kCodes[i], jdB, p, w)) return false;
                r[0] = p.x / kAuKm; r[1] = p.y / kAuKm; r[2] = p.z / kAuKm; v[0] = w.x / kKmS; v[1] = w.y / kKmS; v[2] = w.z / kKmS;
            } else {
                for (int c = 0; c < 3; c++) { r[c] = bary[3 * (i + 1) + c]; v[c] = ast.state().V[3 * i + c]; }
            }
            for (int c = 0; c < 3; c++) { s.Q[3 * i + c] = r[c] - sP[c]; s.V[3 * i + c] = v[c]; }
        }
        /* Calage du pas de 4 jours : l'intégrateur déplace un peu le mouvement moyen (surtout Mercure), d'une quantité qui
           dépend de la position sur l'orbite au départ. On ajuste donc ici, à chaque borne, la vitesse héliocentrique de
           chaque planète pour que sa longitude retrouve DE440 400 ans à l'intérieur de la plage (méthode de Newton, gain de la
           troisième loi de Kepler) ; astéroïdes : facteurs de la page. */
        {
            const double jdT = jdB + (side ? -400.0 : 400.0) * 365.25;
            double tgt[9];
            Vec3 tp, tv, ts, tsv; if (!de440(kSoleil, jdT, ts, tsv)) return false;
            for (int i = 0; i < 9; i++) { if (!de440(kCodes[i], jdT, tp, tv)) return false; tgt[i] = std::atan2(tp.y - ts.y, tp.x - ts.x); }
            const nb::State base = s; double sc[nb::kN];
            for (int i = 0; i < nb::kN; i++) sc[i] = nbody_donnees::kScale[i];
            auto apply = [&](nb::State& o) { o = base; for (int i = 0; i < nb::kN; i++) for (int c = 0; c < 3; c++) o.V[3 * i + c] = sV[c] + (base.V[3 * i + c] - sV[c]) * (1 + sc[i]); };
            for (int iter = 0; iter < 8; iter++) {
                nb::State o; apply(o); nb::Integrator it(o); it.advanceTo(jdT);
                for (int i = 0; i < 9; i++) {
                    const double* q = &it.state().Q[3 * i]; double e = std::atan2(q[1], q[0]) - tgt[i]; e = std::atan2(std::sin(e), std::cos(e));
                    const double* r0 = &base.Q[3 * i]; double vv[3]; for (int c = 0; c < 3; c++) vv[c] = base.V[3 * i + c] - sV[c];
                    const double rn = std::sqrt(r0[0] * r0[0] + r0[1] * r0[1] + r0[2] * r0[2]), v2 = vv[0] * vv[0] + vv[1] * vv[1] + vv[2] * vv[2], a = 1 / (2 / rn - v2 / nb::kGmSun);
                    const double gain = -3 * std::sqrt(nb::kGmSun / (a * a * a)) * a * v2 / nb::kGmSun * (jdT - jdB);      /* dλ/ds */
                    sc[i] -= e / gain;
                }
            }
            apply(s);
        }
        // Points de reprise, de la borne vers l'extérieur.
        auto& cps = side ? apres_ : avant_;
        const double dir = side ? 1 : -1; const long n = (long)std::ceil(ansDirects * 365.25 / kPasReprise);
        nb::Integrator it(s); cps.push_back(it.state());
        for (long k = 1; k <= n; k++) { it.advanceTo(jdB + dir * k * kPasReprise); cps.push_back(it.state()); }
    }
    debutDirect_ = kDe440Debut - (avant_.size() - 1) * kPasReprise;
    finDirect_ = kDe440Fin + (apres_.size() - 1) * kPasReprise;
    ansDirects_ = ansDirects;
    return true;
}

namespace {
constexpr char kMagicReserve[8] = {'U', 'N', 'I', 'V', 'S', 'S', 'R', '1'};
// Empreinte des fichiers DE440 : Soleil, Terre-Lune et Jupiter aux deux bornes (km).
bool empreinte(const SourceDe440& de440, double out[18]) {
    int k = 0;
    for (const double jd : {kDe440Debut, kDe440Fin})
        for (const int c : {kSoleil, kTerreLune, kJupiter}) {
            Vec3 p, v; if (!de440(c, jd, p, v)) return false;
            out[k++] = p.x; out[k++] = p.y; out[k++] = p.z;
        }
    return true;
}
}  // namespace

bool SystemeSolaire::sauver(const std::string& chemin) const {
    if (avant_.empty() || apres_.empty() || empreinte_[0] == 0) return false;
    const std::string tmp = chemin + ".tmp";
    {
        std::ofstream f(tmp, std::ios::binary);
        const double tete[4] = {ansDirects_, nbody_donnees::kJd0, (double)avant_.size(), (double)apres_.size()};
        f.write(kMagicReserve, 8); f.write((const char*)tete, sizeof tete); f.write((const char*)empreinte_, sizeof empreinte_);
        for (const auto* c : {&avant_, &apres_}) f.write((const char*)c->data(), (std::streamsize)(c->size() * sizeof(nb::State)));
        if (!f) return false;
    }
    std::remove(chemin.c_str());
    return std::rename(tmp.c_str(), chemin.c_str()) == 0;
}

bool SystemeSolaire::chargerReserve(const std::string& chemin, const SourceDe440& de440, double ansDirects) {
    std::ifstream f(chemin, std::ios::binary);
    char m[8]; double tete[4], emp[18], ici[18];
    if (!f.read(m, 8) || std::memcmp(m, kMagicReserve, 8) != 0 || !f.read((char*)tete, sizeof tete) || !f.read((char*)emp, sizeof emp)) return false;
    if (tete[0] != ansDirects || tete[1] != nbody_donnees::kJd0 || !empreinte(de440, ici)) return false;
    for (int k = 0; k < 18; k++) if (std::fabs(emp[k] - ici[k]) > 1e-6) return false;      // autres fichiers DE440 : réserve refusée
    std::vector<nb::State> av((size_t)tete[2]), ap((size_t)tete[3]);
    if (!f.read((char*)av.data(), (std::streamsize)(av.size() * sizeof(nb::State))) || !f.read((char*)ap.data(), (std::streamsize)(ap.size() * sizeof(nb::State)))) return false;
    avant_ = std::move(av); apres_ = std::move(ap); std::memcpy(empreinte_, emp, sizeof emp); ansDirects_ = ansDirects;
    debutDirect_ = kDe440Debut - (avant_.size() - 1) * kPasReprise;
    finDirect_ = kDe440Fin + (apres_.size() - 1) * kPasReprise;
    return true;
}

bool SystemeSolaire::chargerTable(const std::string& chemin) { return table_.load(chemin); }

Plage SystemeSolaire::plageTable() const {
    if (!table_.loaded()) return {0, 0};
    return {nbody_donnees::kJd0 + table_.firstYear() * 365.25, nbody_donnees::kJd0 + table_.lastYear() * 365.25};
}

bool SystemeSolaire::grille(double jd, nb::State& s) const {
    const bool apres = jd > kDe440Fin;
    const auto& cps = apres ? apres_ : avant_;
    if (cps.empty()) return false;
    const double jdB = apres ? kDe440Fin : kDe440Debut, d = std::fabs(jd - jdB);
    const long k = (long)std::floor(d / kPasReprise); if (k >= (long)cps.size()) return false;
    const long pasEntiers = (long)std::floor((d - k * kPasReprise) / kPas);      // pas entiers depuis le point de reprise, sans dépasser jd
    nb::Integrator it(cps[k]); it.step(apres ? kPas : -kPas, pasEntiers); s = it.state();
    return true;
}

bool SystemeSolaire::etatDirect(double jd, nb::State& s) const {
    if (!grille(jd, s)) return false;
    finir(s, jd); return true;
}

bool SystemeSolaire::etat(int naif, double jd, Vec3& pos, Vec3& vit, Statut& statut) const {
    if (jd >= kDe440Debut && jd <= kDe440Fin) return false;      // plage de la NASA : l'appli lit les éphémérides
    statut = Statut::Calcule;
    if ((jd >= debutDirect_ && jd < kDe440Debut) || (jd > kDe440Fin && jd <= finDirect_)) {
        nb::State s; if (!etatDirect(jd, s)) return false;
        if (naif == kSoleil) { pos = {}; vit = {}; return true; }
        const int i = indexOf(naif); if (i < 0) return false;
        const auto sv = sunVel(s);
        pos = {s.Q[3 * i] * kAuKm, s.Q[3 * i + 1] * kAuKm, s.Q[3 * i + 2] * kAuKm};
        vit = {(s.V[3 * i] - sv[0]) * kKmS, (s.V[3 * i + 1] - sv[1]) * kKmS, (s.V[3 * i + 2] - sv[2]) * kKmS};
        return true;
    }
    if (!table_.loaded() || naif < kMercure || naif > kPluton) return false;      // table : 8 planètes et Pluton
    double a[3], b[3], c[3];
    if (!table_.position(naif - 1, jd, a) || !table_.position(naif - 1, jd - 0.5, b) || !table_.position(naif - 1, jd + 0.5, c)) return false;
    pos = {a[0] * kAuKm, a[1] * kAuKm, a[2] * kAuKm};
    vit = {(c[0] - b[0]) * kKmS, (c[1] - b[1]) * kKmS, (c[2] - b[2]) * kKmS};      // dérivée centrée sur un jour
    return true;
}

bool SystemeSolaire::positions(double jd, std::span<Vec3> out) const {
    if (out.size() < (size_t)nb::kN) return false;
    if ((jd >= debutDirect_ && jd < kDe440Debut) || (jd > kDe440Fin && jd <= finDirect_)) {
        nb::State s; if (!etatDirect(jd, s)) return false;
        for (int i = 0; i < nb::kN; i++) out[i] = {s.Q[3 * i] * kAuKm, s.Q[3 * i + 1] * kAuKm, s.Q[3 * i + 2] * kAuKm};
        return true;
    }
    Vec3 v; Statut st;
    for (int i = 0; i < 9; i++) if (!etat(kCodes[i], jd, out[i], v, st)) return false;
    for (int i = 9; i < nb::kN; i++) out[i] = {NAN, NAN, NAN};      // la table ne donne pas les astéroïdes : inconnus (NaN), jamais devinés
    return true;
}

bool Suivi::aller(double jd) {
    const auto& S = *ss_; ok_ = false;
    if (jd >= kDe440Debut && jd <= kDe440Fin) return false;
    if ((jd >= S.debutDirect_ && jd < kDe440Debut) || (jd > kDe440Fin && jd <= S.finDirect_)) {
        const bool apres = jd > kDe440Fin, memeCote = direct_ && ((g_.jd > kDe440Fin) == apres);
        const double jdB = apres ? kDe440Fin : kDe440Debut, d = std::fabs(jd - jdB), cible = jdB + (apres ? 1 : -1) * std::floor(d / SystemeSolaire::kPas) * SystemeSolaire::kPas;
        const long n = std::lround((cible - g_.jd) / SystemeSolaire::kPas);
        /* temps qui défile : pas entiers depuis le dernier état de la grille (vers le passé aussi, le schéma est réversible) ;
           les mêmes pas que depuis le point de reprise, donc le même résultat qu'une requête isolée */
        if (memeCote && std::abs(n) * SystemeSolaire::kPas < SystemeSolaire::kPasReprise && (std::floor(std::fabs(g_.jd - jdB) / SystemeSolaire::kPasReprise) == std::floor(d / SystemeSolaire::kPasReprise))) { nb::Integrator it(g_); it.step(n >= 0 ? SystemeSolaire::kPas : -SystemeSolaire::kPas, std::abs(n)); g_ = it.state(); }
        else if (!S.grille(jd, g_)) return false;
        s_ = g_; SystemeSolaire::finir(s_, jd);
        direct_ = true; ok_ = true; jd_ = jd; return true;
    }
    direct_ = false; Vec3 p, v; Statut st;
    if (!S.etat(kMars, jd, p, v, st)) return false;      // la table couvre-t-elle cette date ?
    ok_ = true; jd_ = jd; return true;
}

bool Suivi::etat(int naif, Vec3& pos, Vec3& vit, Statut& statut) const {
    if (!ok_) return false;
    if (!direct_) return ss_->etat(naif, jd_, pos, vit, statut);
    statut = Statut::Calcule;
    if (naif == kSoleil) { pos = {}; vit = {}; return true; }
    const int i = indexOf(naif); if (i < 0) return false;
    const auto sv = sunVel(s_);
    pos = {s_.Q[3 * i] * kAuKm, s_.Q[3 * i + 1] * kAuKm, s_.Q[3 * i + 2] * kAuKm};
    vit = {(s_.V[3 * i] - sv[0]) * kKmS, (s_.V[3 * i + 1] - sv[1]) * kKmS, (s_.V[3 * i + 2] - sv[2]) * kKmS};
    return true;
}

std::span<const int> SystemeSolaire::corps() { return {kCodes.data(), kCodes.size()}; }

}  // namespace phys
