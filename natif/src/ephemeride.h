// Appli PC « Univers » : lecture directe des éphémérides de la NASA (JPL DE440), fichier .bsp tel que publié par
// le NAIF (https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp, 114 Mo, années 1550 à 2650).
//
// Format : fichier DAF / SPK (NAIF, « SPK Required Reading » et « DAF Required Reading »). Chaque segment donne la
// position d'un corps par rapport à un centre, en km, repère ICRF (équatorial J2000), par des polynômes de
// Tchebychev sur des intervalles de temps fixes (segments de type 2 : position ; type 3 : position et vitesse,
// utilisé par les fichiers des lunes). Le temps est en secondes TDB depuis J2000,0.
// Plusieurs fichiers se complètent (planètes : de440.bsp ; lunes : jup365.bsp, sat441.bsp…) : voir Set.
// Ici : aucun calcul d'orbite, seulement la lecture des polynômes de la NASA. Hors de la plage du fichier, la
// fonction répond « inconnu » (false).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <string>
#include <unordered_set>
#include <vector>

#include "fichier_mappe.h"

namespace eph {

constexpr double kAuKm = 149597870.7;
constexpr double kObliquityJ2000 =
    84381.448 / 3600.0 * 3.14159265358979323846 / 180.0;  // UAI 1976, celle des repères « écliptique J2000 » du JPL

// Codes NAIF.
enum Body : int {
    kSsb = 0,
    kMercuryBary = 1,
    kVenusBary = 2,
    kEmb = 3,
    kMarsBary = 4,
    kJupiterBary = 5,
    kSaturnBary = 6,
    kUranusBary = 7,
    kNeptuneBary = 8,
    kPlutoBary = 9,
    kSun = 10,
    kMercury = 199,
    kVenus = 299,
    kMoon = 301,
    kEarth = 399
};

struct Vec {
    double x = 0, y = 0, z = 0;
};

class Spk {
public:
    Spk() = default;
    ~Spk() = default;
    Spk(const Spk&) = delete;
    Spk& operator=(const Spk&) = delete;
    Spk(Spk&&) noexcept = default;
    Spk& operator=(Spk&&) noexcept = default;

    void close() noexcept {
        segments_.clear();
        sourceName_.clear();
        file_.close();
    }

    const std::string& name() const noexcept { return sourceName_; }

