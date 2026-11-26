// Appli PC « Univers », bibliothèque univers_physique : rejeu du calcul complet de la fusion avec Andromède (côté données).
//
// Source : pipeline/fusion/calcul.py (300 000 particules de la Voie lactée, d'Andromède, du Triangle et du Grand Nuage qui
// s'attirent toutes, falcON ; tâche GitHub 43119915874 : fusion à 5,44 Ga, dérive d'énergie 0,11 %). Fichiers :
// fusion_centres.bin (pipeline/natif/fusion_bin.py) et les images kf_NNN.bin (étoiles en entiers 16 bits, pas 0,025 kpc,
// relatives au centre de masse total). Le futur calcul plus fin de l'appli (3 millions de particules) peut écrire les
// mêmes fichiers : rien ne change ici.
// Repère : celui de la page (galactocentrique, kpc), positions rendues RELATIVES AU CENTRE DE LA VOIE LACTÉE de la même date.
// Temps : Ga depuis aujourd'hui, de 0 à la dernière image ; ailleurs, false. Entre deux images (20 Ma), ligne droite.
// Le traceur Soleil du calcul n'est pas fiable (le disque modèle forme une barre et il migre vers le centre) : non fourni.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <limits>
#include <new>
#include <span>
#include <string>
#include <utility>
#include <vector>

#include "phys.h"

