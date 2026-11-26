// Appli PC « Univers » : les étoiles visibles de la Voie lactée suivent le FILM du Groupe local quand il existe.
//
// Le film (natif/physique/film_v2.h, écrit par pipeline/fusion/rencontre.py) contient ces mêmes étoiles, emportées par le
// calcul unique des cinq galaxies : c'est lui qui dit où elles sont à chaque date. Hors du film (dans le passé, ou si le
// film n'est pas là), l'appli garde ses orbites de référence (gaia_orbites.h). Il n'y a qu'une population d'étoiles : on
// change la source de leur mouvement, jamais les étoiles montrées.
//
// Format 3 (film_v3.h) : même rôle, mêmes fichiers d'ordre ; le film est reconnu à son index (« UNIVFLM3 »).
// Fichiers : <dossier du film>/film_index.bin et img_NNNNN.f16 ; vl_etoiles.ordre (pipeline/natif/ordre_film.py) : pour
// chaque étoile de l'appli, son rang dans le film. Le dossier du film est lu dans film_dossier.txt (une ligne), à côté des données.
//
// Entre deux images du film (10 millions d'années), la position suit une courbe passant par les quatre images voisines et la
// vitesse est la pente de cette courbe ; l'état est donné à la carte graphique au pas d'un million d'années de la date
// montrée, et gaia.vert le prolonge dans le pas, comme pour les orbites calculées.
#pragma once
#include <algorithm>
#include <array>
#include <climits>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <fstream>
#include <string>
#include <vector>

#include "film_v2.h"
#include "film_v3.h"
#include "film_vue.h"
#include "simulation.h"

namespace univers {

struct FilmStars {
    // Format 2 (film_v2.h) ou 3 (film_v3.h, lu si film_index.bin commence par « UNIVFLM3 ») ; un seul des deux sert.
    phys::film::FilmV2 film;
    phys::film::FilmV3 film3;
    bool v3 = false;
    std::vector<uint32_t> ordre;      // rang dans le film de chaque étoile de l'appli
    std::string dossier;
    std::string note;      // écarts connus de ce film, écrits par celui qui l'a calculé (<dossier>/ecarts.txt, une ligne) ; dits à l'écran
    bool ready = false;
    long lastStep = LONG_MIN;
    double reloadTimer = 0;