    bool open(const std::string& path, std::string& error) {
        close();
        error.clear();
        auto failOpen = [&](const std::string& msg) {
            close();
            error = msg;
            return false;
        };

        if (!file_.open(path, &error)) return false;
        const uint8_t* base = file_.data();
        const uint64_t size = file_.size();
        if (size < 1024 || std::memcmp(base, "DAF/SPK", 7) != 0) {
            return failOpen("ce n'est pas un fichier SPK du NAIF");
        }
        if (std::memcmp(base + 88, "LTL-IEEE", 8) != 0) {
            return failOpen("fichier SPK non petit-boutiste");
        }
        int32_t nd = 0, ni = 0, fward = 0;
        std::memcpy(&nd, base + 8, 4);
        std::memcpy(&ni, base + 12, 4);
        std::memcpy(&fward, base + 76, 4);
        if (nd != 2 || ni != 6) return failOpen("fichier SPK inattendu (ND, NI)");

        const uint64_t maxRecs = size / 1024;
        if (fward < 2 || static_cast<uint64_t>(fward) > maxRecs) {
            return failOpen("en-tête SPK invalide (FWARD)");
        }

        // Chaîne des enregistrements de résumés : suivant, précédent, nombre, puis les résumés (2 réels, 6 entiers).
        std::unordered_set<int> visited;
        for (int rec = fward; rec > 0;) {
            if (!visited.insert(rec).second) return failOpen("chaîne DAF cyclique");
            if (visited.size() > 65536) return failOpen("trop d'enregistrements de résumés SPK");
            const uint8_t* r = record(rec);
            if (!r) return failOpen("fichier SPK tronqué");
            const double next = loadDouble(r);
            const double countD = loadDouble(r + 16);
            const double maxNext =
                std::min(static_cast<double>(maxRecs), static_cast<double>(std::numeric_limits<int>::max()));
            if (!std::isfinite(next) || next < 0.0 || next > maxNext || std::floor(next) != next) {
                return failOpen("lien DAF invalide");
            }
            if (!std::isfinite(countD) || countD < 0.0 || countD > 25.0 || std::floor(countD) != countD) {
                return failOpen("nombre de résumés SPK invalide");
            }
            const int count = static_cast<int>(countD);
            for (int i = 0; i < count; ++i) {
                const uint8_t* s = r + 24 + static_cast<size_t>(i) * 40;
                Segment seg;
                int32_t ints[6];
                seg.start = loadDouble(s);
                seg.end = loadDouble(s + 8);
                std::memcpy(ints, s + 16, 24);
                seg.target = ints[0];
                seg.center = ints[1];
                seg.frame = ints[2];
                seg.type = ints[3];
                if ((seg.type != 2 && seg.type != 3) || seg.frame != 1) continue;  // segments Tchebychev, ICRF
                if (!std::isfinite(seg.start) || !std::isfinite(seg.end) || seg.start > seg.end) continue;
                if (ints[4] < 1 || ints[5] < 1) continue;
                const uint64_t first = static_cast<uint64_t>(ints[4]);
                const uint64_t last = static_cast<uint64_t>(ints[5]);
                if (last < first + 4 || last > size / 8) continue;
                const uint64_t dataWords = last - first - 3;
                // Les 4 derniers réels : début, durée d'un intervalle, taille d'un enregistrement, nombre.
                const uint8_t* tail = base + (last - 4) * 8;
                seg.init = loadDouble(tail);
                seg.intlen = loadDouble(tail + 8);
                const double rsizeD = loadDouble(tail + 16);
                const double nD = loadDouble(tail + 24);
                if (!std::isfinite(seg.init) || !std::isfinite(seg.intlen) || !(seg.intlen > 0.0)) continue;
                const double maxInt = static_cast<double>(std::numeric_limits<int>::max());
                if (!std::isfinite(rsizeD) || !std::isfinite(nD) || std::floor(rsizeD) != rsizeD ||
                    std::floor(nD) != nD || rsizeD < 5.0 || nD < 1.0 || rsizeD > maxInt || nD > maxInt ||
                    rsizeD > static_cast<double>(dataWords)) {
                    continue;
                }
                seg.rsize = static_cast<int>(rsizeD);
                seg.n = static_cast<int>(nD);
                const int comps = seg.type == 3 ? 6 : 3;
                if ((seg.rsize - 2) % comps != 0 || (seg.rsize - 2) / comps < 1) continue;
                if (static_cast<uint64_t>(seg.n) > dataWords / static_cast<uint64_t>(seg.rsize)) continue;
                seg.data = base + (first - 1) * 8;
                segments_.push_back(seg);
            }
            rec = static_cast<int>(next);
            if (rec != 0 && rec < 2) return failOpen("lien DAF invalide");
        }
        if (segments_.empty()) return failOpen("aucun segment lisible");

        const size_t slash = path.find_last_of("/\\");
        sourceName_ = (slash == std::string::npos) ? path : path.substr(slash + 1);
        return true;
    }

    // Plage de dates couverte par tous les segments (secondes TDB depuis J2000,0).
    double firstEt() const {
        double v = -1e300;
        for (const auto& s : segments_) v = std::max(v, s.start);
        return v;
    }
    double lastEt() const {
        double v = 1e300;
        for (const auto& s : segments_) v = std::min(v, s.end);
        return v;
    }

