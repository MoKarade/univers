// Appli PC « Univers », bibliothèque univers_physique : lecteur du FILM VERSION 3 du Groupe local.
//
// Écrit par pipeline/fusion/film_v3.py (branche film-3, commit 72fdd39 ; docs/format-film-v3.md). Le format 2 garde son
// lecteur (film_v2.h) pour les anciens films.
//
// Contenu. Des traceurs dans un ordre FIXE (l'identifiant d'un traceur est son rang) :
//   P, principaux : étoiles visibles des cinq galaxies, matière du calcul (étoiles et gaz), galaxies naines
//      (un point sans masse chacune, noms dans film.json), Soleil ;
//      une image toutes les 20 Ma (dates dont le bit 0 est levé) ;
//   C, M, L : classes de cadence, disjointes, de traceurs P qui tournent vite autour de leur centre ; images aux dates
//      intermédiaires (C tous les 2 Ma, M tous les 4 Ma, L tous les 10 Ma : bits 1, 3, 4). Le fichier des rangs
//      (centraux.bin, moyens.bin, lents.bin) donne le rang dans P de chaque traceur de la classe ;
//   G, Gaia (bit 2) : étoiles Gaia suivies par le calcul, une famille à part avec ses propres dates (tous les 10 Ma,
//      jusqu'à +1 Ga, y compris aux dates P) ; gaia.bin du dossier : rang de chaque traceur G dans le gaia.bin de l'appli.
// Un enregistrement : 18 octets, petit-boutiste. Position x, y, z en entiers 32 bits (0,01 pc), vitesse x, y, z en
// entiers 16 bits (0,05 km/s), RELATIVES au centre et à la vitesse d'ensemble de la galaxie d'origine à cette date.
//
// Interpolation. Hermite cartésien sur les deux images qui encadrent la date (positions et vitesses aux deux bouts),
// pour le traceur ET pour le centre de sa galaxie (centres et vitesses de l'index, à toutes les dates) : sans Hermite
// sur le centre, son bruit (10 à 50 pc) passerait dans toutes les étoiles (mesure du fil du calcul, 22/11/2026). Les
// nœuds d'un traceur sont les dates P et celles de sa classe : un traceur sans classe n'a que les dates P.
// Repère : phys::galaxie, centré sur la Voie lactée (centre de la galaxie 0 = 0). Temps : Ga, 0 = aujourd'hui.
// Hors du film : false, rien n'est inventé.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <list>
#include <string>
#include <vector>

#include "phys.h"

namespace phys::film {

#ifndef UNIVERS_FILM_FTELL64
#define UNIVERS_FILM_FTELL64
/* Position de fichier sur 64 bits : _fseeki64 / _ftelli64 sous Windows, fseeko / ftello ailleurs. */
#ifdef _WIN32
inline int film3_seek(FILE* f, long long o) { return _fseeki64(f, o, SEEK_SET); }
inline long long film3_taille(FILE* f) { _fseeki64(f, 0, SEEK_END); const long long n = _ftelli64(f); _fseeki64(f, 0, SEEK_SET); return n; }
#else
inline int film3_seek(FILE* f, long long o) { return fseeko(f, (off_t)o, SEEK_SET); }
inline long long film3_taille(FILE* f) { fseeko(f, 0, SEEK_END); const long long n = (long long)ftello(f); fseeko(f, 0, SEEK_SET); return n; }
#endif
#endif

class FilmV3 {
public:
    static constexpr double kKmsEnKpcGa = 1.0227121650456;      // 1 km/s = 1,0227 kpc/Ga
    static constexpr double kUnitePosKpc = 1e-5;                // 0,01 pc
    static constexpr double kUniteVitKms = 0.05;
    static constexpr size_t kEnreg = 18;
    enum Famille : uint8_t { P = 0, C = 1, G = 2, M = 3, L = 4 };
    enum Type : uint8_t { Visibles = 1, Matiere = 2, Soleil = 3, Naine = 4, Gaia = 5 };
    struct Bloc { uint8_t famille = 0, type = 0; uint16_t galaxie = 0xFFFF; uint64_t premier = 0, nombre = 0; };
    struct Ecart { Vec3 position, vitesse; };      // calculé moins mesuré (kpc, km/s)

