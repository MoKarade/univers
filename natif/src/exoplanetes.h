// Appli PC « Univers » : les planètes des autres étoiles (Marc, 20/11/2026 : « on ne voit jamais de planètes »).
//
// Données MESURÉES : NASA Exoplanet Archive, table pscomppars (DOI 10.26133/NEA13), via pipeline/natif/exoplanetes.py puis
// exoplanetes_app.py, qui relie chaque étoile hôte à son étoile du catalogue de l'appli (2 208 hôtes reliés au 20/11/2026 ;
// les autres sont trop faibles pour le catalogue de l'appli et ne sont pas inventés).
//
// Dessin, quand la caméra suit une étoile qui a des planètes et s'en approche :
//  - orbite : ellipse képlérienne de demi-grand axe, excentricité et argument du périastre mesurés ; inclinaison sur le ciel
//    mesurée quand elle l'est, sinon 60° [supposé : valeur médiane pour des orbites orientées au hasard] ; orientation du nœud
//    sur le ciel inconnue pour presque toutes : 0 [supposé] ;
//  - place sur l'orbite : période mesurée et date du passage devant l'étoile (transit) quand elle est mesurée ; sinon départ
//    arbitraire [supposé] ;
//  - repères : la planète est un point d'éclat fixé (sa vraie lumière renvoyée est des millions de fois plus faible que son
//    étoile : on ne la verrait pas), l'orbite des points plus pâles. Le panneau donne les valeurs et leur statut.
// Les points sont relatifs à la caméra, calculés en double précision (une orbite de 0,05 UA autour d'une étoile à 4 al est
// bien plus petite que l'arrondi d'une position en simple précision).
#pragma once
#include <cmath>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "simulation.h"

namespace {

struct Exoplanet {
    std::string name, massKind, method;
    double aAu = NAN, e = NAN, inclDeg = NAN, periodDays = NAN, radiusEarth = NAN, massEarth = NAN, omegaDeg = NAN, transitJd = NAN;
    int year = 0;
};

inline double exoNumber(const std::string& s) { return s.empty() ? NAN : std::atof(s.c_str()); }

struct Exoplanets {
    std::map<int64_t, std::vector<Exoplanet>> byStar;
    static constexpr uint32_t kOrbitPoints = 160, kMax = 4096;
    Buffer vb[StarRenderer::kCols];
    float* cols[StarRenderer::kCols] = {};
    uint32_t count = 0;
    bool gpu = false;

    bool load(const std::string& path) {
        std::ifstream f(path);
        if (!f) return false;
        for (std::string line; std::getline(f, line);) {
            if (line.empty() || line[0] == '#') continue;
            std::vector<std::string> c;
            std::stringstream ss(line);
            for (std::string x; std::getline(ss, x, '\t');) c.push_back(x);
            c.resize(13);
            Exoplanet p;
            p.name = c[1];
            p.aAu = exoNumber(c[2]);
            p.e = exoNumber(c[3]);
            p.inclDeg = exoNumber(c[4]);
            p.periodDays = exoNumber(c[5]);
            p.radiusEarth = exoNumber(c[6]);
            p.massEarth = exoNumber(c[7]);
            p.massKind = c[8];
            p.omegaDeg = exoNumber(c[9]);
            p.transitJd = exoNumber(c[10]);
            p.method = c[11];
            p.year = std::atoi(c[12].c_str());
            byStar[std::strtoll(c[0].c_str(), nullptr, 10)].push_back(p);
        }
        return !byStar.empty();
    }

    // Doubles (rang Gaia -> rang du catalogue principal, doublons.h) : leurs planètes passent à l'étoile du catalogue principal.
    void mergeDoubles(const std::unordered_map<int64_t, int64_t>& doubles) {
        for (const auto& [g, m] : doubles) {
            const auto it = byStar.find(g);
            if (it == byStar.end()) continue;
            auto& dst = byStar[m];
            dst.insert(dst.end(), it->second.begin(), it->second.end());
            byStar.erase(g);
        }
    }

    const std::vector<Exoplanet>* of(const Sim& sim, int body) const {
        if (body < 0) return nullptr;
        const Body& b = sim.bodies[static_cast<size_t>(body)];
        if (b.kind != Kind::Star) return nullptr;
        const auto it = byStar.find(b.star);
        return it == byStar.end() ? nullptr : &it->second;
    }
    static double largestOrbitLy(const std::vector<Exoplanet>& ps) {
        double a = 0;
        for (const Exoplanet& p : ps)
            if (std::isfinite(p.aAu)) a = std::max(a, p.aAu);
        return a * kAuInLy;
    }