    // Indique le centre d'un corps dans ce fichier sans évaluer les polynômes.
    bool findCenter(int body, double et, int& center) const {
        const Segment* seg = find(body, et);
        if (!seg) return false;
        center = seg->center;
        return true;
    }

    // Un pas de la chaîne : position et vitesse d'un corps par rapport à son centre dans ce fichier. false : pas ici.
    bool step(int body, double et, Vec& pos, Vec& vel, int& center) const {
        const Segment* seg = find(body, et);
        if (!seg || !evaluate(*seg, et, pos, vel)) return false;
        center = seg->center;
        return true;
    }

    // Position et vitesse d'un corps par rapport au centre de masse du système solaire, en km et km/s, repère ICRF.
    bool state(int body, double et, Vec& pos, Vec& vel) const {
        pos = {};
        vel = {};
        for (int guard = 0; body != kSsb && guard < 8; ++guard) {
            const Segment* seg = find(body, et);
            if (!seg) return false;
            Vec p, v;
            if (!evaluate(*seg, et, p, v)) return false;
            pos = {pos.x + p.x, pos.y + p.y, pos.z + p.z};
            vel = {vel.x + v.x, vel.y + v.y, vel.z + v.z};
            if (!std::isfinite(pos.x) || !std::isfinite(pos.y) || !std::isfinite(pos.z) || !std::isfinite(vel.x) ||
                !std::isfinite(vel.y) || !std::isfinite(vel.z)) {
                return false;
            }
            body = seg->center;
        }
        return body == kSsb;
    }

private:
    struct Segment {
        double start = 0, end = 0, init = 0, intlen = 0;
        int target = 0, center = 0, frame = 0, type = 0, rsize = 0, n = 0;
        const uint8_t* data = nullptr;
    };

    static double loadDouble(const uint8_t* p) {
        double v = 0.0;
        std::memcpy(&v, p, sizeof(v));
        return v;
    }

    // Enregistrements de 1024 octets, numérotés à partir de 1.
    const uint8_t* record(int rec) const {
        if (rec < 1) return nullptr;
        const uint64_t rIdx = static_cast<uint64_t>(rec - 1);
        return rIdx < file_.size() / 1024 ? file_.data() + rIdx * 1024 : nullptr;
    }

    const Segment* find(int target, double et) const {
        for (const auto& s : segments_) {
            if (s.target == target && et >= s.start && et <= s.end) return &s;
        }
        return nullptr;
    }

    static bool evaluate(const Segment& seg, double et, Vec& pos, Vec& vel) {
        if (!std::isfinite(et)) return false;
        const double idxD = std::floor((et - seg.init) / seg.intlen);
        if (!std::isfinite(idxD)) return false;
        const int i = static_cast<int>(std::clamp(idxD, 0.0, static_cast<double>(seg.n - 1)));
        const uint8_t* r = seg.data + static_cast<size_t>(i) * static_cast<size_t>(seg.rsize) * 8;
        const double mid = loadDouble(r);
        const double radius = loadDouble(r + 8);
        if (!std::isfinite(mid) || !std::isfinite(radius) || !(radius > 0.0)) return false;
        // Type 3 : les coefficients de vitesse suivent ceux de position (non lus : on dérive).
        const int nc = (seg.rsize - 2) / (seg.type == 3 ? 6 : 3);
        const double t = (et - mid) / radius;
        if (!std::isfinite(t)) return false;
        // Polynômes de Tchebychev T_k(t) et leurs dérivées, par récurrence.
        double T[32], D[32];
        const int n = std::min(nc, 32);
        T[0] = 1.0;
        D[0] = 0.0;
        if (n > 1) {
            T[1] = t;
            D[1] = 1.0;
        }
        for (int k = 2; k < n; ++k) {
            T[k] = 2.0 * t * T[k - 1] - T[k - 2];
            D[k] = 2.0 * T[k - 1] + 2.0 * t * D[k - 1] - D[k - 2];
            if (!std::isfinite(T[k]) || !std::isfinite(D[k])) return false;
        }
        double p[3] = {0.0, 0.0, 0.0}, v[3] = {0.0, 0.0, 0.0};
        for (int a = 0; a < 3; ++a) {
            const uint8_t* c = r + (2 + static_cast<size_t>(a) * static_cast<size_t>(nc)) * 8;
            for (int k = 0; k < n; ++k) {
                const double ck = loadDouble(c + static_cast<size_t>(k) * 8);
                p[a] += ck * T[k];
                v[a] += ck * D[k];
            }
            v[a] /= radius;
            if (!std::isfinite(p[a]) || !std::isfinite(v[a])) return false;
        }
        pos = {p[0], p[1], p[2]};
        vel = {v[0], v[1], v[2]};
        return true;
    }