    // Lit l'index et les fichiers de rangs. err dit pourquoi en cas d'échec.
    bool charger(const std::string& dossier, std::string& err) {
        *this = FilmV3{}; dossier_ = dossier;
        std::vector<char> b;
        if (!lire(dossier + "/film_index.bin", b)) return echec(err, "film_index.bin illisible");
        if (b.size() < 80 || std::memcmp(b.data(), "UNIVFLM3", 8) != 0) return echec(err, "film_index.bin : pas un film version 3");
        uint32_t version, ng, nb, nd, enreg; uint64_t n[5]; double pas;
        std::memcpy(&version, &b[8], 4); std::memcpy(&ng, &b[12], 4); std::memcpy(&nb, &b[16], 4); std::memcpy(&nd, &b[20], 4);
        std::memcpy(n, &b[24], 40); std::memcpy(&pas, &b[64], 8); std::memcpy(&enreg, &b[72], 4);
        if (version != 3 || enreg != kEnreg) return echec(err, "film_index.bin : version ou taille d'enregistrement inattendue");
        if (ng < 1 || nd < 1) return echec(err, "film_index.bin : aucune galaxie ou aucune date");
        const size_t parDate = 16 + 48ull * ng + 8, besoin = 80 + 32ull * nb + 48ull * (ng + 1) + 16 + parDate * nd;
        if (b.size() < besoin) return echec(err, "film_index.bin tronqué");
        g_ = (int)ng; pasBaseMa_ = pas;
        nP_ = n[0]; nC_ = n[1]; nG_ = n[2]; nM_ = n[3]; nL_ = n[4];
        size_t o = 80;
        blocs_.resize(nb);
        for (auto& x : blocs_) {
            std::memcpy(&x.famille, &b[o], 1); std::memcpy(&x.type, &b[o + 1], 1); std::memcpy(&x.galaxie, &b[o + 2], 2);
            std::memcpy(&x.premier, &b[o + 8], 8); std::memcpy(&x.nombre, &b[o + 16], 8); o += 32;
        }
        ecarts_.resize(ng + 1);      // galaxies puis le Soleil
        for (auto& e : ecarts_) { double v[6]; std::memcpy(v, &b[o], 48); e = {{v[0], v[1], v[2]}, {v[3], v[4], v[5]}}; o += 48; }
        std::memcpy(&gaiaTaille_, &b[o], 8); std::memcpy(&gaiaCrc_, &b[o + 8], 4); o += 16;
        t_.resize(nd); fam_.resize(nd); c_.resize((size_t)nd * ng * 3); v_.resize((size_t)nd * ng * 3); e_.resize(nd);
        for (uint32_t k = 0; k < nd; ++k) {
            std::memcpy(&t_[k], &b[o], 8); std::memcpy(&fam_[k], &b[o + 8], 4); o += 16;
            for (uint32_t g = 0; g < ng; ++g) {
                std::memcpy(&c_[((size_t)k * ng + g) * 3], &b[o], 24); std::memcpy(&v_[((size_t)k * ng + g) * 3], &b[o + 24], 24); o += 48;
            }
            std::memcpy(&e_[k], &b[o], 8); o += 8;
        }
        for (uint32_t k = 1; k < nd; ++k) if (!(t_[k] > t_[k - 1])) return echec(err, "film_index.bin : dates non croissantes");
        // Galaxie d'origine de chaque traceur P (blocs de la famille P) ; 0xFFFF : pas encore rangé.
        origineP_.assign(nP_, 0xFFFF);
        for (const auto& x : blocs_)
            if (x.famille == P) {
                if (x.premier + x.nombre > nP_ || x.galaxie >= ng) return echec(err, "film_index.bin : bloc P hors des traceurs ou des galaxies");
                std::fill(origineP_.begin() + (long)x.premier, origineP_.begin() + (long)(x.premier + x.nombre), x.galaxie);
            }
        for (uint64_t i = 0; i < nP_; ++i) if (origineP_[i] == 0xFFFF) return echec(err, "film_index.bin : traceur P sans bloc");
        // Classes de cadence : pour chaque traceur P, sa famille de dates intermédiaires et son rang dans cette famille.
        classe_.assign(nP_, P); rangClasse_.assign(nP_, 0);
        const struct { Famille f; const char* nom; uint64_t n; } cl[3] = {{C, "centraux.bin", nC_}, {M, "moyens.bin", nM_}, {L, "lents.bin", nL_}};
        for (const auto& c : cl) {
            if (!c.n) continue;
            std::vector<char> r;
            if (!lire(dossier + "/" + c.nom, r) || r.size() != c.n * 4) return echec(err, std::string(c.nom) + " absent ou de mauvaise taille");
            for (uint64_t j = 0; j < c.n; ++j) {
                uint32_t i; std::memcpy(&i, &r[j * 4], 4);
                if (i >= nP_ || classe_[i] != P) return echec(err, std::string(c.nom) + " : rang hors de P ou déjà dans une autre classe");
                classe_[i] = c.f; rangClasse_[i] = (uint32_t)j;
            }
        }
        // Couverture : de la première à la dernière date P (un traceur sans classe n'a que ces nœuds).
        for (uint32_t k = 0; k < nd; ++k) if (fam_[k] & 1u) { if (premierP_ < 0) premierP_ = (int)k; dernierP_ = (int)k; }
        if (premierP_ < 0 || dernierP_ == premierP_) return echec(err, "moins de deux images P");
        // Famille G (Gaia) : ses propres dates (bit 2), sa galaxie d'origine dans son bloc.
        for (uint32_t k = 0; k < nd; ++k) if (fam_[k] & 4u) { if (premierG_ < 0) premierG_ = (int)k; dernierG_ = (int)k; }
        for (const auto& x : blocs_) if (x.famille == G) { if (x.galaxie >= ng || x.premier + x.nombre > nG_) return echec(err, "film_index.bin : bloc G invalide"); origineG_ = x.galaxie; }
        return true;
    }

