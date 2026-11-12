// Appli PC « Univers » : trajectoires réelles des sondes (sondes.bin, pipeline/natif/sondes.py ; source : JPL Horizons).
// Une position et une vitesse par jour, par rapport au Soleil (écliptique J2000, km et km/s), et une toutes les
// 10 minutes autour de chaque survol de planète. Entre deux valeurs : polynôme d'Hermite, qui passe exactement par les
// deux positions avec les deux vitesses. Hors des dates fournies : inconnu (false).
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace sondes {

struct Segment {
    double jd0 = 0, stepDays = 1;
    std::vector<double> states;      // n x 6
    size_t count() const { return states.size() / 6; }
    double lastJd() const { return jd0 + stepDays * static_cast<double>(count() - 1); }
    bool covers(double jd) const { return count() >= 2 && jd >= jd0 && jd <= lastJd(); }
};

struct Probe {
    std::string name;
    std::vector<Segment> segments;      // le premier couvre tout le vol ; les suivants, plus fins, les survols
    double firstJd() const { return segments.empty() ? 0 : segments[0].jd0; }
    double lastJd() const { return segments.empty() ? 0 : segments[0].lastJd(); }

    // Position (km) et vitesse (km/s) au jour julien jd ; false hors de la trajectoire fournie.
    bool at(double jd, double pos[3], double vel[3]) const {
        const Segment* seg = nullptr;
        for (const Segment& s : segments)
            if (s.covers(jd) && (!seg || s.stepDays < seg->stepDays)) seg = &s;      // le tronçon le plus fin qui contient la date
        if (!seg) return false;
        const double x = (jd - seg->jd0) / seg->stepDays;
        const size_t k = std::min(static_cast<size_t>(x), seg->count() - 2);
        const double s = x - static_cast<double>(k), h = seg->stepDays * 86400.0;      // durée du pas en secondes
        const double* a = &seg->states[k * 6];
        const double* b = a + 6;
        const double h00 = 2 * s * s * s - 3 * s * s + 1, h10 = s * s * s - 2 * s * s + s, h01 = -2 * s * s * s + 3 * s * s, h11 = s * s * s - s * s;
        const double d00 = 6 * s * s - 6 * s, d10 = 3 * s * s - 4 * s + 1, d01 = -6 * s * s + 6 * s, d11 = 3 * s * s - 2 * s;
        for (int c = 0; c < 3; ++c) {
            pos[c] = h00 * a[c] + h10 * h * a[3 + c] + h01 * b[c] + h11 * h * b[3 + c];
            vel[c] = (d00 * a[c] + d01 * b[c]) / h + d10 * a[3 + c] + d11 * b[3 + c];
        }
        return true;
    }
};

// Rend false si le fichier manque ou n'est pas lisible (le simulateur continue sans sondes).
inline bool load(const std::string& path, std::vector<Probe>& out) {
    FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) return false;
    char magic[8];
    int64_t n = 0;
    bool ok = std::fread(magic, 1, 8, f) == 8 && std::memcmp(magic, "UNIVSON2", 8) == 0 && std::fread(&n, 8, 1, f) == 1 && n > 0 && n < 100;
    for (int64_t i = 0; ok && i < n; ++i) {
        char name[33] = {};
        Probe p;
        int64_t segs = 0;
        ok = std::fread(name, 1, 32, f) == 32 && std::fread(&segs, 8, 1, f) == 1 && segs > 0 && segs < 100;
        p.name = name;
        for (int64_t k = 0; ok && k < segs; ++k) {
            Segment s;
            int64_t count = 0;
            ok = std::fread(&s.jd0, 8, 1, f) == 1 && std::fread(&s.stepDays, 8, 1, f) == 1 && std::fread(&count, 8, 1, f) == 1 && count > 1 && count < 10000000;
            if (!ok) break;
            s.states.resize(static_cast<size_t>(count) * 6);
            ok = std::fread(s.states.data(), 8, s.states.size(), f) == s.states.size();
            if (ok) p.segments.push_back(std::move(s));
        }
        if (ok) out.push_back(std::move(p));
    }
    std::fclose(f);
    return ok && !out.empty();
}

}  // namespace sondes
