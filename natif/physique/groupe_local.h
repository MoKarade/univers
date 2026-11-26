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
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <limits>
#include <span>
#include <string>
#include <vector>

#include "phys.h"

namespace phys::fusion {

enum Galaxie { kVoieLactee = 0, kAndromede = 1, kTriangle = 2, kGrandNuage = 3 };

class Rejeu {
public:
    // Nom de fichier simple (un seul segment, sans séparateur ni « .. » ni « : ») : empêche toute lecture hors du dossier.
    static bool nomValide(const char* nom) {
        if (!nom || !nom[0]) return false;
        if (std::strcmp(nom, ".") == 0 || std::strcmp(nom, "..") == 0) return false;
        for (const unsigned char* p = reinterpret_cast<const unsigned char*>(nom); *p; ++p) {
            if (*p < 0x20 || *p == '/' || *p == '\\' || *p == ':') return false;
        }
        return true;
    }

    // Charge fusion_centres.bin et les images du même dossier (dossier vide : les images ne sont pas chargées).
    bool charger(const std::string& centres, const std::string& dossierImages) {
        std::vector<char> b; if (!lire(centres, b) || b.size() < 12 * 8) return false;
        double h[12]; std::memcpy(h, b.data(), sizeof(h));
        for (double v : h) if (!std::isfinite(v)) return false;
        if (h[1] < 2.0 || h[1] > 1e6 || h[2] <= 0.0 || h[4] < 1.0 || h[4] > 1e5 || h[5] <= 0.0) return false;
        const long n = static_cast<long>(h[1]);
        const int T = static_cast<int>(h[4]);
        int nGal[4] = {};
        int64_t nsTot = 0;
        for (int k = 0; k < 4; k++) {
            if (h[8 + k] < 0.0 || h[8 + k] > 1e8) return false;
            nGal[k] = static_cast<int>(h[8 + k]);
            nsTot += nGal[k];
        }
        if (nsTot < 0 || nsTot > 200000000LL) return false;
        const size_t o0 = 12 * 8;
        const size_t nc = static_cast<size_t>(n) * 12, nt = static_cast<size_t>(n) * static_cast<size_t>(T) * 3;
        if (nc > (b.size() - o0) / 8 || nt > (b.size() - o0) / 8 - nc || b.size() < o0 + (nc + nt + 1) * 8) return false;
        size_t o = o0;
        std::vector<double> cTmp(nc), tTmp(nt);
        std::memcpy(cTmp.data(), b.data() + o, nc * 8); o += nc * 8;
        std::memcpy(tTmp.data(), b.data() + o, nt * 8); o += nt * 8;
        double nfD = 0; std::memcpy(&nfD, b.data() + o, 8); o += 8;
        if (!std::isfinite(nfD) || nfD < 0.0 || nfD > 1e5) return false;
        const int nf = static_cast<int>(nfD);
        if (static_cast<size_t>(nf) > (b.size() - o) / 24) return false;

        std::vector<int16_t> imgTmp;
        if (!dossierImages.empty()) {
            if (nf == 0 || nsTot == 0) return false;
            const size_t ns = static_cast<size_t>(nsTot);
            if (static_cast<size_t>(n) > (512ULL * 1024 * 1024) / (ns * 6)) return false;
            // Valide tous les descripteurs et la taille des fichiers sur disque avant toute réservation mémoire.
            struct Descr { std::string chemin; size_t k; };
            std::vector<Descr> desc; desc.reserve(static_cast<size_t>(nf));
            size_t totalImages = 0;
            for (int f = 0; f < nf; f++) {
                char nom[17] = {}; std::memcpy(nom, b.data() + o, 16);
                double kD = 0; std::memcpy(&kD, b.data() + o + 16, 8); o += 24;
                if (!nomValide(nom) || !std::isfinite(kD) || kD < 1.0 || kD > static_cast<double>(n)) return false;
                const size_t k = static_cast<size_t>(kD);
                if (k > static_cast<size_t>(n) - totalImages) return false;
                totalImages += k;
                const std::string chemin = dossierImages + "/" + nom;
                std::error_code ec;
                if (!std::filesystem::is_regular_file(chemin, ec)) return false;
                const auto fsz = std::filesystem::file_size(chemin, ec);
                if (ec || fsz != k * ns * 6) return false;
                desc.push_back({chemin, k});
            }
            if (totalImages != static_cast<size_t>(n)) return false;
            imgTmp.reserve(static_cast<size_t>(n) * ns * 3);
            for (const auto& d : desc) {
                std::vector<char> kf; if (!lire(d.chemin, kf) || kf.size() != d.k * ns * 6) return false;
                const int16_t* p = reinterpret_cast<const int16_t*>(kf.data());
                imgTmp.insert(imgTmp.end(), p, p + d.k * ns * 3);
            }
            if (imgTmp.size() != static_cast<size_t>(n) * ns * 3) return false;
        }
        n_ = n; dt_ = h[2]; T_ = T; q_ = h[5]; fusionGa_ = h[6]; derive_ = h[7];
        for (int k = 0; k < 4; k++) nGal_[k] = nGal[k];
        ns_ = static_cast<int>(nsTot);
        centres_ = std::move(cTmp);
        traceurs_ = std::move(tTmp);
        images_ = std::move(imgTmp);
        return true;
    }
    double finGa() const { return (n_ - 1) * dt_; }
    double fusionGa() const { return fusionGa_; }
    double deriveEnergie() const { return derive_; }
    int etoiles(int g) const { return nGal_[g]; }
    int nombreEtoiles() const { return ns_; }
    int nombreTraceurs() const { return T_ - 1; }      // sans le Soleil