    univers::MappedFile file_;
    std::string sourceName_;
    std::vector<Segment> segments_;
};

// Plusieurs fichiers lus ensemble : un corps peut être donné dans un fichier par rapport à un centre décrit dans un
// autre (Io par rapport au centre de masse de Jupiter dans jup365.bsp, ce centre de masse par rapport à celui du
// système solaire dans de440.bsp). Les fichiers sont interrogés dans l'ordre où ils ont été ajoutés.
class Set {
public:
    bool add(const std::string& path, std::string& error) {
        auto f = std::make_unique<Spk>();
        if (!f->open(path, error)) return false;
        files_.push_back(std::move(f));
        return true;
    }
    bool empty() const { return files_.empty(); }

    bool state(int body, double et, Vec& pos, Vec& vel) const {
        pos = {};
        vel = {};
        for (int guard = 0; body != kSsb && guard < 8; ++guard) {
            Vec p, v;
            int center = 0;
            bool found = false;
            for (const auto& f : files_) {
                if (f->step(body, et, p, v, center)) {
                    found = true;
                    break;
                }
            }
            if (!found) return false;
            pos = {pos.x + p.x, pos.y + p.y, pos.z + p.z};
            vel = {vel.x + v.x, vel.y + v.y, vel.z + v.z};
            if (!std::isfinite(pos.x) || !std::isfinite(pos.y) || !std::isfinite(pos.z) || !std::isfinite(vel.x) ||
                !std::isfinite(vel.y) || !std::isfinite(vel.z)) {
                return false;
            }
            body = center;
        }
        return body == kSsb;
    }

    // Noms des fichiers .bsp utilisés pour remonter jusqu'au centre de masse du système solaire (ex. « jup365.bsp, de440.bsp »).
    std::string sourcesOf(int body, double et) const {
        std::vector<std::string> names;
        for (int guard = 0; body != kSsb && guard < 8; ++guard) {
            int center = 0;
            const Spk* matched = nullptr;
            for (const auto& f : files_) {
                if (f->findCenter(body, et, center)) {
                    matched = f.get();
                    break;
                }
            }
            if (!matched) return {};
            const std::string& n = matched->name();
            if (!n.empty() && std::find(names.begin(), names.end(), n) == names.end()) {
                names.push_back(n);
            }
            body = center;
        }
        if (body != kSsb) return {};
        std::string out;
        for (size_t i = 0; i < names.size(); ++i) {
            if (i > 0) out += ", ";
            out += names[i];
        }
        return out;
    }

private:
    std::vector<std::unique_ptr<Spk>> files_;
};

// Équatorial J2000 (ICRF) -> écliptique J2000 : rotation autour de l'axe x de l'obliquité.
inline Vec toEcliptic(Vec e) {
    const double c = std::cos(kObliquityJ2000), s = std::sin(kObliquityJ2000);
    return {e.x, c * e.y + s * e.z, -s * e.y + c * e.z};
}

// Jour julien (TDB) -> secondes TDB depuis J2000,0.
inline double etOfJd(double jd) { return (jd - 2451545.0) * 86400.0; }

}  // namespace eph