    void create(const Gpu& g) {
        for (int i = 0; i < StarRenderer::kCols; ++i) {
            vb[i] = createBuffer(g, kMax * 4ull, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
            void* p = nullptr;
            check(vkMapMemory(g.dev, vb[i].mem, 0, kMax * 4ull, 0, &p), "tampon des planètes des autres étoiles");
            cols[i] = static_cast<float*>(p);
        }
        gpu = true;
    }

    // Place (relative à l'étoile, années-lumière, repère de l'appli) de la planète p à la date (jours juliens) ; la variante
    // « anomalie » sert à tracer l'orbite.
    static Vec3 placeAt(const Exoplanet& p, const Vec3& los, const Vec3& east, const Vec3& north, double trueAnomaly) {
        const double e = std::isfinite(p.e) ? std::clamp(p.e, 0.0, 0.99) : 0.0;
        const double w = (std::isfinite(p.omegaDeg) ? p.omegaDeg : 90.0) * kPi / 180.0;
        const double inc = (std::isfinite(p.inclDeg) ? p.inclDeg : 60.0) * kPi / 180.0;
        const double r = p.aAu * (1 - e * e) / (1 + e * std::cos(trueAnomaly)) * kAuInLy;
        const double u = w + trueAnomaly;      // argument de latitude, nœud ascendant sur l'axe nord (Ω = 0, supposé)
        // Repère du ciel : X = nord, Y = est, Z = vers l'observateur (-los) ; formules des orbites visuelles.
        const double X = r * std::cos(u), Y = r * std::sin(u) * std::cos(inc), Z = r * std::sin(u) * std::sin(inc);
        return {X * north.x + Y * east.x - Z * los.x, X * north.y + Y * east.y - Z * los.y, X * north.z + Y * east.z - Z * los.z};
    }
    static double trueAnomalyAt(const Exoplanet& p, double jd) {
        const double e = std::isfinite(p.e) ? std::clamp(p.e, 0.0, 0.99) : 0.0;
        const double w = (std::isfinite(p.omegaDeg) ? p.omegaDeg : 90.0) * kPi / 180.0;
        // Au transit, la planète passe devant l'étoile : anomalie vraie f = 90° - ω (Z maximal vers l'observateur).
        double M0 = 0, t0 = 2451545.0;
        if (std::isfinite(p.transitJd)) {
            const double f = kPi / 2 - w, E = 2 * std::atan(std::sqrt((1 - e) / (1 + e)) * std::tan(f / 2));
            M0 = E - e * std::sin(E);
            t0 = p.transitJd;
        }
        double M = std::fmod(M0 + 2 * kPi * (jd - t0) / p.periodDays, 2 * kPi);
        double E = M;
        for (int k = 0; k < 30; ++k) E -= (E - e * std::sin(E) - M) / (1 - e * std::cos(E));
        return 2 * std::atan2(std::sqrt(1 + e) * std::sin(E / 2), std::sqrt(1 - e) * std::cos(E / 2));
    }

    void update(const Sim& sim, const Camera& cam) {
        count = 0;
        const auto* ps = gpu ? of(sim, sim.focus) : nullptr;
        if (!ps || !sim.visible(sim.focus)) return;
        const Vec3 c = sim.position(sim.focus), rel{c.x - cam.pos.x, c.y - cam.pos.y, c.z - cam.pos.z};
        const double d = std::sqrt(dot(rel, rel)), amax = largestOrbitLy(*ps);
        if (amax <= 0 || d > 300.0 * amax) return;
        const double eps = 23.4392911 * kPi / 180.0;
        const Vec3 pole{0.0, -std::sin(eps), std::cos(eps)};
        const double dc = std::sqrt(dot(c, c));
        const Vec3 los{c.x / dc, c.y / dc, c.z / dc};
        const Vec3 east = unit(cross(pole, los)), north = cross(los, east);
        const double jd = 2451545.0 + sim.years * 365.25;
        const auto put = [&](const Vec3& q, double appMag, const std::array<uint8_t, 4>& col) {
            if (count >= kMax) return;
            const Vec3 p{rel.x + q.x, rel.y + q.y, rel.z + q.z};
            const double dp = std::max(std::sqrt(dot(p, p)), 1e-15);
            cols[0][count] = static_cast<float>(p.x);
            cols[1][count] = static_cast<float>(p.y);
            cols[2][count] = static_cast<float>(p.z);
            cols[3][count] = static_cast<float>(appMag - 5.0 * std::log10(dp / 3.2615638) + 5.0);
            std::memcpy(&cols[4][count], col.data(), 4);
            cols[5][count] = cols[6][count] = cols[7][count] = 0;
            ++count;
        };
        const auto orbitCol = colorOfTemperature(9000.0), planetCol = colorOfTemperature(6500.0);
        for (const Exoplanet& p : *ps) {
            if (!std::isfinite(p.aAu) || p.aAu <= 0) continue;
            for (uint32_t k = 0; k < kOrbitPoints; ++k) put(placeAt(p, los, east, north, 2 * kPi * k / kOrbitPoints), 3.5, orbitCol);
            if (std::isfinite(p.periodDays) && p.periodDays > 0) put(placeAt(p, los, east, north, trueAnomalyAt(p, jd)), -1.0, planetCol);
        }
    }

    void draw(VkCommandBuffer cmd, const StarRenderer& sr, PushConstants pc, uint32_t w, uint32_t h) const {
        if (!count) return;
        for (int a = 0; a < 3; ++a) pc.camHi[a] = pc.camLo[a] = 0.0f;
        pc.par[2] = 0.0f;
        sr.bind(cmd, pc, w, h);
        VkBuffer bufs[StarRenderer::kCols];
        VkDeviceSize offs[StarRenderer::kCols] = {};
        for (int i = 0; i < StarRenderer::kCols; ++i) bufs[i] = vb[i].buf;
        vkCmdBindVertexBuffers(cmd, 0, StarRenderer::kCols, bufs, offs);
        vkCmdDraw(cmd, count, 1, 0, 0);
    }

    void release(const Gpu& g) {
        if (!gpu) return;
        for (auto& b : vb) {
            vkUnmapMemory(g.dev, b.mem);
            destroy(g, b);
        }
    }
};

}  // namespace