    // Rend false si le film, son index ou l'ordre des étoiles manquent : l'appli garde alors ses orbites de référence.
    // ordreFile : rang de chaque étoile de l'appli parmi les étoiles des galaxies firstGalaxy à firstGalaxy + galaxyCount - 1
    // du film (la Voie lactée : galaxie 0 seule ; les voisines : galaxies 1 à 4, voisines_etoiles.ordre).
    bool load(const std::string& dataDir, uint64_t starCount, const char* ordreFile = "vl_etoiles.ordre", int firstGalaxy = 0, int galaxyCount = 1) {
        std::ifstream f(dataDir + "/film_dossier.txt");
        if (!std::getline(f, dossier) || dossier.empty()) return false;
        while (!dossier.empty() && (dossier.back() == '\r' || dossier.back() == ' ')) dossier.pop_back();
        std::ifstream o(dataDir + "/" + ordreFile, std::ios::binary | std::ios::ate);
        if (!o || static_cast<uint64_t>(o.tellg()) != starCount * 4) return false;
        ordre.resize(starCount);
        o.seekg(0);
        o.read(reinterpret_cast<char*>(ordre.data()), static_cast<std::streamsize>(starCount * 4));
        first_ = firstGalaxy; galaxies_ = galaxyCount;
        v3 = estV3(dossier);
        if (v3) {
            std::string err;
            if (!film3.charger(dossier, err) || film3.galaxies() < firstGalaxy + galaxyCount) {
                std::printf("film v3 non lu : %s\n", err.empty() ? "galaxies manquantes" : err.c_str());
                return false;
            }
        } else if (!film.charger(dossier) || film.galaxies() < firstGalaxy + galaxyCount) return false;
        std::ifstream e(dossier + "/ecarts.txt");
        if (std::getline(e, note))
            while (!note.empty() && (note.back() == '\r' || note.back() == ' ')) note.pop_back();
        if (v3) {
            // Étoiles visibles de ces galaxies : blocs P de type 1, qui doivent se suivre (galaxie après galaxie).
            const auto b0 = film3.bloc(phys::film::FilmV3::Visibles, firstGalaxy);
            uint64_t fin = b0.premier;
            for (int g = firstGalaxy; g < firstGalaxy + galaxyCount; ++g) {
                const auto b = film3.bloc(phys::film::FilmV3::Visibles, g);
                if (!b.nombre || b.premier != fin) return false;
                fin += b.nombre;
            }
            if (fin - b0.premier != starCount) {
                std::printf("film v3 : %llu etoiles visibles dans le film, %llu dans l'appli\n", (unsigned long long)(fin - b0.premier), (unsigned long long)starCount);
                return false;
            }
            base_ = b0.premier;
            loadIgnore();
        } else {
            if (inFilm(film) != starCount) return false;
            base_ = 0;
            for (int g = 0; g < firstGalaxy; ++g) base_ += film.etoiles(g);
        }
        for (uint32_t k : ordre)
            if (k >= starCount) return false;
        ready = true;
        return true;
    }
    // Le film s'allonge pendant que le calcul tourne : l'index est relu de temps en temps.
    void reload(double dt) {
        reloadTimer += dt;
        if (!ready || reloadTimer < 5.0) return;
        reloadTimer = 0;
        if (v3) {      // film v3 : relu s'il a gagné des dates P (même contenu, mêmes traceurs)
            phys::film::FilmV3 neuf; std::string err;
            if (neuf.charger(dossier, err) && neuf.finGa() > film3.finGa() && neuf.traceursP() == film3.traceursP() && neuf.galaxies() == film3.galaxies())
                film3 = std::move(neuf);
            return;
        }
        phys::film::FilmV2 neuf;
        if (neuf.charger(dossier) && neuf.images() > film.images() && neuf.galaxies() == film.galaxies() && inFilm(neuf) == inFilm(film)) {
            film = std::move(neuf);
            for (int& h : have_) h = -1;
        }
    }
    // Le film couvre-t-il cette date (Ga depuis aujourd'hui) ? La dernière image listée peut être en cours d'écriture : on
    // s'arrête une image avant la fin.
    // Étoiles à ne pas dessiner (film v3) : <film>/ignorer.bin, rangs dans P (u32, triés), donnés par le fil du calcul pour un
    // défaut connu (film 3 : 4 258 étoiles du bulbe d'Andromède nées à plus de 10 kpc de son centre, bulbe sans coupure). Leur
    // lumière est mise à zéro quand le film mène (gaia.vert : facteur de lumière). hidden[s] : 1 pour l'étoile s de l'appli.
    std::vector<uint8_t> hidden;
    size_t hiddenCount = 0;
    void loadIgnore() {
        hidden.assign(ordre.size(), 0); hiddenCount = 0;
        std::vector<uint32_t> r;
        if (FILE* f = std::fopen((dossier + "/ignorer.bin").c_str(), "rb")) {
            uint32_t x;
            while (std::fread(&x, 4, 1, f) == 1) r.push_back(x);
            std::fclose(f);
        }
        if (r.empty()) return;
        std::sort(r.begin(), r.end());
        for (size_t s = 0; s < ordre.size(); ++s)
            if (std::binary_search(r.begin(), r.end(), static_cast<uint32_t>(base_ + ordre[s]))) { hidden[s] = 1; ++hiddenCount; }
        std::printf("film v3 : %zu etoiles de ces galaxies ecartees (ignorer.bin)\n", hiddenCount);
    }
    bool covers(double tGa) const { return ready && vue().couvre(tGa); }
    phys::film::FilmVue vue() const { return v3 ? phys::film::FilmVue{nullptr, &film3} : phys::film::FilmVue{&film, nullptr}; }
    double startGa() const { return vue().debutGa(); }
    double endGa() const { return vue().finSureGa(); }      // dernière date que le film couvre entièrement
    int imageCount() const { return v3 ? film3.dates() : film.images(); }

