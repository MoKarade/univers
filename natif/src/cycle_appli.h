// Appli PC « Univers » : le cycle de vie des étoiles branché sur l'appli (Soleil et étoiles nommées). À chaque image :
// rayon, teinte et éclat de chaque étoile à la date montrée (cycle_etoile.h), et la matière autour d'elle (cycle_matiere.h)
// pour celles assez proches de la caméra. Dessin : spheres.h (l'étoile), cycle_nebuleuse.h (la matière), points du
// catalogue (StarRenderer, éclat et couleur réécrits pour ces seules étoiles).
//
// Aujourd'hui, rien ne change : l'étoile garde son rayon et son éclat mesurés (le modèle ne donne que le changement).
#pragma once
#include "cycle_matiere.h"
#include "simulation.h"

namespace {

class CycleAppli {
public:
    static constexpr double kProfilMaxAl = 3000.0;      // au-delà, la matière autour d'une étoile ne fait pas un pixel
    static constexpr float kCache = 60.0f;              // magnitude absolue d'une étoile absente (pas née, éteinte)

    struct Astre {
        int body = -1;
        cycle::Vie vie;
        std::vector<cycle::Paquet> paquets;
        cycle::Vu vu;
        cycle::Bilan bilan;
        cycle::Profil profil;
        bool profilOk = false;
        std::string sourceTeff;      // température publiée utilisée pour le placement (vide : tirée de B-V)
        float pointMag = 0, pointMag0 = 0;      // éclat du point dessiné (magnitude absolue V) ; celui du catalogue
        uint32_t pointRgba = 0, pointRgba0 = 0;
        float writtenMag = 0;      // ce qui est dans la colonne de la carte graphique
        uint32_t writtenRgba = 0;
    };
    cycle::Grille grille;
    std::vector<Astre> astres;
    std::vector<int> deBody;      // rang dans astres de chaque astre de la simulation, -1 sinon

    bool ready() const { return grille.ready && !astres.empty(); }

    void build(const std::string& path, Sim& sim, const std::string& publiees = "") {
        if (!grille.load(path)) return;
        // Températures publiées (etoiles_cycle.tsv) : numéro du catalogue -> Teff, source.
        std::vector<std::pair<int64_t, std::pair<double, std::string>>> teffs;
        if (!publiees.empty()) {
            std::ifstream f(publiees);
            for (std::string l; std::getline(f, l);) {
                if (l.empty() || l[0] == '#') continue;
                std::vector<std::string> c;
                size_t from = 0;
                for (size_t tab; (tab = l.find('	', from)) != std::string::npos; from = tab + 1) c.push_back(l.substr(from, tab - from));
                c.push_back(l.substr(from));
                if (c.size() >= 4 && std::atof(c[2].c_str()) > 0) teffs.push_back({std::strtoll(c[0].c_str(), nullptr, 10), {std::atof(c[2].c_str()), c[3]}});
            }
        }
        astres.clear();
        deBody.assign(sim.bodies.size(), -1);
        for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            if (b.kind != Kind::Sun && b.kind != Kind::Star) continue;
            if (b.kind == Kind::Star && (!sim.stars || b.star < 0)) continue;
            const double mag = b.kind == Kind::Sun ? kSunAbsMag : sim.stars->mag()[b.star];
            Astre a;
            a.body = i;
            double teff = 0;
            for (const auto& [idx, ts] : teffs)
                if (b.kind == Kind::Star && idx == b.star) { teff = ts.first; a.sourceTeff = ts.second; }
            a.vie = cycle::vieEtoile(grille, b.kind == Kind::Sun, mag, b.bv, teff);
            if (!a.vie.ok()) continue;
            a.paquets = cycle::paquets(a.vie);
            a.pointMag0 = static_cast<float>(mag);
            a.pointRgba0 = rgba(b.kind == Kind::Sun ? kSunBv : b.bv);
            a.pointMag = a.writtenMag = a.pointMag0;
            a.pointRgba = a.writtenRgba = a.pointRgba0;
            deBody[static_cast<size_t>(i)] = static_cast<int>(astres.size());
            astres.push_back(std::move(a));
        }
        sim.sunAlways = true;      // le Soleil reste montré à toute date, pour qu'on voie sa vie (sa place dans la Galaxie : voir le panneau)
    }

    const Astre* of(int body) const {
        if (body < 0 || static_cast<size_t>(body) >= deBody.size() || deBody[static_cast<size_t>(body)] < 0) return nullptr;
        return &astres[static_cast<size_t>(deBody[static_cast<size_t>(body)])];
    }

    static uint32_t rgba(double bv) {
        const auto c = colorOfBv(bv);
        return static_cast<uint32_t>(c[0]) | (static_cast<uint32_t>(c[1]) << 8) | (static_cast<uint32_t>(c[2]) << 16) | (static_cast<uint32_t>(c[3]) << 24);
    }

