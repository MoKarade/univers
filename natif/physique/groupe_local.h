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
#include <cstdio>
#include <cstring>
#include <span>
#include <string>
#include <vector>

#include "phys.h"

namespace phys::fusion {

enum Galaxie { kVoieLactee = 0, kAndromede = 1, kTriangle = 2, kGrandNuage = 3 };

class Rejeu {
public:
    // Charge fusion_centres.bin et les images du même dossier (dossier vide : les images ne sont pas chargées).
    bool charger(const std::string& centres, const std::string& dossierImages) {
        std::vector<char> b; if (!lire(centres, b) || b.size() < 12 * 8) return false;
        const double* h = reinterpret_cast<const double*>(b.data());
        n_ = (long)h[1]; dt_ = h[2]; T_ = (int)h[4]; q_ = h[5]; fusionGa_ = h[6]; derive_ = h[7];
        for (int k = 0; k < 4; k++) nGal_[k] = (int)h[8 + k];
        size_t o = 12 * 8; const size_t nc = (size_t)n_ * 12, nt = (size_t)n_ * T_ * 3;
        if (b.size() < o + (nc + nt + 1) * 8) return false;
        centres_.assign(reinterpret_cast<const double*>(b.data() + o), reinterpret_cast<const double*>(b.data() + o) + nc); o += nc * 8;
        traceurs_.assign(reinterpret_cast<const double*>(b.data() + o), reinterpret_cast<const double*>(b.data() + o) + nt); o += nt * 8;
        double nf; std::memcpy(&nf, b.data() + o, 8); o += 8;
        ns_ = nGal_[0] + nGal_[1] + nGal_[2] + nGal_[3];
        if (dossierImages.empty()) return true;
        images_.clear(); images_.reserve((size_t)n_ * ns_ * 3);
        for (int f = 0; f < (int)nf; f++) {
            char nom[17] = {}; std::memcpy(nom, b.data() + o, 16); double k; std::memcpy(&k, b.data() + o + 16, 8); o += 24;
            std::vector<char> kf; if (!lire(dossierImages + "/" + nom, kf) || kf.size() != (size_t)k * ns_ * 6) return false;
            const int16_t* p = reinterpret_cast<const int16_t*>(kf.data()); images_.insert(images_.end(), p, p + (size_t)k * ns_ * 3);
        }
        return images_.size() == (size_t)n_ * ns_ * 3;
    }
    double finGa() const { return (n_ - 1) * dt_; }
    double fusionGa() const { return fusionGa_; }
    double deriveEnergie() const { return derive_; }
    int etoiles(int g) const { return nGal_[g]; }
    int nombreEtoiles() const { return ns_; }
    int nombreTraceurs() const { return T_ - 1; }      // sans le Soleil

    // Centre de la galaxie g relatif au centre de la Voie lactée (kpc) à tGa ; false hors du calcul.
    bool centre(int g, double tGa, Vec3& out) const {
        double a[3], m[3]; if (!lerp(centres_, 4, g, tGa, a) || !lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        out = {a[0] - m[0], a[1] - m[1], a[2] - m[2]}; return true;
    }
    // Traceur k (0 = première naine de conditions.json, Triangle exclu) relatif au centre de la Voie lactée.
    bool traceur(int k, double tGa, Vec3& out) const {
        double a[3], m[3]; if (!lerp(traceurs_, T_, k + 1, tGa, a) || !lerp(centres_, 4, kVoieLactee, tGa, m)) return false;
        out = {a[0] - m[0], a[1] - m[1], a[2] - m[2]}; return true;
    }
    // Étoiles affichées (ordre : Voie lactée, Andromède, Triangle, Grand Nuage) relatives au centre de la Voie lactée.
    bool etoilesA(double tGa, std::span<Vec3> out) const {
        if (images_.empty() || out.size() < (size_t)ns_) return false;
        const double x = tGa / dt_; if (!(x >= 0 && x <= n_ - 1)) return false;
        const long k = std::min((long)x, n_ - 2); const double f = x - k; double m[3]; lerp(centres_, 4, kVoieLactee, tGa, m);
        const int16_t* a = &images_[(size_t)k * ns_ * 3]; const int16_t* b = a + (size_t)ns_ * 3;
        for (int i = 0; i < ns_; i++) out[i] = {(a[3 * i] + (b[3 * i] - a[3 * i]) * f) * q_ - m[0], (a[3 * i + 1] + (b[3 * i + 1] - a[3 * i + 1]) * f) * q_ - m[1], (a[3 * i + 2] + (b[3 * i + 2] - a[3 * i + 2]) * f) * q_ - m[2]};
        return true;
    }

private:
    long n_ = 0; int T_ = 0, ns_ = 0, nGal_[4] = {}; double dt_ = 0, q_ = 0, fusionGa_ = 0, derive_ = 0;
    std::vector<double> centres_, traceurs_;
    std::vector<int16_t> images_;
    static bool lire(const std::string& p, std::vector<char>& b) {
        FILE* f = std::fopen(p.c_str(), "rb"); if (!f) return false; std::fseek(f, 0, SEEK_END); const long n = std::ftell(f); std::fseek(f, 0, SEEK_SET);
        b.resize(n); const bool ok = std::fread(b.data(), 1, n, f) == (size_t)n; std::fclose(f); return ok;
    }
    bool lerp(const std::vector<double>& A, int stride, int k, double t, double out[3]) const {
        const double x = t / dt_; if (n_ < 2 || !(x >= 0 && x <= n_ - 1)) return false;
        const long i = std::min((long)x, n_ - 2); const double f = x - i; const double* a = &A[((size_t)i * stride + k) * 3]; const double* b = &A[((size_t)(i + 1) * stride + k) * 3];
        for (int c = 0; c < 3; c++) out[c] = a[c] + (b[c] - a[c]) * f; return true;
    }
};

}  // namespace phys::fusion