    // Centre de la galaxie g relatif au centre de la Voie lactée (kpc) à tGa ; false hors du calcul.
    bool centre(int g, double tGa, Vec3& out) const {
        if (g < 0 || g >= 4) return false;
        double a[3], m[3]; if (!lerp(centres_, 4, g, tGa, a) || !lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        out = {a[0] - m[0], a[1] - m[1], a[2] - m[2]}; return true;
    }
    // Traceur k (0 = première naine de conditions.json, Triangle exclu) relatif au centre de la Voie lactée.
    bool traceur(int k, double tGa, Vec3& out) const {
        if (k < 0 || k + 1 >= T_) return false;
        double a[3], m[3]; if (!lerp(traceurs_, T_, k + 1, tGa, a) || !lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        out = {a[0] - m[0], a[1] - m[1], a[2] - m[2]}; return true;
    }
    // Étoiles affichées (ordre : Voie lactée, Andromède, Triangle, Grand Nuage) relatives au centre de la Voie lactée.
    bool etoilesA(double tGa, std::span<Vec3> out) const {
        if (images_.empty() || out.size() < static_cast<size_t>(ns_) || !std::isfinite(tGa) || n_ < 2 || dt_ <= 0.0) return false;
        const double maxX = static_cast<double>(n_ - 1);
        double x = tGa / dt_;
        if (!(x >= 0.0 && x <= maxX + 1e-9)) return false;
        if (x > maxX) x = maxX;
        const long k = std::min(static_cast<long>(x), n_ - 2); const double f = x - k; double m[3];
        if (!lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        const int16_t* a = &images_[static_cast<size_t>(k) * ns_ * 3]; const int16_t* b = a + static_cast<size_t>(ns_) * 3;
        for (int i = 0; i < ns_; i++) out[i] = {(a[3 * i] + (b[3 * i] - a[3 * i]) * f) * q_ - m[0], (a[3 * i + 1] + (b[3 * i + 1] - a[3 * i + 1]) * f) * q_ - m[1], (a[3 * i + 2] + (b[3 * i + 2] - a[3 * i + 2]) * f) * q_ - m[2]};
        return true;
    }

private:
    long n_ = 0; int T_ = 0, ns_ = 0, nGal_[4] = {}; double dt_ = 0, q_ = 0, fusionGa_ = 0, derive_ = 0;
    std::vector<double> centres_, traceurs_;
    std::vector<int16_t> images_;
    static bool lire(const std::string& p, std::vector<char>& b) {
        std::error_code ec;
        if (!std::filesystem::is_regular_file(p, ec)) return false;
        const auto sz = std::filesystem::file_size(p, ec);
        if (ec || sz > 512ULL * 1024 * 1024) return false;
        FILE* f = std::fopen(p.c_str(), "rb"); if (!f) return false;
        b.resize(static_cast<size_t>(sz));
        const bool ok = sz == 0 || std::fread(b.data(), 1, static_cast<size_t>(sz), f) == static_cast<size_t>(sz);
        std::fclose(f); return ok;
    }
    bool lerp(const std::vector<double>& A, int stride, int k, double t, double out[3]) const {
        if (n_ < 2 || dt_ <= 0.0 || !std::isfinite(t)) return false;
        const double maxX = static_cast<double>(n_ - 1);
        double x = t / dt_;
        if (!(x >= 0.0 && x <= maxX + 1e-9)) return false;
        if (x > maxX) x = maxX;
        const long i = std::min(static_cast<long>(x), n_ - 2); const double f = x - i; const double* a = &A[(static_cast<size_t>(i) * stride + k) * 3]; const double* b = &A[(static_cast<size_t>(i + 1) * stride + k) * 3];
        for (int c = 0; c < 3; c++) out[c] = a[c] + (b[c] - a[c]) * f;
        return true;
    }
};

}  // namespace phys::fusion