    // Lumière entière des étoiles (revue F1). vl_etoiles.bin ne porte que la lumière que Gaia ne montre pas déjà ; <nom>.lum
    // (pipeline/natif/ordre_film.py) donne la lumière entière de chaque étoile, en L☉ (bande V), dans l'ordre de l'appli.
    // gain[i] = entière / rangée : quand le film mène et que Gaia s'éteint, l'étoile reprend la lumière que Gaia portait.
    std::vector<float> gain;
    double gaiaOff = 0;      // 0 : Gaia montré, gain sans effet ; 1 : Gaia éteint, lumière entière (à poser avant states)
    // magnitude(i) : magnitude absolue V rangée pour l'étoile i (GaiaRenderer::starMagnitude). false sans fichier : rien ne change.
    template <class Mag> bool loadLum(const std::string& dataDir, const char* lumFile, Mag magnitude) {
        std::ifstream f(dataDir + "/" + lumFile, std::ios::binary | std::ios::ate);
        if (!f || static_cast<uint64_t>(f.tellg()) != ordre.size() * 4) return false;
        std::vector<float> lum(ordre.size());
        f.seekg(0);
        f.read(reinterpret_cast<char*>(lum.data()), static_cast<std::streamsize>(lum.size() * 4));
        gain.resize(lum.size());
        constexpr double kMSolV = 4.83;      // même valeur que pipeline/natif/etoiles_visibles.py
        for (size_t i = 0; i < lum.size(); ++i) {
            const double rangee = std::pow(10.0, -0.4 * (static_cast<double>(magnitude(i)) - kMSolV));
            gain[i] = rangee > 0 && std::isfinite(rangee) && lum[i] > 0 ? static_cast<float>(lum[i] / rangee) : 1.0f;
        }
        return true;
    }

    // États (8 flottants par étoile, ordre de l'appli, puis le Soleil) à tGa. Le 8e flottant de chaque étoile est son facteur de
    // lumière (gaia.vert ; 0 : sans objet). sun, sunVel : place et vitesse galactocentriques du
    // Soleil selon l'appli (kpc, km/s). false si une image manque : l'appelant garde alors l'état précédent.
    bool states(double tGa, phys::Vec3 sun, phys::Vec3 sunVel, std::vector<float>& out) {
        if (v3) return states3(tGa, sun, sunVel, out);
        const int n = film.images();
        int i = 0;
        while (i + 2 < n && film.date(i + 1) <= tGa) ++i;      // image juste avant la date
        const double span = film.date(i + 1) - film.date(i), u = std::clamp((tGa - film.date(i)) / span, 0.0, 1.0);
        const int want[4] = {std::max(i - 1, 0), i, i + 1, std::min(i + 2, n - 1)};
        const float* p[4];
        for (int j = 0; j < 4; ++j) {
            p[j] = decoded(want[j]);
            if (!p[j]) return false;
        }
        const double u2 = u * u, u3 = u2 * u, k = phys::film::FilmV2::kKpcGaEnKms / span;      // Catmull-Rom et sa pente (kpc/Ga -> km/s)
        const float w[4] = {static_cast<float>(0.5 * (-u + 2 * u2 - u3)), static_cast<float>(0.5 * (2 - 5 * u2 + 3 * u3)), static_cast<float>(0.5 * (u + 4 * u2 - 3 * u3)),
                            static_cast<float>(0.5 * (-u2 + u3))};
        const float d[4] = {static_cast<float>(0.5 * (-1 + 4 * u - 3 * u2) * k), static_cast<float>(0.5 * (-10 * u + 9 * u2) * k), static_cast<float>(0.5 * (1 + 8 * u - 9 * u2) * k),
                            static_cast<float>(0.5 * (-2 * u + 3 * u2) * k)};
        const size_t stars = ordre.size();
        out.resize((stars + 1) * 8);
        for (size_t s = 0; s < stars; ++s) {
            float* o = &out[s * 8];
            for (int a = 0; a < 3; ++a) {
                const size_t c = s * 3 + static_cast<size_t>(a);
                o[a] = w[0] * p[0][c] + w[1] * p[1][c] + w[2] * p[2][c] + w[3] * p[3][c];
                o[4 + a] = d[0] * p[0][c] + d[1] * p[1][c] + d[2] * p[2][c] + d[3] * p[3][c];
            }
            o[3] = 1.0f;      // sous-pas (sans objet : le film mène)
            o[7] = gain.empty() || gaiaOff <= 0 ? 0.0f : static_cast<float>(1.0 + gaiaOff * (gain[s] - 1.0));
        }
        float* o = &out[stars * 8];
        o[0] = static_cast<float>(sun.x); o[1] = static_cast<float>(sun.y); o[2] = static_cast<float>(sun.z); o[3] = 1.0f;
        o[4] = static_cast<float>(sunVel.x); o[5] = static_cast<float>(sunVel.y); o[6] = static_cast<float>(sunVel.z); o[7] = 0.0f;
        return true;
    }

