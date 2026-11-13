// Appli PC « Univers » : vieillissement de la lumière des étoiles du MODÈLE (traceurs), par composante.
// Table vieillissement.tsv (pipeline/natif/vieillissement_tsv.py, depuis pipeline/etoiles/vieillissement_populations.json de
// la PR 97, docs/vieillissement-lumiere.md) : régime « naissance continue », -3 à +10 Ga par pas de 50 Ma, facteurs de
// lumière et de température égaux à 1 aujourd'hui. Interpolation linéaire entre deux dates ; hors de la plage : bornée.
// Modèle : isochrones MIST v1.2, fonction de masse de Kroupa, histoires de formation supposées, naines blanches non comptées.
#pragma once
#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

class Vieillissement {
public:
    bool ready = false;
    static constexpr int kComps[5] = {1, 2, 4, 5, 6};

    bool load(const std::string& path) {
        std::ifstream f(path);
        std::string line;
        if (!std::getline(f, line)) return false;      // en-tête
        while (std::getline(f, line)) {
            std::istringstream in(line);
            Row r{};
            in >> r.t;
            for (float& v : r.lum) in >> v;
            for (float& v : r.teff) in >> v;
            if (in) rows_.push_back(r);
        }
        ready = rows_.size() >= 2;
        return ready;
    }

    // Facteurs à tGa (milliards d'années depuis aujourd'hui), rangés par numéro de composante (0 à 15 ; 1 hors table).
    void factors(double tGa, float lum[16], float teff[16]) const {
        for (int k = 0; k < 16; ++k) lum[k] = teff[k] = 1.0f;
        if (!ready) return;
        const double t = std::clamp(tGa, rows_.front().t, rows_.back().t);
        size_t i = 0;
        while (i + 2 < rows_.size() && rows_[i + 1].t < t) ++i;
        const Row &a = rows_[i], &b = rows_[i + 1];
        const double u = b.t > a.t ? (t - a.t) / (b.t - a.t) : 0.0;
        for (int c = 0; c < 5; ++c) {
            lum[kComps[c]] = static_cast<float>(a.lum[c] + (b.lum[c] - a.lum[c]) * u);
            teff[kComps[c]] = static_cast<float>(a.teff[c] + (b.teff[c] - a.teff[c]) * u);
        }
    }

private:
    struct Row { double t; float lum[5], teff[5]; };
    std::vector<Row> rows_;
};

}  // namespace