    // À chaque image, avant le dessin des sphères.
    void update(Sim& sim, const Camera& cam) {
        if (!ready()) return;
        const double dt = sim.years - kStartYears;
        for (Astre& a : astres) {
            Body& b = sim.bodies[static_cast<size_t>(a.body)];
            a.vu = cycle::vuA(a.vie, dt);
            const cycle::Etat& s = a.vu.modele;
            b.lifeOn = true;
            b.lifeRadiusKm = a.vu.rayonKm;
            b.lifeTeff = a.vu.teff;
            b.lifeBv = a.vu.bv;
            b.lifeAbsMag = a.vu.magV;
            b.lifeBlack = s.trouNoir;
            b.lifeMapped = a.vu.etoile;      // surface de l'étoile elle-même (le Soleil garde sa carte) ; reste : teinte unie
            // Point du catalogue : aujourd'hui exactement l'éclat mesuré ; sinon l'éclat calculé (absente : très faible).
            const bool today = std::fabs(dt) < 1e-6;
            a.pointMag = today ? a.pointMag0 : a.vu.magV < 90 ? static_cast<float>(a.vu.magV) : kCache;
            a.pointRgba = today ? a.pointRgba0 : rgba(a.vu.bv);
            a.profilOk = false;
            const bool shown = sim.visible(a.body);
            const Vec3 p = sim.position(a.body) - cam.pos;
            if (!shown || std::sqrt(dot(p, p)) > kProfilMaxAl) continue;
            const auto cs = cycle::couches(a.vie, a.paquets, a.vie.ageAujourdhui + dt, &a.bilan);
            if (cs.empty()) continue;
            const auto c = colorOfTemperature(s.teff > 0 ? s.teff : 5772.0);
            const float col[3] = {std::pow(c[0] / 255.0f, 2.2f), std::pow(c[1] / 255.0f, 2.2f), std::pow(c[2] / 255.0f, 2.2f)};
            a.profil = cycle::profil(cs, s, col);
            a.profilOk = a.profil.n > 0;
        }
    }

    // Pose « photo » (fenetre.cpp) : brillance moyenne, par unité d'exposition, de la nébuleuse la plus brillante à
    // l'écran (dans le rayon qui contient la moitié de sa lumière), quand son étoile est encore un point. Même échelle que
    // les points des étoiles (cycle_nebuleuse.h) ; 0 : aucune.
    double maxSurface(const Sim& sim, const Camera& cam, double pixel) const {
        double best = 0;
        for (const Astre& a : astres) {
            if (!a.profilOk || a.profil.lumiere <= 0) continue;
            const cycle::Profil& p = a.profil;
            double cum = 0, rDemi = p.r[p.n];
            for (int k = 0; k < p.n; ++k) {
                const double vk = 4.0 / 3.0 * cycle::kPi * (static_cast<double>(p.r[k + 1]) * p.r[k + 1] * p.r[k + 1] - static_cast<double>(p.r[k]) * p.r[k] * p.r[k]);
                cum += (p.rgb[k][0] + p.rgb[k][1] + p.rgb[k][2]) / 3.0 * vk;
                if (cum >= 0.5 * p.lumiere) { rDemi = p.r[k + 1]; break; }
            }
            const Vec3 c = sim.position(a.body) - cam.pos;
            const double dist = std::sqrt(dot(c, c));
            if (dist <= 0 || rDemi <= 0) continue;
            const double rPx = rDemi / dist / pixel, starPx = sim.bodies[static_cast<size_t>(a.body)].lifeRadiusKm / kLyInKm / dist / pixel;
            if (rPx < 3.0 || starPx > 1.5 || (dot(c, cam.fwd) <= 0 && dist > rDemi)) continue;
            const double surface = std::pow(10.0, -0.4 * 4.83) * 32.6156 * 32.6156 * pixel * pixel * 0.5 * p.lumiere / (cycle::kPi * rDemi * rDemi);
            best = std::max(best, surface);
        }
        return best;
    }

    // Réécrit l'éclat et la couleur des points de ces étoiles dans les colonnes du catalogue (avant la passe de dessin).
    // Seuls les mots qui changent partent à la carte graphique.
    void recordPoints(VkCommandBuffer cmd, const Sim& sim, StarRenderer& sr) {
        if (!ready()) return;
        bool any = false;
        for (Astre& a : astres) {
            const Body& b = sim.bodies[static_cast<size_t>(a.body)];
            const uint32_t idx = b.kind == Kind::Sun ? sr.count - 1 : static_cast<uint32_t>(b.star);
            if (idx >= sr.count || (b.kind != Kind::Sun && idx >= sr.count - 1)) continue;      // la dernière case est celle du Soleil
            if (a.pointMag == a.writtenMag && a.pointRgba == a.writtenRgba) continue;
            vkCmdUpdateBuffer(cmd, sr.vb[3].buf, 4ull * idx, 4, &a.pointMag);
            vkCmdUpdateBuffer(cmd, sr.vb[4].buf, 4ull * idx, 4, &a.pointRgba);
            a.writtenMag = a.pointMag;
            a.writtenRgba = a.pointRgba;
            any = true;
        }
        if (!any) return;
        VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        mb.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        mb.dstAccessMask = VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT | VK_ACCESS_SHADER_READ_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_VERTEX_INPUT_BIT | VK_PIPELINE_STAGE_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                             0, 1, &mb, 0, nullptr, 0, nullptr);
    }
};

}  // namespace