    uint64_t base() const { return base_; }      // rang, dans une image du film, de la première étoile suivie

private:
    // Format 3 : Hermite sur les deux images qui encadrent la date (film_v3.h), positions et vitesses relatives au centre
    // de la galaxie d'origine, comme le format 2.
    std::vector<float> brut3_;
    bool states3(double tGa, phys::Vec3 sun, phys::Vec3 sunVel, std::vector<float>& out) {
        const size_t stars = ordre.size();
        brut3_.resize(stars * 6);
        if (!film3.etats(tGa, base_, stars, brut3_.data(), true)) return false;
        out.resize((stars + 1) * 8);
        for (size_t s = 0; s < stars; ++s) {
            const float* b = &brut3_[static_cast<size_t>(ordre[s]) * 6];
            float* o = &out[s * 8];
            o[0] = b[0]; o[1] = b[1]; o[2] = b[2]; o[3] = 1.0f;
            o[4] = b[3]; o[5] = b[4]; o[6] = b[5];
            o[7] = gain.empty() || gaiaOff <= 0 ? 0.0f : static_cast<float>(1.0 + gaiaOff * (gain[s] - 1.0));
            if (!hidden.empty() && hidden[s]) o[7] = kHiddenLight;
        }
        float* o = &out[stars * 8];
        o[0] = static_cast<float>(sun.x); o[1] = static_cast<float>(sun.y); o[2] = static_cast<float>(sun.z); o[3] = 1.0f;
        o[4] = static_cast<float>(sunVel.x); o[5] = static_cast<float>(sunVel.y); o[6] = static_cast<float>(sunVel.z); o[7] = 0.0f;
        return true;
    }
public:
    static constexpr float kHiddenLight = 1.0e-30f;      // facteur de lumière d'une étoile écartée (> 0 : gaia.vert le prend)
private:
    static bool estV3(const std::string& dossier) {
        char m[8] = {};
        FILE* f = std::fopen((dossier + "/film_index.bin").c_str(), "rb");
        if (!f) return false;
        const bool lu = std::fread(m, 1, 8, f) == 8;
        std::fclose(f);
        return lu && std::memcmp(m, "UNIVFLM3", 8) == 0;
    }
    int first_ = 0, galaxies_ = 1;
    uint64_t base_ = 0;      // rang, dans une image du film, de la première étoile suivie
    uint64_t inFilm(const phys::film::FilmV2& f) const {
        uint64_t n = 0;
        for (int g = first_; g < first_ + galaxies_; ++g) n += f.etoiles(g);
        return n;
    }
    // Quatre images décodées (nombres sur 16 bits -> flottants) et rangées dans l'ordre de l'appli : 48 Mo chacune pour 4 M d'étoiles.
    std::array<int, 4> have_{-1, -1, -1, -1};
    std::array<std::vector<float>, 4> frames_;

    const float* decoded(int image) {
        for (int j = 0; j < 4; ++j)
            if (have_[static_cast<size_t>(j)] == image) return frames_[static_cast<size_t>(j)].data();
        const uint16_t* raw = film.image(image);
        if (raw) raw += base_ * 3;      // les étoiles de la Voie lactée sont les premières du film, celles des voisines suivent
        if (!raw) return nullptr;
        // on remplace l'image décodée la plus éloignée de celle demandée
        int slot = 0, loin = -1;
        for (int j = 0; j < 4; ++j) {
            const int h = have_[static_cast<size_t>(j)], gap = h < 0 ? INT_MAX : std::abs(h - image);
            if (gap > loin) { loin = gap; slot = j; }
        }
        std::vector<float>& f = frames_[static_cast<size_t>(slot)];
        f.resize(ordre.size() * 3);
        for (size_t s = 0; s < ordre.size(); ++s) {
            const uint16_t* r = raw + static_cast<size_t>(ordre[s]) * 3;
            f[s * 3] = phys::film::demiVersFloat(r[0]);
            f[s * 3 + 1] = phys::film::demiVersFloat(r[1]);
            f[s * 3 + 2] = phys::film::demiVersFloat(r[2]);
        }
        have_[static_cast<size_t>(slot)] = image;
        return f.data();
    }
};

}  // namespace univers