namespace phys::fusion {

enum Galaxie { kVoieLactee = 0, kAndromede = 1, kTriangle = 2, kGrandNuage = 3 };

class Rejeu {
public:
    // Charge fusion_centres.bin et les images du même dossier (dossier vide : les images ne sont pas chargées).
    bool charger(const std::string& centres, const std::string& dossierImages) {
        reset();
        std::vector<uint8_t> b;
        if (!lire(centres, b) || b.size() < 12 * sizeof(double)) return false;

        double h[12];
        std::memcpy(h, b.data(), sizeof(h));
        for (size_t i = 0; i < 12; ++i) {
            if (i == 6) {
                if (std::isinf(h[i])) return false;  // fusion_ga peut valoir NaN s'il n'y a pas de fusion
            } else if (!std::isfinite(h[i])) {
                return false;
            }
        }
        auto validInt = [](double v, double lo, double hi) {
            return v >= lo && v <= hi && std::floor(v) == v;
        };
        if (!validInt(h[1], 2.0, 1e7) || !(h[2] > 0.0) || h[3] != 4.0 || !validInt(h[4], 1.0, 1e6) || !(h[5] > 0.0)) {
            return false;
        }
        int nGal[4] = {};
        const double maxGal = static_cast<double>(std::numeric_limits<int>::max() / 12);
        long long nsSum = 0;
        for (size_t k = 0; k < 4; ++k) {
            if (!validInt(h[8 + k], 0.0, maxGal)) return false;
            nGal[k] = static_cast<int>(h[8 + k]);
            nsSum += nGal[k];
        }
        if (nsSum < 0 || nsSum > std::numeric_limits<int>::max() / 3) return false;

        const long n = static_cast<long>(h[1]);
        const double dt = h[2];
        const int T = static_cast<int>(h[4]);
        const double q = h[5];
        const double fusionVal = h[6];
        const double derive = h[7];
        const int ns = static_cast<int>(nsSum);

        auto mulChecked = [](size_t a, size_t c, size_t& res) {
            if (a != 0 && c > std::numeric_limits<size_t>::max() / a) return false;
            res = a * c;
            return true;
        };
        auto addChecked = [](size_t a, size_t c, size_t& res) {
            if (c > std::numeric_limits<size_t>::max() - a) return false;
            res = a + c;
            return true;
        };

        size_t nc = 0, ntTmp = 0, nt = 0, ncBytes = 0, ntBytes = 0, minBytes = 0;
        if (!mulChecked(static_cast<size_t>(n), 12, nc) ||
            !mulChecked(static_cast<size_t>(n), static_cast<size_t>(T), ntTmp) ||
            !mulChecked(ntTmp, 3, nt) ||
            !mulChecked(nc, sizeof(double), ncBytes) ||
            !mulChecked(nt, sizeof(double), ntBytes) ||
            !addChecked(12 * sizeof(double), ncBytes, minBytes) ||
            !addChecked(minBytes, ntBytes, minBytes) ||
            !addChecked(minBytes, sizeof(double), minBytes) ||
            minBytes > b.size()) {
            return false;
        }

        size_t o = 12 * sizeof(double);
        try {
            centres_.resize(nc);
            if (ncBytes > 0) std::memcpy(centres_.data(), b.data() + o, ncBytes);
            o += ncBytes;

            traceurs_.resize(nt);
            if (ntBytes > 0) std::memcpy(traceurs_.data(), b.data() + o, ntBytes);
            o += ntBytes;
        } catch (const std::bad_alloc&) {
            reset();
            return false;
        }

        double nfRaw = 0.0;
        std::memcpy(&nfRaw, b.data() + o, sizeof(double));
        o += sizeof(double);
        if (!std::isfinite(nfRaw) || nfRaw < 0.0 || std::floor(nfRaw) != nfRaw || nfRaw > 1e7) {
            reset();
            return false;
        }
        const size_t nf = static_cast<size_t>(nfRaw);
        if (nf > (b.size() - o) / 24) {
            reset();
            return false;
        }

        n_ = n;
        dt_ = dt;
        T_ = T;
        q_ = q;
        fusionGa_ = fusionVal;
        derive_ = derive;
        for (size_t k = 0; k < 4; ++k) nGal_[k] = nGal[k];
        ns_ = ns;

        if (dossierImages.empty()) return true;

        size_t totalTmp = 0, totalI16 = 0, totalBytes = 0;
        if (!mulChecked(static_cast<size_t>(n_), static_cast<size_t>(ns_), totalTmp) ||
            !mulChecked(totalTmp, 3, totalI16) ||
            !mulChecked(totalI16, sizeof(int16_t), totalBytes) ||
            static_cast<uintmax_t>(totalBytes) > kMaxTotalImageBytes) {
            reset();
            return false;
        }
        if (nf == 0 || nf > static_cast<size_t>(n_)) {
            reset();
            return false;
        }

        struct KfEntry {
            std::string path;
            size_t countI16 = 0;
            size_t expectedBytes = 0;
        };
        std::vector<KfEntry> entries;
        try {
            entries.reserve(nf);
        } catch (const std::bad_alloc&) {
            reset();
            return false;
        }

        uint64_t sumFrames = 0;
        size_t sumBytes = 0;
        for (size_t f = 0; f < nf; ++f) {
            if (b.size() - o < 24) {
                reset();
                return false;
            }
            char nomRaw[16];
            std::memcpy(nomRaw, b.data() + o, 16);
            double kRaw = 0.0;
            std::memcpy(&kRaw, b.data() + o + 16, sizeof(double));
            o += 24;
            std::string nom;
            if (!nomValide(nomRaw, nom) || !std::isfinite(kRaw) || kRaw < 1.0 || std::floor(kRaw) != kRaw ||
                kRaw > static_cast<double>(n_)) {
                reset();
                return false;
            }
            const uint64_t frames = static_cast<uint64_t>(kRaw);
            if (frames > static_cast<uint64_t>(n_) - sumFrames) {
                reset();
                return false;
            }
            sumFrames += frames;
            size_t countTmp = 0, countI16 = 0, kfBytes = 0;
            if (!mulChecked(static_cast<size_t>(frames), static_cast<size_t>(ns_), countTmp) ||
                !mulChecked(countTmp, 3, countI16) ||
                !mulChecked(countI16, sizeof(int16_t), kfBytes) ||
                static_cast<uintmax_t>(kfBytes) > kMaxFileBytes ||
                !addChecked(sumBytes, kfBytes, sumBytes)) {
                reset();
                return false;
            }
            std::string fullPath = dossierImages + "/" + nom;
            std::error_code ec;
            if (!std::filesystem::is_regular_file(fullPath, ec) || ec) {
                reset();
                return false;
            }
            const uintmax_t fsz = std::filesystem::file_size(fullPath, ec);
            if (ec || fsz != static_cast<uintmax_t>(kfBytes)) {
                reset();
                return false;
            }
            entries.push_back({std::move(fullPath), countI16, kfBytes});
        }
        if (sumFrames != static_cast<uint64_t>(n_) || sumBytes != totalBytes) {
            reset();
            return false;
        }

        try {
            images_.clear();
            images_.reserve(totalI16);
        } catch (const std::bad_alloc&) {
            reset();
            return false;
        }

        for (const auto& entry : entries) {
            std::vector<uint8_t> kf;
            if (!lire(entry.path, kf, entry.expectedBytes) || kf.size() != entry.expectedBytes) {
                reset();
                return false;
            }
            const size_t prev = images_.size();
            images_.resize(prev + entry.countI16);
            if (entry.expectedBytes > 0) std::memcpy(images_.data() + prev, kf.data(), entry.expectedBytes);
        }
        if (images_.size() != totalI16) {
            reset();
            return false;
        }
        return true;
    }

