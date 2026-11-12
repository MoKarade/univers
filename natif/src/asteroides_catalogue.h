// Appli PC « Univers » : le catalogue des astéroïdes côté processeur (asteroides.bin et asteroides_noms.txt), pour
// pouvoir en désigner un (clic ou recherche), le suivre et afficher sa fiche. Le dessin de tous les astéroïdes reste
// fait par la carte graphique (asteroides.h) ; ici la même équation de Kepler, en double précision, pour un seul.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace asteroides {

struct Catalogue {
    uint64_t n = 0;
    double epochJd = 0;
    std::vector<float> cols[10];      // Px, Py, Pz, Qx, Qy, Qz (UA), e, M0 (rad), n (rad/jour), H
    std::vector<std::string> names;   // « Nom~numéro » (nom vide : seulement un numéro ou une désignation)

    bool load(const std::string& binPath, const std::string& namesPath) {
        FILE* f = std::fopen(binPath.c_str(), "rb");
        if (!f) return false;
        char head[64];
        bool ok = std::fread(head, 1, 64, f) == 64 && std::memcmp(head, "UNIVAST1", 8) == 0;
        if (ok) {
            std::memcpy(&n, head + 8, 8);
            std::memcpy(&epochJd, head + 16, 8);
            const size_t column = (n * 4 + 63) / 64 * 64;
            for (int c = 0; ok && c < 10; ++c) {
                cols[c].resize(n);
                ok = std::fread(cols[c].data(), 4, n, f) == n && std::fseek(f, static_cast<long>(column - n * 4), SEEK_CUR) == 0;
            }
        }
        std::fclose(f);
        if (!ok) return false;
        std::ifstream nf(namesPath);
        for (std::string line; std::getline(nf, line);) names.push_back(line);
        names.resize(n);
        return true;
    }

    // Nom à l'écran, comme dans la page : « Albert (719) », ou « Astéroïde 2000 CM104 » sans nom propre.
    std::string label(size_t k) const {
        const std::string& t = names[k];
        const size_t cut = t.find('~');
        const std::string name = t.substr(0, cut), id = cut == std::string::npos ? "" : t.substr(cut + 1);
        if (name.empty()) return id.empty() ? "Astéroïde" : "Astéroïde " + id;
        return id.empty() ? name : name + " (" + id + ")";
    }
    double magnitudeH(size_t k) const { return cols[9][k]; }
    double semiMajorAxisAu(size_t k) const {      // n = k_Gauss / a^1,5
        return std::pow(0.01720209895 / static_cast<double>(cols[8][k]), 2.0 / 3.0);
    }
    double eccentricity(size_t k) const { return cols[6][k]; }
    double periodYears(size_t k) const { return 2.0 * 3.14159265358979323846 / static_cast<double>(cols[8][k]) / 365.25; }

    // Position par rapport au Soleil (UA, écliptique J2000) au jour julien jd : orbite mesurée, suivie sans l'attraction
    // des planètes (contrôle : moins de 100 000 km d'écart avec JPL Horizons après 154 jours).
    void position(size_t k, double jd, double out[3]) const {
        const double e = cols[6][k];
        double M = std::fmod(static_cast<double>(cols[7][k]) + static_cast<double>(cols[8][k]) * (jd - epochJd), 6.283185307179586);
        if (M < 0) M += 6.283185307179586;
        double E = M + e * std::sin(M) * (1.0 + e * std::cos(M));
        for (int i = 0; i < 20; ++i) {      // s'arrête dès que c'est exact : 3 ou 4 tours en général (1,58 million d'orbites au clic)
            const double dE = (E - e * std::sin(E) - M) / (1.0 - e * std::cos(E));
            E -= dE;
            if (std::fabs(dE) < 1e-13) break;
        }
        const double c = std::cos(E) - e, s = std::sin(E);
        for (int a = 0; a < 3; ++a) out[a] = static_cast<double>(cols[a][k]) * c + static_cast<double>(cols[3 + a][k]) * s;
    }

    // Les `max` premiers astéroïdes dont le nom ou le numéro contient le texte (sans tenir compte des majuscules).
    std::vector<int> search(const std::string& text, int max) const {
        std::vector<int> out;
        if (text.size() < 2) return out;
        std::string needle = text;
        for (char& ch : needle) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
        for (size_t k = 0; k < n && static_cast<int>(out.size()) < max; ++k) {
            std::string hay = names[k];
            for (char& ch : hay) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
            if (hay.find(needle) != std::string::npos) out.push_back(static_cast<int>(k));
        }
        return out;
    }
};

}  // namespace asteroides
