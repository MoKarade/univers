// Appli PC « Univers » : petits outils de texte de l'interface (recherche sans accents, dates tapées au clavier).
// Rien ici ne dépend de l'affichage : ces fonctions sont aussi vérifiées par essai_interface.cpp.
#pragma once
#include <cerrno>
#include <cstdlib>
#include <string>

namespace ui_outils {

// Minuscules sans accents, pour chercher « venus » et trouver « Vénus ». Le texte est en UTF-8.
inline std::string fold(const std::string& s) {
    // Table complète pour UTF-8 0xC3 0x80..0xBF (U+00C0 à U+00FF) ; Æ/æ sont traités à part en « ae ».
    static constexpr char kLatin1[65] =
        "aaaaaaeceeeeiiiidnoooooxouuuuyps"
        "aaaaaaeceeeeiiiidnooooo/ouuuuypy";
    static_assert(sizeof(kLatin1) == 65);
    std::string out;
    out.reserve(s.size());
    for (size_t i = 0; i < s.size(); ++i) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        if (c < 0x80) {
            out += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
            continue;
        }
        if (c == 0xC3 && i + 1 < s.size()) {
            const unsigned char b = static_cast<unsigned char>(s[i + 1]);
            if (b >= 0x80 && b <= 0xBF) {
                ++i;
                if (b == 0x86 || b == 0xA6) {  // Æ / æ
                    out += "ae";
                } else {
                    out += kLatin1[b - 0x80];
                }
                continue;
            }
        }
        if (c == 0xC5 && i + 1 < s.size()) {
            const unsigned char b = static_cast<unsigned char>(s[i + 1]);
            if (b == 0x92 || b == 0x93) {  // Œ / œ
                out += "oe";
                ++i;
                continue;
            }
            if (b == 0xB8) {  // Ÿ
                out += 'y';
                ++i;
                continue;
            }
        }
        if (c == 0xE2 && i + 2 < s.size() && static_cast<unsigned char>(s[i + 1]) == 0x80 &&
            static_cast<unsigned char>(s[i + 2]) == 0x99) {
            out += '\'';  // apostrophe typographique ’
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
    for (size_t p = n.find(q); p != std::string::npos; p = n.find(q, p + 1)) {
        if (p > 0 && (n[p - 1] == ' ' || n[p - 1] == '(' || n[p - 1] == '-' || n[p - 1] == '\'')) return 1;
    }
    return 2;
}

inline bool isLeapYear(long long y) { return (y % 4 == 0) && ((y % 100 != 0) || (y % 400 == 0)); }

inline int daysInMonth(long long y, int m) {
    static constexpr int kDays[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (m < 1 || m > 12) return 0;
    return (m == 2 && isLeapYear(y)) ? 29 : kDays[m - 1];
}

// Jour julien à 0 h TU d'une date du calendrier grégorien proleptique (algorithme de Hinnant, années astronomiques).
inline double julianDay(long long y, int m, int d) {
    y -= (m <= 2) ? 1 : 0;
    const long long era = (y >= 0 ? y : y - 399) / 400;
    const long long yoe = y - era * 400;
    const long long doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const long long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return static_cast<double>(era * 146097 + doe - 719468) + 2440587.5;
}

// Date tapée : « 1969 », « -500 », « 21/07/1969 », « 1969-07-21 », « -500-01-01 », « 1/1/-500 ».
// Rend false si le texte n'est pas une date valide. `years` : années juliennes depuis J2000,0.
inline bool parseDate(const std::string& raw, double& years) {
    std::string t;
    t.reserve(raw.size());
    for (size_t i = 0; i < raw.size(); ++i) {
        if (raw[i] == ' ') continue;
        if (i + 2 < raw.size() && static_cast<unsigned char>(raw[i]) == 0xE2 &&
            static_cast<unsigned char>(raw[i + 1]) == 0x88 &&
            static_cast<unsigned char>(raw[i + 2]) == 0x92) {
            t += '-';  // signe moins typographique
            i += 2;
            continue;
        }
        t += raw[i];
    }
    if (t.empty()) return false;

    auto parseInt = [](const char* p, const char*& next, bool allowSign, long long& out) -> bool {
        if (!p || !*p) return false;
        const char* q = p;
        if (*q == '-' || *q == '+') {
            if (!allowSign) return false;
            ++q;
        }
        if (*q < '0' || *q > '9') return false;
        char* end = nullptr;
        errno = 0;
        const long long v = std::strtoll(p, &end, 10);
        if (errno == ERANGE || !end || end == p) return false;
        next = end;
        out = v;
        return true;
    };

    long long d = 0, m = 0, y = 0;
    bool hasCal = false;
    if (t.find('/') != std::string::npos) {
        const char* p1 = nullptr;
        const char* p2 = nullptr;
        const char* p3 = nullptr;
        if (parseInt(t.c_str(), p1, false, d) && *p1 == '/' && parseInt(p1 + 1, p2, false, m) && *p2 == '/' &&
            parseInt(p2 + 1, p3, true, y) && *p3 == '\0') {
            hasCal = true;
        } else {
            return false;
        }
    } else if (t.find('-', 1) != std::string::npos) {
        const char* p1 = nullptr;
        const char* p2 = nullptr;
        const char* p3 = nullptr;
        if (parseInt(t.c_str(), p1, true, y) && *p1 == '-' && parseInt(p1 + 1, p2, false, m) && *p2 == '-' &&
            parseInt(p2 + 1, p3, false, d) && *p3 == '\0') {
            hasCal = true;
        } else {
            return false;
        }
    }
    if (hasCal) {
        if (y < -1000000000LL || y > 1000000000LL || m < 1 || m > 12) return false;
        const int mi = static_cast<int>(m);
        const int maxDay = daysInMonth(y, mi);
        if (d < 1 || d > maxDay) return false;
        years = (julianDay(y, mi, static_cast<int>(d)) - 2451545.0) / 365.25;
        return true;
    }

    const char* end = nullptr;
    long long only = 0;
    if (!parseInt(t.c_str(), end, true, only) || *end != '\0') return false;
    if (only >= -6000 && only <= 6000) years = (julianDay(only, 1, 1) - 2451545.0) / 365.25;
    else years = static_cast<double>(only) - 2000.0;
    return true;
}

}  // namespace ui_outils