    double finGa() const { return n_ >= 2 ? static_cast<double>(n_ - 1) * dt_ : 0.0; }
    double fusionGa() const { return fusionGa_; }
    double deriveEnergie() const { return derive_; }
    int etoiles(int g) const { return (g >= 0 && g < 4) ? nGal_[g] : 0; }
    int nombreEtoiles() const { return ns_; }
    int nombreTraceurs() const { return T_ > 0 ? T_ - 1 : 0; }  // sans le Soleil

    // Centre de la galaxie g relatif au centre de la Voie lactée (kpc) à tGa ; false hors du calcul.
    bool centre(int g, double tGa, Vec3& out) const {
        if (g < 0 || g >= 4) return false;
        double a[3], m[3];
        if (!lerp(centres_, 4, g, tGa, a) || !lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        out = {a[0] - m[0], a[1] - m[1], a[2] - m[2]};
        return true;
    }

    // Traceur k (0 = première naine de conditions.json, Triangle exclu) relatif au centre de la Voie lactée.
    bool traceur(int k, double tGa, Vec3& out) const {
        if (k < 0 || k + 1 >= T_) return false;
        double a[3], m[3];
        if (!lerp(traceurs_, T_, k + 1, tGa, a) || !lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        out = {a[0] - m[0], a[1] - m[1], a[2] - m[2]};
        return true;
    }

    // Étoiles affichées (ordre : Voie lactée, Andromède, Triangle, Grand Nuage) relatives au centre de la Voie lactée.
    bool etoilesA(double tGa, std::span<Vec3> out) const {
        if (n_ < 2 || ns_ <= 0 || !(dt_ > 0.0) || !std::isfinite(tGa) || tGa < 0.0 || tGa > finGa() ||
            images_.empty() || out.size() < static_cast<size_t>(ns_)) {
            return false;
        }
        const double x = std::clamp(tGa / dt_, 0.0, static_cast<double>(n_ - 1));
        double m[3];
        if (!lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        const size_t k = static_cast<size_t>(std::clamp(static_cast<long>(std::floor(x)), 0L, n_ - 2));
        const double f = x - static_cast<double>(k);
        const size_t uNs = static_cast<size_t>(ns_);
        const size_t stride = uNs * 3;
        if ((k + 2) * stride > images_.size()) return false;
        const int16_t* a = &images_[k * stride];
        const int16_t* b = a + stride;
        for (size_t i = 0; i < uNs; ++i) {
            out[i] = {(a[3 * i] + (b[3 * i] - a[3 * i]) * f) * q_ - m[0],
                      (a[3 * i + 1] + (b[3 * i + 1] - a[3 * i + 1]) * f) * q_ - m[1],
                      (a[3 * i + 2] + (b[3 * i + 2] - a[3 * i + 2]) * f) * q_ - m[2]};
        }
        return true;
    }

private:
    long n_ = 0;
    int T_ = 0, ns_ = 0, nGal_[4] = {};
    double dt_ = 0, q_ = 0, fusionGa_ = 0, derive_ = 0;
    std::vector<double> centres_, traceurs_;
    std::vector<int16_t> images_;

    void reset() {
        n_ = 0;
        T_ = 0;
        ns_ = 0;
        std::fill(std::begin(nGal_), std::end(nGal_), 0);
        dt_ = 0;
        q_ = 0;
        fusionGa_ = 0;
        derive_ = 0;
        centres_.clear();
        traceurs_.clear();
        images_.clear();
    }

    static constexpr uintmax_t kMaxFileBytes = 2ULL * 1024ULL * 1024ULL * 1024ULL;
    static constexpr uintmax_t kMaxTotalImageBytes = 16ULL * 1024ULL * 1024ULL * 1024ULL;

    static bool nomValide(const char raw[16], std::string& out) {
        out.clear();
        size_t len = 0;
        while (len < 16 && raw[len] != '\0') ++len;
        if (len == 0) return false;
        for (size_t i = len; i < 16; ++i) {
            if (raw[i] != '\0') return false;
        }
        for (size_t i = 0; i < len; ++i) {
            const unsigned char c = static_cast<unsigned char>(raw[i]);
            if (c < 0x20 || c >= 0x7F || c == '/' || c == '\\' || c == ':') return false;
        }
        out.assign(raw, len);
        return out != "." && out != "..";
    }

    static bool lire(const std::string& p, std::vector<uint8_t>& b, uintmax_t maxBytes = kMaxFileBytes) {
        b.clear();
        if (p.empty()) return false;
        std::error_code ec;
        if (!std::filesystem::is_regular_file(p, ec) || ec) return false;
        const uintmax_t fsz = std::filesystem::file_size(p, ec);
        if (ec || fsz > maxBytes || fsz > static_cast<uintmax_t>(std::numeric_limits<size_t>::max())) return false;
        FILE* f = std::fopen(p.c_str(), "rb");
        if (!f) return false;
        const size_t n = static_cast<size_t>(fsz);
        try {
            b.resize(n);
        } catch (const std::bad_alloc&) {
            std::fclose(f);
            b.clear();
            return false;
        }
        const bool readOk = (n == 0) || (std::fread(b.data(), 1, n, f) == n);
        std::fclose(f);
        if (!readOk) b.clear();
        return readOk;
    }

    bool lerp(const std::vector<double>& A, int stride, int k, double t, double out[3]) const {
        if (n_ < 2 || stride <= 0 || k < 0 || k >= stride || !(dt_ > 0.0) || !std::isfinite(t) || t < 0.0 ||
            t > finGa()) {
            return false;
        }
        const double x = std::clamp(t / dt_, 0.0, static_cast<double>(n_ - 1));
        const size_t i = static_cast<size_t>(std::clamp(static_cast<long>(std::floor(x)), 0L, n_ - 2));
        const double f = x - static_cast<double>(i);
        const size_t uStride = static_cast<size_t>(stride);
        const size_t uK = static_cast<size_t>(k);
        const size_t idx0 = (i * uStride + uK) * 3;
        const size_t idx1 = ((i + 1) * uStride + uK) * 3;
        if (idx1 + 3 > A.size()) return false;
        const double* a = &A[idx0];
        const double* b = &A[idx1];
        for (size_t c = 0; c < 3; ++c) {
            out[c] = a[c] + (b[c] - a[c]) * f;
        }
        return true;
    }
};

}  // namespace phys::fusion
