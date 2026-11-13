// Appli PC « Univers » : centres de référence des galaxies du Groupe local (centres_reference.bin, pipeline/natif/centres_bin.py,
// depuis pipeline/fusion/resultats/centres_reference.npz de la PR 97).
//
// Une seule histoire calculée (galaxies indéformables : halos NFW, adoucissement 20 kpc, frottement de Chandrasekhar,
// énergie noire ; Sawala et al. 2025), de -3 à +10 milliards d'années, pas de 0,978 million d'années. Positions et vitesses
// relatives au centre de la Voie lactée, repère phys::galaxie (galaxie_orbites.h). Chaque galaxie se déplace en bloc le long
// de son centre ; entre deux dates, interpolation d'Hermite cubique avec les vitesses (erreur < 0,002 kpc annoncée à 5 Ma).
// Pas de déformation par les marées : c'est le rôle du film de la rencontre, quand il existera.
#pragma once
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "galaxie_orbites.h"

namespace {

class CentresReference {
public:
    enum Galaxie { kVoieLactee = 0, kAndromede = 1, kTriangle = 2, kGrandNuage = 3, kPetitNuage = 4 };
    bool ready = false;

    bool load(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        char head[64] = {};
        if (!f.read(head, 64) || std::memcmp(head, "UNIVCEN1", 8) != 0) return false;
        std::memcpy(&n_, head + 8, 4);
        std::memcpy(&g_, head + 12, 4);
        std::memcpy(&today_, head + 16, 4);
        std::memcpy(&t0_, head + 24, 8);
        std::memcpy(&dt_, head + 32, 8);
        if (n_ < 2 || g_ < 1 || dt_ <= 0) return false;
        pos_.resize(static_cast<size_t>(n_) * g_ * 3);
        vel_.resize(pos_.size());
        if (!f.read(reinterpret_cast<char*>(pos_.data()), static_cast<std::streamsize>(pos_.size() * 4))) return false;
        if (!f.read(reinterpret_cast<char*>(vel_.data()), static_cast<std::streamsize>(vel_.size() * 4))) return false;
        ready = true;
        return true;
    }

    double firstGa() const { return t0_; }
    double lastGa() const { return t0_ + dt_ * (n_ - 1); }

    // Centre de la galaxie k à tGa (milliards d'années depuis aujourd'hui), kpc relatifs au centre de la Voie lactée.
    // Rend false hors de la plage calculée.
    bool centre(int k, double tGa, phys::Vec3& out) const {
        if (!ready || k < 0 || static_cast<uint32_t>(k) >= g_ || tGa < firstGa() || tGa > lastGa()) return false;
        const double x = (tGa - t0_) / dt_;
        const long i = std::min(static_cast<long>(x), static_cast<long>(n_) - 2);
        const double s = x - static_cast<double>(i), s2 = s * s, s3 = s2 * s;
        const double h00 = 2 * s3 - 3 * s2 + 1, h10 = s3 - 2 * s2 + s, h01 = -2 * s3 + 3 * s2, h11 = s3 - s2;
        const double T = dt_ * phys::galaxie::kKmsKpcToRadGa;      // km/s × Ga -> kpc (même facteur que les orbites de l'appli)
        const float* a = &pos_[(static_cast<size_t>(i) * g_ + k) * 3];
        const float* b = &pos_[(static_cast<size_t>(i + 1) * g_ + k) * 3];
        const float* u = &vel_[(static_cast<size_t>(i) * g_ + k) * 3];
        const float* w = &vel_[(static_cast<size_t>(i + 1) * g_ + k) * 3];
        out = {h00 * a[0] + h10 * T * u[0] + h01 * b[0] + h11 * T * w[0], h00 * a[1] + h10 * T * u[1] + h01 * b[1] + h11 * T * w[1],
               h00 * a[2] + h10 * T * u[2] + h01 * b[2] + h11 * T * w[2]};
        return true;
    }

    // Rang dans le fichier pour un astre de l'appli (nom), -1 sinon. La Voie lactée reste à l'origine : pas de rang.
    static int indexOf(const std::string& name) {
        if (name == "Andromède (M31)") return kAndromede;
        if (name == "Galaxie du Triangle (M33)") return kTriangle;
        if (name == "Grand Nuage de Magellan") return kGrandNuage;
        if (name == "Petit Nuage de Magellan") return kPetitNuage;
        return -1;
    }

private:
    uint32_t n_ = 0, g_ = 0, today_ = 0;
    double t0_ = 0, dt_ = 0;
    std::vector<float> pos_, vel_;
};

}  // namespace
