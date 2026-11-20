// Appli PC « Univers » : fiches complètes des astres (demande de Marc, 20/11/2026 : « toutes les données disponibles »).
// Les fichiers fiches/*.tsv, à côté du programme, sont écrits par pipeline/natif/fiches_*.py (format : docs/fiches-format.md).
// Chaque ligne d'une fiche : groupe, libellé, valeur, incertitude, unité, statut (mesuré, calculé, modèle, publié) et source.
//
// Les fichiers peuvent peser plusieurs centaines de Mo (1,58 million d'astéroïdes) : ils ne sont pas chargés en mémoire.
// Au démarrage, un fil à part les parcourt une fois et garde, pour chaque astre, l'empreinte de son nom et la place de ses
// lignes dans le fichier (16 octets par astre). Quand un astre est choisi, seules ses lignes sont relues sur le disque.
#pragma once
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace fiches {

struct Ligne {
    std::string groupe, libelle, valeur, incertitude, unite, statut, source;
};

// Empreinte d'un nom (FNV-1a 64 bits). Deux noms de même empreinte sont départagés à la relecture.
inline uint64_t empreinte(std::string_view s) {
    uint64_t h = 1469598103934665603ull;
    for (unsigned char c : s) {
        h ^= c;
        h *= 1099511628211ull;
    }
    return h;
}

// Découpe une ligne aux tabulations (cases vides gardées).
inline std::vector<std::string> decouper(const std::string& l) {
    std::vector<std::string> c;
    size_t from = 0;
    for (size_t tab; (tab = l.find('\t', from)) != std::string::npos; from = tab + 1) c.push_back(l.substr(from, tab - from));
    c.push_back(l.substr(from));
    return c;
}

// Retire le retour chariot de fin (fichiers écrits sous Windows) et la marque d'ordre des octets en tête de fichier.
inline void nettoyer(std::string& l, bool premiere) {
    if (!l.empty() && l.back() == '\r') l.pop_back();
    if (premiere && l.size() >= 3 && static_cast<unsigned char>(l[0]) == 0xEF && static_cast<unsigned char>(l[1]) == 0xBB &&
        static_cast<unsigned char>(l[2]) == 0xBF)
        l.erase(0, 3);
}

// ---------------------------------------------------------------- écriture des nombres (texte seul, sans arrondi)

// Écrit un nombre de la source en français, chiffre pour chiffre : virgule décimale, espace insécable entre les milliers,
// « 1.989e30 » -> « 1,989 × 10^30 ». Les chiffres de la source sont gardés tels quels : ni précision inventée, ni perdue.
// Une case qui n'est pas un nombre est rendue telle quelle.
inline std::string nombreFr(const std::string& s) {
    size_t i = 0;
    std::string signe;
    if (i < s.size() && (s[i] == '-' || s[i] == '+')) signe = s[i++] == '-' ? "\xE2\x88\x92" : "";
    const size_t debutEntier = i;
    while (i < s.size() && s[i] >= '0' && s[i] <= '9') ++i;
    std::string entier = s.substr(debutEntier, i - debutEntier), frac;
    if (i < s.size() && s[i] == '.') {
        const size_t d = ++i;
        while (i < s.size() && s[i] >= '0' && s[i] <= '9') ++i;
        frac = s.substr(d, i - d);
    }
    if (entier.empty() && frac.empty()) return s;
    std::string exposant;
    if (i < s.size() && (s[i] == 'e' || s[i] == 'E')) {
        size_t j = i + 1;
        std::string se;
        if (j < s.size() && (s[j] == '-' || s[j] == '+')) se = s[j++] == '-' ? "\xE2\x88\x92" : "";
        const size_t d = j;
        while (j < s.size() && s[j] >= '0' && s[j] <= '9') ++j;
        if (j == d) return s;
        std::string e = s.substr(d, j - d);
        while (e.size() > 1 && e[0] == '0') e.erase(0, 1);
        exposant = e == "0" ? "" : " \xC3\x97 10^" + se + e;
        i = j;
    }
    if (i != s.size()) return s;      // reste du texte : pas un nombre
    if (entier.empty()) entier = "0";
    // Espace entre les milliers, sauf un entier de 4 chiffres (une année, « 2007 », reste collée).
    const bool grouper = entier.size() > 4 || (entier.size() == 4 && !frac.empty());
    std::string out = signe;
    for (size_t k = 0; k < entier.size(); ++k) {
        out += entier[k];
        const size_t reste = entier.size() - 1 - k;
        if (grouper && reste > 0 && reste % 3 == 0) out += "\xC2\xA0";
    }
    if (!frac.empty()) out += "," + frac;
    return out + exposant;
}

// « 0.05 » -> « ± 0,05 » ; « +0.1/-0.2 » -> « +0,1 / −0,2 ».
inline std::string incertitudeFr(const std::string& s) {
    if (s.empty()) return "";
    const size_t barre = s.find('/');
    if (barre == std::string::npos) return " \xC2\xB1 " + nombreFr(s[0] == '+' ? s.substr(1) : s);
    std::string haut = s.substr(0, barre), bas = s.substr(barre + 1);
    if (!haut.empty() && haut[0] == '+') haut.erase(0, 1);
    if (!bas.empty() && bas[0] == '-') bas.erase(0, 1);
    if (haut == bas) return " \xC2\xB1 " + nombreFr(haut);
    return " +" + nombreFr(haut) + " / \xE2\x88\x92" + nombreFr(bas);
}

// Valeur complète d'une ligne : limite, nombre, incertitude, unité.
inline std::string valeurFr(const Ligne& l) {
    std::string v = l.valeur, prefixe;
    if (!v.empty() && (v[0] == '<' || v[0] == '>')) {      // limite publiée
        prefixe = v[0] == '<' ? "moins de " : "plus de ";
        v.erase(0, 1);
    }
    std::string out = prefixe + nombreFr(v) + incertitudeFr(l.incertitude);
    if (!l.unite.empty()) out += " " + l.unite;
    return out;
}

// Statut puis source, comme les attend row() : « mesuré — Gaia DR3 (…) ».
inline std::string statutFr(const Ligne& l) {
    if (l.statut.empty()) return l.source;
    return l.source.empty() ? l.statut : l.statut + " \xE2\x80\x94 " + l.source;
}

class Index {
public:
    Index() = default;
    Index(const Index&) = delete;
    Index& operator=(const Index&) = delete;
    ~Index() {
        if (fil_.joinable()) fil_.join();
    }

    // Lance le parcours des fichiers de <dossier>/fiches en tâche de fond. Sans dossier : aucune fiche, rien d'autre.
    void demarrer(const std::string& dossierDonnees) {
        const std::filesystem::path dossier = std::filesystem::path(dossierDonnees) / "fiches";
        fil_ = std::thread([this, dossier]() {
            parcourir(dossier);
            pret_ = true;
        });
    }

    bool pret() const { return pret_.load(); }
    size_t nombreAstres() const { return pret() ? entrees_.size() : 0; }

    // Toutes les lignes de l'astre, dans l'ordre des fichiers puis des lignes. Vide si le parcours n'est pas fini ou s'il
    // n'a pas de fiche.
    std::vector<Ligne> lire(const std::string& cle) const {
        std::vector<Ligne> out;
        if (!pret()) return out;
        const uint64_t h = empreinte(cle);
        auto it = std::lower_bound(entrees_.begin(), entrees_.end(), Entree{h, 0, 0});
        for (; it != entrees_.end() && it->h == h; ++it) relire(*it, cle, out);
        return out;
    }

private:
    struct Colonne {
        std::string groupe, libelle, unite, statut, source;
    };
    struct Fichier {
        std::string chemin;
        bool tableau = false;
        std::vector<Colonne> colonnes;
    };
    struct Entree {
        uint64_t h;
        uint32_t fichier;
        uint64_t place;
        bool operator<(const Entree& o) const { return h != o.h ? h < o.h : fichier != o.fichier ? fichier < o.fichier : place < o.place; }
    };

    std::vector<Fichier> fichiers_;
    std::vector<Entree> entrees_;
    std::atomic<bool> pret_{false};
    std::thread fil_;

    void parcourir(const std::filesystem::path& dossier) {
        std::error_code ec;
        if (!std::filesystem::is_directory(dossier, ec)) return;
        std::vector<std::filesystem::path> chemins;
        for (const auto& e : std::filesystem::directory_iterator(dossier, ec))
            if (e.is_regular_file() && e.path().extension() == ".tsv") chemins.push_back(e.path());
        std::sort(chemins.begin(), chemins.end());      // ordre stable d'un démarrage à l'autre
        for (const auto& p : chemins) parcourirFichier(p);
        std::sort(entrees_.begin(), entrees_.end());
    }

    void parcourirFichier(const std::filesystem::path& p) {
        std::ifstream f(p, std::ios::binary);
        if (!f) return;
        Fichier fi;
        fi.chemin = p.string();
        const uint32_t numero = static_cast<uint32_t>(fichiers_.size());
        std::string l, precedente;
        bool premiere = true, enTete = true;
        uint64_t suivante = 0;      // place du début de la ligne suivante (compté ici : tellg serait lent sur des millions de lignes)
        for (;;) {
            const uint64_t place = suivante;
            if (!std::getline(f, l)) break;
            suivante += l.size() + 1;
            nettoyer(l, premiere);
            premiere = false;
            if (l.empty() || l[0] == '#') continue;
            if (l[0] == '@') {      // en-tête d'une colonne : fichier en tableau
                if (!enTete) continue;
                const std::vector<std::string> c = decouper(l);
                if (c.size() < 6) continue;
                fi.tableau = true;
                fi.colonnes.push_back({c[1], c[2], c[3], c[4], c[5]});
                continue;
            }
            enTete = false;
            const size_t tab = l.find('\t');
            if (tab == std::string::npos || tab == 0) continue;
            const std::string_view cle(l.data(), tab);
            if (!fi.tableau && cle == precedente) continue;      // format long : lignes d'un astre consécutives, place de la première
            precedente.assign(cle);
            entrees_.push_back({empreinte(cle), numero, place});
        }
        fichiers_.push_back(std::move(fi));
    }

    void relire(const Entree& e, const std::string& cle, std::vector<Ligne>& out) const {
        const Fichier& fi = fichiers_[e.fichier];
        std::ifstream f(fi.chemin, std::ios::binary);
        if (!f) return;
        f.seekg(static_cast<std::streamoff>(e.place));
        std::string l;
        while (std::getline(f, l)) {
            nettoyer(l, false);
            if (l.empty() || l[0] == '#') continue;
            const std::vector<std::string> c = decouper(l);
            if (c[0] != cle) return;      // fin des lignes de l'astre (ou autre nom de même empreinte)
            if (fi.tableau) {
                for (size_t k = 0; k < fi.colonnes.size(); ++k) {
                    const size_t iv = 1 + 2 * k, ii = iv + 1;
                    if (iv >= c.size() || c[iv].empty()) continue;
                    const Colonne& col = fi.colonnes[k];
                    out.push_back({col.groupe, col.libelle, c[iv], ii < c.size() ? c[ii] : "", col.unite, col.statut, col.source});
                }
                return;
            }
            if (c.size() < 4 || c[3].empty()) continue;
            Ligne li;
            li.groupe = c[1];
            li.libelle = c[2];
            li.valeur = c[3];
            if (c.size() > 4) li.incertitude = c[4];
            if (c.size() > 5) li.unite = c[5];
            if (c.size() > 6) li.statut = c[6];
            if (c.size() > 7) li.source = c[7];
            out.push_back(std::move(li));
        }
    }
};

}  // namespace fiches