    int galaxies() const { return g_; }
    int dates() const { return (int)t_.size(); }
    double date(int k) const { return t_[(size_t)k]; }
    uint32_t familles(int k) const { return fam_[(size_t)k]; }
    double ecartEnergie(int k) const { return e_[(size_t)k]; }
    double pasBaseMa() const { return pasBaseMa_; }
    uint64_t traceursP() const { return nP_; }
    uint64_t traceursG() const { return nG_; }
    uint64_t traceursClasse(Famille f) const { return f == C ? nC_ : f == M ? nM_ : f == L ? nL_ : 0; }
    const std::vector<Bloc>& blocs() const { return blocs_; }
    const Ecart& decalageAT0(int g) const { return ecarts_[(size_t)g]; }
    const Ecart& ecartSoleil() const { return ecarts_[(size_t)g_]; }
    uint64_t gaiaTaille() const { return gaiaTaille_; }
    uint32_t gaiaCrc32() const { return gaiaCrc_; }
    int origine(uint64_t i) const { return origineP_[i]; }
    Famille classe(uint64_t i) const { return (Famille)classe_[i]; }
    // Premier bloc P de ce type (et de cette galaxie si g >= 0) ; nombre = 0 s'il n'y en a pas.
    Bloc bloc(Type type, int g = -1) const {
        for (const auto& x : blocs_) if (x.famille == P && x.type == type && (g < 0 || x.galaxie == g)) return x;
        return {};
    }

