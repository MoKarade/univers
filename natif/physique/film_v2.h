// Appli PC « Univers », bibliothèque univers_physique : lecteur du FILM VERSION 2 du Groupe local.
//
// Le film est écrit par pipeline/fusion/rencontre.py (mode « futur ») : ce sont les étoiles visibles d'aujourd'hui
// (docs/contrat-etoiles-visibles.md) emportées par le calcul unique des cinq galaxies, dans le même ordre à toutes les
// dates. Il n'y a donc qu'une population : l'image de t = 0 est celle que l'appli montre aujourd'hui.
//
// Fichiers du dossier :
//   film_index.bin : « UNIVFLM2 », nombre d'images (u32), nombre de galaxies (u32), étoiles visibles par galaxie (u64 chacune),
//                    puis par image : date en Ga (f64), centre de chaque galaxie relatif à la Voie lactée (3 f64, kpc),
//                    vitesse de chaque centre (3 f64, km/s), écart d'énergie (f64) ;
//   img_NNNNN.f16  : pour chaque étoile visible, galaxie après galaxie, sa position RELATIVE AU CENTRE DE SA GALAXIE
//                    D'ORIGINE, trois nombres à virgule sur 16 bits (kpc).
// Repère : phys::galaxie (galaxie_orbites.h). Temps : Ga, 0 = aujourd'hui. Hors du film : false, rien n'est inventé.
// Entre deux images : une courbe qui passe par les quatre images voisines (Catmull-Rom), jamais une ligne droite ; pour
// les centres, une courbe de Hermite avec leurs vitesses.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <list>
#include <span>
#include <string>
#include <vector>

#include "phys.h"

namespace phys::film {

// Nombre à virgule sur 16 bits (IEEE 754 binary16) -> float.
inline float demiVersFloat(uint16_t h) {
    const uint32_t s = (h & 0x8000u) << 16, e = (h >> 10) & 0x1Fu, m = h & 0x3FFu;
    uint32_t bits;
    if (e == 0) {
        if (m == 0) bits = s;
        else {      // dénormalisé
            int k = 0; uint32_t mm = m;
            while (!(mm & 0x400u)) { mm <<= 1; ++k; }
            bits = s | ((uint32_t)(127 - 15 - k) << 23) | ((mm & 0x3FFu) << 13);
        }
    } else if (e == 31) bits = s | 0x7F800000u | (m << 13);
    else bits = s | ((e + 112u) << 23) | (m << 13);
    float f; std::memcpy(&f, &bits, 4); return f;
}

class FilmV2 {
public:
    static constexpr double kKpcGaEnKms = 1.0 / 1.0227121650456;

    bool charger(const std::string& dossier) {
        dossier_ = dossier; cache_.clear();
        std::vector<char> b; if (!lire(dossier + "/film_index.bin", b) || b.size() < 16 || std::memcmp(b.data(), "UNIVFLM2", 8) != 0) return false;
        uint32_t n, g; std::memcpy(&n, b.data() + 8, 4); std::memcpy(&g, b.data() + 12, 4);
        const size_t tete = 16 + 8ull * g, parImage = 8 + 48ull * g + 8;
        if (g < 1 || n < 2 || b.size() < tete + parImage * n) return false;
        n_ = (int)n; g_ = (int)g; etoiles_.resize(g); debut_.assign(g + 1, 0);
        std::memcpy(etoiles_.data(), b.data() + 16, 8ull * g);
        for (uint32_t k = 0; k < g; ++k) debut_[k + 1] = debut_[k] + etoiles_[k];
        t_.resize(n); c_.resize((size_t)n * g * 3); v_.resize((size_t)n * g * 3); e_.resize(n);
        for (uint32_t i = 0; i < n; ++i) {
            const char* p = b.data() + tete + parImage * i;
            std::memcpy(&t_[i], p, 8); std::memcpy(&c_[(size_t)i * g * 3], p + 8, 24ull * g); std::memcpy(&v_[(size_t)i * g * 3], p + 8 + 24ull * g, 24ull * g);
            std::memcpy(&e_[i], p + 8 + 48ull * g, 8);
        }
        return true;
    }
    int images() const { return n_; }
    int galaxies() const { return g_; }
    uint64_t etoiles(int g) const { return etoiles_[(size_t)g]; }
    uint64_t total() const { return debut_.empty() ? 0 : debut_.back(); }
    double date(int i) const { return t_[(size_t)i]; }
    double debutGa() const { return n_ ? t_.front() : 0; }
    double finGa() const { return n_ ? t_.back() : 0; }
    double ecartEnergie(int i) const { return e_[(size_t)i]; }

