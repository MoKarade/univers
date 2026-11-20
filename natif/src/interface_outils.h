// Appli PC « Univers » : petits outils de texte de l'interface (recherche sans accents, dates tapées au clavier).
// Rien ici ne dépend de l'affichage : ces fonctions sont aussi vérifiées par essai_interface.cpp.
#pragma once
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace ui_outils {

// Minuscules sans accents, pour chercher « venus » et trouver « Vénus ». Le texte est en UTF-8.
inline std::string fold(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (size_t i = 0; i < s.size(); ++i) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        if (c < 0x80) {
            out += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
            continue;
        }
        if (c == 0xC3 && i + 1 < s.size()) {      // lettres latines accentuées (U+00C0 à U+00FF)
            const unsigned char d = static_cast<unsigned char>(s[++i]) & 0x1F;      // même lettre en majuscule et en minuscule
            const char* map = "aaaaaaeceeeeiiiidnooooo/ouuuuyps";
            out += map[d];
            continue;
        }
        if (c == 0xE2 && i + 2 < s.size() && static_cast<unsigned char>(s[i + 1]) == 0x80 && static_cast<unsigned char>(s[i + 2]) == 0x99) {
            out += '\'';      // apostrophe typographique ’
            i += 2;
            continue;
        }
        out += static_cast<char>(c);
    }
    return out;
}

// Rang d'un nom pour une recherche : 0 = commence par le texte, 1 = un mot commence par le texte, 2 = le contient,
// -1 = ne correspond pas. `q` est déjà passé par fold().
inline int matchRank(const std::string& name, const std::string& q) {
    if (q.empty()) return -1;
    const std::string n = fold(name);
    const size_t at = n.find(q);
    if (at == std::string::npos) return -1;
    if (at == 0) return 0;
    for (size_t p = n.find(q); p != std::string::npos; p = n.find(q, p + 1))
        if (p > 0 && (n[p - 1] == ' ' || n[p - 1] == '(' || n[p - 1] == '-' || n[p - 1] == '\'')) return 1;
    return 2;
}

// Jour julien à 0 h TU d'une date du calendrier grégorien (Fliegel et Van Flandern 1968, années astronomiques).
inline double julianDay(long long y, long long m, long long d) {
    const long long a = (m - 14) / 12;
    const long long jdn = (1461 * (y + 4800 + a)) / 4 + (367 * (m - 2 - 12 * a)) / 12 - (3 * ((y + 4900 + a) / 100)) / 4 + d - 32075;
    return static_cast<double>(jdn) - 0.5;
}

// Date tapée : « 1969 », « -500 », « 21/07/1969 », « 1969-07-21 ». Rend false si le texte n'est pas une date.
// `years` : années juliennes depuis J2000,0 (même échelle que le simulateur).
inline bool parseDate(const std::string& raw, double& years) {
    std::string t;
    for (char c : raw)
        if (c != ' ') t += c;
    if (t.size() >= 3 && static_cast<unsigned char>(t[0]) == 0xE2 && static_cast<unsigned char>(t[1]) == 0x88 && static_cast<unsigned char>(t[2]) == 0x92)
        t = "-" + t.substr(3);      // signe moins typographique
    if (t.empty()) return false;
    long long d = 0, m = 0, y = 0;
    char extra = 0;
    if (std::sscanf(t.c_str(), "%lld/%lld/%lld%c", &d, &m, &y, &extra) == 3 || std::sscanf(t.c_str(), "%lld-%lld-%lld%c", &y, &m, &d, &extra) == 3) {
        if (t[0] == '-' && t.find('/') == std::string::npos) return false;      // « -500-01-01 » : ambigu, refusé
        if (m < 1 || m > 12 || d < 1 || d > 31) return false;
        years = (julianDay(y, m, d) - 2451545.0) / 365.25;
        return true;
    }
    char* end = nullptr;
    const long long only = std::strtoll(t.c_str(), &end, 10);
    if (!end || *end || end == t.c_str()) return false;
    if (std::llabs(only) <= 6000) years = (julianDay(only, 1, 1) - 2451545.0) / 365.25;
    else years = static_cast<double>(only) - 2000.0;
    return true;
}

// Index de recherche pour une très longue liste de noms (1,58 million d'astéroïdes) : tous les noms, passés par fold(),
// mis bout à bout dans un seul texte. Une recherche est alors une suite de find() sur ce texte, sans copie : environ 1 ms
// au lieu de 25 ms en recopiant chaque nom (mesuré le 12/11/2026 sur le catalogue complet du JPL ; construction 42 ms).
struct NameIndex {
    std::string all;                 // noms en minuscules sans accents, chacun suivi de '\n'
    std::vector<uint32_t> start;     // début de chaque nom dans `all`, plus la fin du texte
    std::vector<int> order;          // rang d'origine de chaque nom de l'index (vide : même ordre que la liste)
    bool built = false;