    // Galaxies naines : un point sans masse chacune, dans P (bloc de type Naine, galaxie 0), positions relatives à la
    // Voie lactée comme le reste de P. Leurs noms, dans l'ordre du bloc, sont dans film.json (« naines » : « noms »).
    // false si film.json manque ou n'a pas de noms ; noms vide et true s'il n'y a pas de naines.
    bool nomsNaines(std::vector<std::string>& noms, std::string& err) const {
        noms.clear();
        const Bloc b = bloc(Naine, 0);
        if (!b.nombre) return true;
        std::vector<char> j;
        if (!lire(dossier_ + "/film.json", j)) return echec(err, "film.json absent");
        const std::string s(j.begin(), j.end());
        size_t i = s.find("\"naines\""); if (i != std::string::npos) i = s.find("\"noms\"", i);
        if (i != std::string::npos) i = s.find('[', i);
        if (i == std::string::npos) return echec(err, "film.json : pas de noms de naines");
        for (++i; i < s.size();) {
            while (i < s.size() && (s[i] == ' ' || s[i] == ',' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) ++i;
            if (i >= s.size() || s[i] == ']') break;
            if (s[i] != '"') return echec(err, "film.json : noms de naines illisibles");
            std::string n; uint32_t haut = 0;
            for (++i; i < s.size() && s[i] != '"'; ++i) {
                if (s[i] != '\\') { n += s[i]; continue; }
                if (++i >= s.size()) break;
                const char e = s[i];
                if (e == 'u' && i + 4 < s.size()) {      // \uXXXX, paires de substitution comprises, écrit en UTF-8
                    uint32_t c = (uint32_t)std::strtoul(s.substr(i + 1, 4).c_str(), nullptr, 16); i += 4;
                    if (c >= 0xD800 && c < 0xDC00) { haut = c; continue; }
                    if (c >= 0xDC00 && c < 0xE000 && haut) c = 0x10000 + ((haut - 0xD800) << 10) + (c - 0xDC00);
                    haut = 0;
                    if (c < 0x80) n += (char)c;
                    else if (c < 0x800) { n += (char)(0xC0 | c >> 6); n += (char)(0x80 | (c & 63)); }
                    else if (c < 0x10000) { n += (char)(0xE0 | c >> 12); n += (char)(0x80 | (c >> 6 & 63)); n += (char)(0x80 | (c & 63)); }
                    else { n += (char)(0xF0 | c >> 18); n += (char)(0x80 | (c >> 12 & 63)); n += (char)(0x80 | (c >> 6 & 63)); n += (char)(0x80 | (c & 63)); }
                } else n += e == 'n' ? '\n' : e == 't' ? '\t' : e == 'r' ? '\r' : e == 'b' ? '\b' : e == 'f' ? '\f' : e;
            }
            noms.push_back(n); ++i;
        }
        if (noms.size() != b.nombre) return echec(err, "film.json : nombre de noms de naines différent du bloc");
        return true;
    }

    // Dates couvertes par tous les traceurs P (Ga).
    double debutGa() const { return t_[(size_t)premierP_]; }
    double finGa() const { return t_[(size_t)dernierP_]; }
    bool couvre(double tGa) const { return tGa >= debutGa() && tGa <= finGa(); }

    // Centre (kpc) et vitesse (km/s) de la galaxie g relatifs à la Voie lactée, à tGa (Hermite sur toutes les dates de
    // l'index). false hors des dates de l'index.
    bool centre(int g, double tGa, Vec3& pos, Vec3* vit = nullptr) const {
        int k; double u; if (!placeDates(tGa, k, u)) return false;
        const double h = (t_[(size_t)k + 1] - t_[(size_t)k]) * kKmsEnKpcGa;
        const double* a = &c_[((size_t)k * g_ + g) * 3]; const double* b = &c_[((size_t)(k + 1) * g_ + g) * 3];
        const double* va = &v_[((size_t)k * g_ + g) * 3]; const double* vb = &v_[((size_t)(k + 1) * g_ + g) * 3];
        double p[3], v[3]; for (int c = 0; c < 3; ++c) hermite(a[c], va[c], b[c], vb[c], h, u, p[c], v[c]);
        pos = {p[0], p[1], p[2]}; if (vit) *vit = {v[0], v[1], v[2]};
        return true;
    }

    // États des traceurs P [premier, premier + nombre) à tGa : 6 flottants chacun (position kpc, vitesse km/s), relatifs à
    // la Voie lactée (centre de la galaxie d'origine ajouté, lui aussi par Hermite). out : au moins 6 × nombre valeurs.
    // false hors du film ou si une image manque.
    // relatif = true : positions et vitesses relatives au centre de la galaxie d'origine (sans l'ajouter), comme l'appli les
    // donne à gaia.vert.
    bool etats(double tGa, uint64_t premier, uint64_t nombre, float* out, bool relatif = false) {
        if (!couvre(tGa) || premier + nombre > nP_) return false;
        // Nœuds P qui encadrent la date, et pour chaque classe ses propres nœuds (dates P ou dates de la classe).
        Noeuds nP, nc[5];
        if (!noeuds(tGa, 1u, nP)) return false;
        const uint32_t bits[5] = {1u, 1u | 2u, 0, 1u | 8u, 1u | 16u};
        for (Famille f : {C, M, L}) if (traceursClasse(f) && !noeuds(tGa, bits[f], nc[f])) return false;
        // Centres de chaque galaxie à tGa.
        std::vector<double> cen((size_t)g_ * 6);
        for (int g = 0; g < g_; ++g) {
            Vec3 p, v; if (!centre(g, tGa, p, &v)) return false;
            double* d = &cen[(size_t)g * 6]; d[0] = p.x; d[1] = p.y; d[2] = p.z; d[3] = v.x; d[4] = v.y; d[5] = v.z;
        }
        const Image* ia = imageP(nP.a, premier, nombre); const Image* ib = imageP(nP.b, premier, nombre);
        if (!ia || !ib) return false;
        const Image* ca[5] = {}; const Image* cb[5] = {};
        for (Famille f : {C, M, L}) {
            if (!traceursClasse(f)) continue;
            ca[f] = imageNoeud(nc[f].a, f, premier, nombre); cb[f] = imageNoeud(nc[f].b, f, premier, nombre);
            if (!ca[f] || !cb[f]) return false;
        }
        for (uint64_t s = 0; s < nombre; ++s) {
            const uint64_t i = premier + s; const Famille f = (Famille)classe_[i];
            const Noeuds& n = f == P ? nP : nc[f];
            // Un nœud de classe tombé sur une date P se lit dans l'image P (rang s de la plage), sinon dans le fichier de la
            // classe (rang du traceur dans sa classe).
            const Image* xa = f == P ? ia : ca[f]; const Image* xb = f == P ? ib : cb[f];
            const uint8_t* ra = xa->estP ? xa->rec(s) : xa->rec(rangClasse_[i]);
            const uint8_t* rb = xb->estP ? xb->rec(s) : xb->rec(rangClasse_[i]);
            double pa[3], va[3], pb[3], vb[3]; decoder(ra, pa, va); decoder(rb, pb, vb);
            static const double zero[6] = {};
            const double* c = relatif ? zero : &cen[(size_t)origineP_[i] * 6];
            float* o = out + s * 6;
            for (int a = 0; a < 3; ++a) {
                double p, v; hermite(pa[a], va[a], pb[a], vb[a], n.h, n.u, p, v);
                o[a] = (float)(p + c[a]); o[3 + a] = (float)(v + c[3 + a]);
            }
        }
        return true;
    }

    // Pour un lecteur qui lit lui-même les images (film_carte_v3.h, calcul sur la carte graphique).
    // Nœuds : les deux dates qui encadrent tGa pour les traceurs de la famille f (P seuls : dates P ; classe C, M, L : dates
    // P ou de la classe). h : écart en (km/s)⁻¹·kpc pour Hermite, u : fraction.
    struct Noeuds { int a = -1, b = -1; double u = 0, h = 1; };
    bool noeudsDe(Famille f, double tGa, Noeuds& n) const {
        const uint32_t bits = f == P ? 1u : f == C ? 3u : f == M ? 9u : f == L ? 17u : 0u;
        return bits && noeuds(tGa, bits, n);
    }
    bool estDateP(int k) const { return (fam_[(size_t)k] & 1u) != 0; }
    uint32_t famillesA(int k) const { return fam_[(size_t)k]; }
    const std::vector<uint8_t>& classes() const { return classe_; }        // famille de chaque traceur P (P, C, M ou L)
    const std::vector<uint32_t>& rangsDansClasse() const { return rangClasse_; }
    const std::string& dossier() const { return dossier_; }
    // Lit les enregistrements [premier, premier + nombre) du fichier <lettre>_<k>.bin, qui doit contenir exactement total
    // enregistrements (un fichier d'une autre taille est refusé). out : nombre × 18 octets.
    static bool lireTranche(const std::string& dossier, char lettre, int k, uint64_t premier, uint64_t nombre, uint64_t total, std::vector<uint8_t>& out) {
        char nom[32]; std::snprintf(nom, sizeof nom, "/%c_%05d.bin", lettre, k);
        FILE* f = std::fopen((dossier + nom).c_str(), "rb"); if (!f) return false;
        const long long taille = film3_taille(f);
        bool ok = taille >= 0 && (uint64_t)taille == total * kEnreg && premier + nombre <= total && film3_seek(f, (long long)(premier * kEnreg)) == 0;
        if (ok) { out.resize(nombre * kEnreg); ok = nombre == 0 || std::fread(out.data(), 1, out.size(), f) == out.size(); }
        std::fclose(f);
        return ok;
    }

    // Famille G : étoiles Gaia suivies par le calcul (positions relatives à la Voie lactée), une image tous les 10 Ma
    // jusqu'à +1 Ga. Couverture : de la première à la dernière date G.
    bool aGaia() const { return nG_ > 0 && premierG_ >= 0 && dernierG_ > premierG_; }
    double debutGaGaia() const { return aGaia() ? t_[(size_t)premierG_] : 0; }
    double finGaGaia() const { return aGaia() ? t_[(size_t)dernierG_] : 0; }
    bool couvreGaia(double tGa) const { return aGaia() && tGa >= debutGaGaia() && tGa <= finGaGaia(); }
    // Rang de chaque traceur G dans le gaia.bin de l'appli (fichier gaia.bin du dossier du film, entiers 32 bits).
    bool chargerRangsGaia(std::vector<uint32_t>& rangs, std::string& err) const {
        std::vector<char> r;
        if (!lire(dossier_ + "/gaia.bin", r) || r.size() != nG_ * 4) return echec(err, "gaia.bin du film absent ou de mauvaise taille");
        rangs.resize(nG_); if (nG_) std::memcpy(rangs.data(), r.data(), r.size());
        return true;
    }
    // Le gaia.bin de l'appli est-il celui du calcul ? Compare la taille, puis le CRC32 (lecture complète : quelques
    // secondes pour 2,4 Go). false si le fichier manque ou diffère : l'appli ne doit alors pas relier G à ses étoiles.
    bool gaiaCorrespond(const std::string& cheminGaia) const {
        if (!gaiaTaille_) return false;
        FILE* f = std::fopen(cheminGaia.c_str(), "rb"); if (!f) return false;
        const long long n = film3_taille(f);
        if (n < 0 || (uint64_t)n != gaiaTaille_) { std::fclose(f); return false; }
        uint32_t c = 0xFFFFFFFFu; std::vector<uint8_t> tampon(1u << 22); size_t lu;
        while ((lu = std::fread(tampon.data(), 1, tampon.size(), f)) > 0) c = crc32(c, tampon.data(), lu);
        std::fclose(f);
        return (c ^ 0xFFFFFFFFu) == gaiaCrc_;
    }
    // États des traceurs G [premier, premier + nombre) à tGa, comme etats().
    bool etatsGaia(double tGa, uint64_t premier, uint64_t nombre, float* out) {
        if (!couvreGaia(tGa) || premier + nombre > nG_) return false;
        Noeuds n; if (!noeuds(tGa, 4u, n)) return false;
        Vec3 cp, cv; if (!centre(origineG_, tGa, cp, &cv)) return false;
        const Image* a = image(n.a, 'g', premier, nombre, false, nG_); const Image* b = image(n.b, 'g', premier, nombre, false, nG_);
        if (!a || !b) return false;
        const double c[6] = {cp.x, cp.y, cp.z, cv.x, cv.y, cv.z};
        for (uint64_t s = 0; s < nombre; ++s) {
            double pa[3], va[3], pb[3], vb[3]; decoder(a->rec(s), pa, va); decoder(b->rec(s), pb, vb);
            float* o = out + s * 6;
            for (int k = 0; k < 3; ++k) { double p, v; hermite(pa[k], va[k], pb[k], vb[k], n.h, n.u, p, v); o[k] = (float)(p + c[k]); o[3 + k] = (float)(v + c[3 + k]); }
        }
        return true;
    }
    // CRC32 (polynôme 0xEDB88320, celui de zlib) : c = 0xFFFFFFFF au départ, résultat ^ 0xFFFFFFFF à la fin.
    static uint32_t crc32(uint32_t c, const uint8_t* p, size_t n) {
        static const auto table = [] { std::array<uint32_t, 256> t{}; for (uint32_t i = 0; i < 256; ++i) { uint32_t x = i; for (int k = 0; k < 8; ++k) x = x & 1 ? 0xEDB88320u ^ (x >> 1) : x >> 1; t[i] = x; } return t; }();
        for (size_t i = 0; i < n; ++i) c = table[(c ^ p[i]) & 0xFFu] ^ (c >> 8);
        return c;
    }

    // Matière du calcul (bloc P de type Matiere, galaxie après galaxie) : nature à t = 0 (matiere.bin), puis naissances et
    // retours au gaz (evenements.bin, triés par date). natureA rend, pour chaque particule de matière, 1 si c'est une
    // étoile à tGa, 0 si c'est du gaz. false si les fichiers manquent.
    struct Particule { uint8_t nature, sorte; uint16_t galaxie; float masse; };
    static_assert(sizeof(Particule) == 8, "matiere.bin : 8 octets par particule");
    struct Evenement { uint32_t rang; uint8_t nature; double date; };
    bool chargerMatiere(std::string& err) {
        std::vector<char> m, e;
        if (!lire(dossier_ + "/matiere.bin", m) || m.size() % 8) return echec(err, "matiere.bin absent ou de mauvaise taille");
        matiere_.resize(m.size() / 8);
        for (size_t i = 0; i < matiere_.size(); ++i) std::memcpy(&matiere_[i], &m[i * 8], 8);
        evenements_.clear();
        if (lire(dossier_ + "/evenements.bin", e)) {
            if (e.size() % 16) return echec(err, "evenements.bin de mauvaise taille");
            evenements_.resize(e.size() / 16);
            for (size_t i = 0; i < evenements_.size(); ++i) {
                auto& x = evenements_[i]; std::memcpy(&x.rang, &e[i * 16], 4); x.nature = (uint8_t)e[i * 16 + 4]; std::memcpy(&x.date, &e[i * 16 + 8], 8);
                if (x.rang >= matiere_.size()) return echec(err, "evenements.bin : rang hors de la matière");
            }
        }
        return true;
    }
    const std::vector<Particule>& matiere() const { return matiere_; }
    const std::vector<Evenement>& evenements() const { return evenements_; }
    void natureA(double tGa, std::vector<uint8_t>& out) const {
        out.resize(matiere_.size());
        for (size_t i = 0; i < matiere_.size(); ++i) out[i] = matiere_[i].nature;
        for (const auto& x : evenements_) { if (x.date > tGa + 1e-12) break; out[x.rang] = x.nature; }
    }

    // Un enregistrement de 18 octets -> position (kpc) et vitesse (km/s).
    static void decoder(const uint8_t* r, double p[3], double v[3]) {
        int32_t q[3]; int16_t w[3]; std::memcpy(q, r, 12); std::memcpy(w, r + 12, 6);
        for (int a = 0; a < 3; ++a) { p[a] = q[a] * kUnitePosKpc; v[a] = w[a] * kUniteVitKms; }
    }
    // Hermite cubique entre (pa, va) et (pb, vb) ; h : durée en kpc/(km/s) ; position et vitesse (km/s) à la fraction u.
    static void hermite(double pa, double va, double pb, double vb, double h, double u, double& p, double& v) {
        const double u2 = u * u, u3 = u2 * u;
        p = (2 * u3 - 3 * u2 + 1) * pa + (u3 - 2 * u2 + u) * h * va + (-2 * u3 + 3 * u2) * pb + (u3 - u2) * h * vb;
        v = ((6 * u2 - 6 * u) * pa + (6 * u2 - 6 * u) * -pb) / h + (3 * u2 - 4 * u + 1) * va + (3 * u2 - 2 * u) * vb;
    }

private:
    struct Image {
        int date = -1; char lettre = 0; uint64_t premier = 0, nombre = 0; bool estP = false;
        std::vector<uint8_t> octets;
        const uint8_t* rec(uint64_t j) const { return octets.data() + j * kEnreg; }
    };

    std::string dossier_;
    int g_ = 0, premierP_ = -1, dernierP_ = -1, premierG_ = -1, dernierG_ = -1, origineG_ = 0;
    double pasBaseMa_ = 0;
    uint64_t nP_ = 0, nC_ = 0, nG_ = 0, nM_ = 0, nL_ = 0, gaiaTaille_ = 0;
    uint32_t gaiaCrc_ = 0;
    std::vector<Bloc> blocs_;
    std::vector<Ecart> ecarts_;
    std::vector<double> t_, c_, v_, e_;
    std::vector<uint32_t> fam_;
    std::vector<uint16_t> origineP_;
    std::vector<uint8_t> classe_;
    std::vector<uint32_t> rangClasse_;
    std::vector<Particule> matiere_;
    std::vector<Evenement> evenements_;
    std::list<Image> cache_;      // images lues, la plus récente devant
    static constexpr size_t kCache = 12;      // au plus 8 images servent à un même appel d'etats

    static bool echec(std::string& err, const std::string& m) { err = m; return false; }

    bool placeDates(double tGa, int& k, double& u) const {
        const int n = (int)t_.size();
        if (n < 2 || tGa < t_.front() || tGa > t_.back()) return false;
        k = (int)(std::upper_bound(t_.begin(), t_.end(), tGa) - t_.begin()) - 1;
        k = std::clamp(k, 0, n - 2);
        u = (tGa - t_[(size_t)k]) / (t_[(size_t)k + 1] - t_[(size_t)k]);
        return true;
    }
    // Les deux dates portant l'un des bits qui encadrent tGa.
    bool noeuds(double tGa, uint32_t bits, Noeuds& n) const {
        int a = -1, b = -1;
        for (int k = 0; k < (int)t_.size(); ++k) {
            if (!(fam_[(size_t)k] & bits)) continue;
            if (t_[(size_t)k] <= tGa) a = k;
            if (t_[(size_t)k] >= tGa && b < 0 && k != a) b = k;
        }
        if (a < 0) return false;
        if (b < 0) {      // tGa est exactement la dernière date portant ces bits : on prend l'intervalle d'avant
            b = a; a = -1;
            for (int k = b - 1; k >= 0; --k) if (fam_[(size_t)k] & bits) { a = k; break; }
            if (a < 0) return false;
        }
        n.a = a; n.b = b; n.h = (t_[(size_t)b] - t_[(size_t)a]) * kKmsEnKpcGa; n.u = (tGa - t_[(size_t)a]) / (t_[(size_t)b] - t_[(size_t)a]);
        return true;
    }
    // Image d'un nœud de classe : la date P (même plage que les P) ou le fichier de la classe (entier).
    const Image* imageNoeud(int k, Famille f, uint64_t premier, uint64_t nombre) {
        if (fam_[(size_t)k] & 1u) return imageP(k, premier, nombre);
        const char l = f == C ? 'c' : f == M ? 'm' : 'l';
        return image(k, l, 0, traceursClasse(f), false);
    }
    const Image* imageP(int k, uint64_t premier, uint64_t nombre) { return image(k, 'p', premier, nombre, true); }
    // total : traceurs dans le fichier entier (contrôle de sa taille) ; 0 : nP_ si estP, sinon nombre.
    const Image* image(int k, char lettre, uint64_t premier, uint64_t nombre, bool estP, uint64_t total = 0) {
        for (auto it = cache_.begin(); it != cache_.end(); ++it)
            if (it->date == k && it->lettre == lettre && it->premier == premier && it->nombre == nombre) {
                cache_.splice(cache_.begin(), cache_, it); return &cache_.front();
            }
        char nom[32]; std::snprintf(nom, sizeof nom, "/%c_%05d.bin", lettre, k);
        FILE* f = std::fopen((dossier_ + nom).c_str(), "rb"); if (!f) return nullptr;
        const long long taille = film3_taille(f);
        const uint64_t attendu = (total ? total : estP ? nP_ : nombre) * kEnreg;
        Image im; im.date = k; im.lettre = lettre; im.premier = premier; im.nombre = nombre; im.estP = estP;
        bool ok = taille >= 0 && (uint64_t)taille == attendu && film3_seek(f, (long long)(premier * kEnreg)) == 0;
        if (ok) { im.octets.resize(nombre * kEnreg); ok = std::fread(im.octets.data(), 1, im.octets.size(), f) == im.octets.size(); }
        std::fclose(f);
        if (!ok) return nullptr;
        cache_.push_front(std::move(im));
        if (cache_.size() > kCache) cache_.pop_back();
        return &cache_.front();
    }
    static bool lire(const std::string& p, std::vector<char>& out) {
        FILE* f = std::fopen(p.c_str(), "rb"); if (!f) return false;
        const long long n = film3_taille(f); if (n < 0) { std::fclose(f); return false; }
        out.resize((size_t)n); const bool ok = n == 0 || std::fread(out.data(), 1, (size_t)n, f) == (size_t)n; std::fclose(f); return ok;
    }
};

}  // namespace phys::film