    // Centre de la galaxie g relatif à la Voie lactée (kpc) à tGa ; false hors du film.
    bool centre(int g, double tGa, Vec3& out) const {
        int i; double u; if (!place(tGa, i, u)) return false;
        const double h = (t_[(size_t)i + 1] - t_[(size_t)i]) / kKpcGaEnKms;      // durée entre les deux images, en kpc/(km/s)
        const double h00 = 2 * u * u * u - 3 * u * u + 1, h10 = (u * u * u - 2 * u * u + u) * h, h01 = -2 * u * u * u + 3 * u * u, h11 = (u * u * u - u * u) * h;
        const double* a = &c_[((size_t)i * g_ + g) * 3]; const double* b = &c_[((size_t)(i + 1) * g_ + g) * 3];
        const double* va = &v_[((size_t)i * g_ + g) * 3]; const double* vb = &v_[((size_t)(i + 1) * g_ + g) * 3];
        out = {h00 * a[0] + h10 * va[0] + h01 * b[0] + h11 * vb[0], h00 * a[1] + h10 * va[1] + h01 * b[1] + h11 * vb[1], h00 * a[2] + h10 * va[2] + h01 * b[2] + h11 * vb[2]};
        return true;
    }

    // Positions (x, y, z en kpc, relatives au centre de la galaxie g) de ses étoiles visibles à tGa, dans xyz
    // (au moins 3 x etoiles(g) valeurs). premier, nombre : pour n'en lire qu'une partie. false hors du film ou image absente.
    bool positions(int g, double tGa, std::span<float> xyz, uint64_t premier = 0, uint64_t nombre = UINT64_MAX) {
        int i; double u; if (!place(tGa, i, u)) return false;
        nombre = std::min(nombre, etoiles_[(size_t)g] - std::min(premier, etoiles_[(size_t)g]));
        if (xyz.size() < 3 * nombre) return false;
        const int k[4] = {std::max(i - 1, 0), i, i + 1, std::min(i + 2, n_ - 1)};
        const uint16_t* p[4];
        for (int j = 0; j < 4; ++j) { p[j] = image(k[j]); if (!p[j]) return false; }
        const double u2 = u * u, u3 = u2 * u;      // Catmull-Rom
        const float w0 = (float)(0.5 * (-u + 2 * u2 - u3)), w1 = (float)(0.5 * (2 - 5 * u2 + 3 * u3)), w2 = (float)(0.5 * (u + 4 * u2 - 3 * u3)), w3 = (float)(0.5 * (-u2 + u3));
        const size_t o = (size_t)(debut_[(size_t)g] + premier) * 3;
        for (size_t c = 0; c < 3 * nombre; ++c)
            xyz[c] = w0 * demiVersFloat(p[0][o + c]) + w1 * demiVersFloat(p[1][o + c]) + w2 * demiVersFloat(p[2][o + c]) + w3 * demiVersFloat(p[3][o + c]);
        return true;
    }

    // Image brute i (3 x total() nombres sur 16 bits), gardée en mémoire avec au plus kImagesGardees autres ; nul si absente.
    const uint16_t* image(int i) {
        for (auto it = cache_.begin(); it != cache_.end(); ++it)
            if (it->first == i) { cache_.splice(cache_.begin(), cache_, it); return cache_.front().second.data(); }
        char nom[32]; std::snprintf(nom, sizeof(nom), "/img_%05d.f16", i);
        std::vector<char> b; if (!lire(dossier_ + nom, b) || b.size() != total() * 6) return nullptr;
        std::vector<uint16_t> v(total() * 3); std::memcpy(v.data(), b.data(), b.size());
        cache_.emplace_front(i, std::move(v));
        if (cache_.size() > kImagesGardees) cache_.pop_back();
        return cache_.front().second.data();
    }
    static constexpr size_t kImagesGardees = 6;      // 51 Mo chacune pour 8,5 millions d'étoiles

private:
    std::string dossier_; int n_ = 0, g_ = 0;
    std::vector<uint64_t> etoiles_, debut_; std::vector<double> t_, c_, v_, e_;
    std::list<std::pair<int, std::vector<uint16_t>>> cache_;

    bool place(double tGa, int& i, double& u) const {
        if (n_ < 2 || !(tGa >= t_.front() && tGa <= t_.back())) return false;
        i = (int)(std::upper_bound(t_.begin(), t_.end(), tGa) - t_.begin()) - 1; i = std::clamp(i, 0, n_ - 2);
        u = (tGa - t_[(size_t)i]) / (t_[(size_t)i + 1] - t_[(size_t)i]); return true;
    }
    static bool lire(const std::string& p, std::vector<char>& b) {
        FILE* f = std::fopen(p.c_str(), "rb"); if (!f) return false; std::fseek(f, 0, SEEK_END); const long long n = _ftelli64(f); std::fseek(f, 0, SEEK_SET);
        b.resize((size_t)n); const bool ok = std::fread(b.data(), 1, (size_t)n, f) == (size_t)n; std::fclose(f); return ok;
    }
};

}  // namespace phys::film