    // `first` : les noms à mettre en tête (ex. les comètes, pour que « halley » trouve 1P/Halley avant l'astéroïde 2688) ;
    // les autres suivent dans l'ordre de la liste.
    void build(const std::vector<std::string>& names, const std::vector<char>& first = {}) {
        all.clear();
        start.clear();
        order.clear();
        start.reserve(names.size() + 1);
        if (!first.empty()) {
            order.reserve(names.size());
            for (int pass = 0; pass < 2; ++pass)
                for (size_t k = 0; k < names.size(); ++k)
                    if ((k < first.size() && first[k]) == (pass == 0)) order.push_back(static_cast<int>(k));
        }
        for (size_t i = 0; i < names.size(); ++i) {
            start.push_back(static_cast<uint32_t>(all.size()));
            all += fold(names[order.empty() ? i : static_cast<size_t>(order[i])]);
            all += '\n';
        }
        start.push_back(static_cast<uint32_t>(all.size()));
        built = true;
    }
    // Rangs des `max` premiers noms qui contiennent `text` (au moins 2 caractères), dans l'ordre de la liste.
    std::vector<int> find(const std::string& text, int max) const {
        std::vector<int> out;
        const std::string q = fold(text);
        if (q.size() < 2 || q.find('\n') != std::string::npos) return out;
        for (size_t pos = 0; static_cast<int>(out.size()) < max && (pos = all.find(q, pos)) != std::string::npos;) {
            const int k = static_cast<int>(std::upper_bound(start.begin(), start.end(), static_cast<uint32_t>(pos)) - start.begin()) - 1;
            out.push_back(order.empty() ? k : order[static_cast<size_t>(k)]);
            pos = start[static_cast<size_t>(k) + 1];      // un nom ne compte qu'une fois
        }
        return out;
    }
};

// ---------------------------------------------------------------- statut d'une valeur (refonte de l'interface, 20/11/2026)

// Statut d'une valeur affichée, lu dans le texte libre que chaque ligne de fiche porte déjà (« mesuré », « calculé d'après
// la couleur », « mesuré (JPL Small-Body Database) », « modèle — MIST v1.2 »…). Il donne la couleur de la pastille ;
// le reste du texte (la source, la méthode) reste affiché en dessous, rien n'est retiré.
enum class Statut { Aucun, Mesure, Publie, Calcule, Modele, Suppose, Inconnu };

inline Statut statutDe(const std::string& raw) {
    const std::string s = fold(raw);
    if (s.empty()) return Statut::Aucun;
    // Le mot le plus prudent l'emporte : « calculé, approché (supposé…) » est une supposition, pas un calcul sûr.
    if (s.find("suppos") != std::string::npos || s.find("hypoth") != std::string::npos || s.find("extrapol") != std::string::npos) return Statut::Suppose;
    if (s.find("modele") != std::string::npos || s.find("scenario") != std::string::npos) return Statut::Modele;
    if (s.find("non mesure") != std::string::npos || s.find("inconnu") != std::string::npos) return Statut::Inconnu;
    if (s.rfind("calcul", 0) == 0) return Statut::Calcule;
    if (s.rfind("publie", 0) == 0) return Statut::Publie;
    if (s.rfind("mesure", 0) == 0 || s.find("ephemerides") != std::string::npos) return Statut::Mesure;
    if (s.find("calcul") != std::string::npos) return Statut::Calcule;
    return Statut::Aucun;
}

// Mot court de la pastille.
inline const char* statutMot(Statut s) {
    switch (s) {
        case Statut::Mesure: return "mesuré";
        case Statut::Publie: return "publié";
        case Statut::Calcule: return "calculé";
        case Statut::Modele: return "modèle";
        case Statut::Suppose: return "supposé";
        case Statut::Inconnu: return "inconnu";
        default: return "";
    }
}

// Ce qui reste du texte une fois le mot de statut retiré du début : « (JPL Small-Body Database) » → « JPL Small-Body
// Database » ; « calculé d'après la couleur » → « d'après la couleur ». Texte d'origine si le mot n'est pas au début.
inline std::string statutReste(const std::string& raw, Statut st) {
    const std::string mot = statutMot(st);
    if (mot.empty() || raw.compare(0, mot.size(), mot) != 0) return raw;
    std::string r = raw.substr(mot.size());
    while (!r.empty() && (r[0] == ' ' || r[0] == ',' || r[0] == ':' || r[0] == ';')) r.erase(0, 1);
    if (r.rfind("\xE2\x80\x94", 0) == 0) r.erase(0, 3);      // tiret long « — »
    while (!r.empty() && r[0] == ' ') r.erase(0, 1);
    if (r.size() >= 2 && r.front() == '(' && r.back() == ')' && r.find('(', 1) == std::string::npos) r = r.substr(1, r.size() - 2);
    return r;
}

// Échelles de la vue (touches 1 à 5) : où se trouve la caméra entre deux échelles, en fraction de l'échelle (log de la
// distance). 0 = première échelle, n-1 = dernière ; bornée.
inline double positionEchelle(double distLy, const double* echelles, int n) {
    if (n <= 0 || distLy <= 0) return 0;
    if (distLy <= echelles[0]) return 0;
    for (int k = 0; k + 1 < n; ++k)
        if (distLy <= echelles[k + 1]) return k + std::log(distLy / echelles[k]) / std::log(echelles[k + 1] / echelles[k]);
    return n - 1;
}

}  // namespace ui_outils
