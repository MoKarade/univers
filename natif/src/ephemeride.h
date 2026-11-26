// Appli PC « Univers » : lecture directe des éphémérides de la NASA (JPL DE440), fichier .bsp tel que publié par
// le NAIF (https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp, 114 Mo, années 1550 à 2650).
//
// Format : fichier DAF / SPK (NAIF, « SPK Required Reading » et « DAF Required Reading »). Chaque segment donne la
// position d'un corps par rapport à un centre, en km, repère ICRF (équatorial J2000), par des polynômes de
// Tchebychev sur des intervalles de temps fixes (segments de type 2 : position ; type 3 : position et vitesse,
// utilisé par les fichiers des lunes). Le temps est en secondes TDB depuis J2000,0.
// Plusieurs fichiers se complètent (planètes : de440.bsp ; lunes : jup365.bsp, sat441.bsp…) : voir Set.
// Ici : aucun calcul d'orbite, seulement la lecture des polynômes de la NASA. Hors de la plage du fichier, la
// fonction répond « inconnu » (false).
#pragma once
/* Projection du fichier en mémoire : API Win32 sous Windows, mmap POSIX ailleurs (Linux, CI). Même lecture des octets. */
#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

#include <cmath>
#include <cstdint>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

namespace eph {

constexpr double kAuKm = 149597870.7;
constexpr double kObliquityJ2000 = 84381.448 / 3600.0 * 3.14159265358979323846 / 180.0;      // UAI 1976, celle des repères « écliptique J2000 » du JPL

// Codes NAIF.
enum Body : int {
    kSsb = 0, kMercuryBary = 1, kVenusBary = 2, kEmb = 3, kMarsBary = 4, kJupiterBary = 5, kSaturnBary = 6, kUranusBary = 7, kNeptuneBary = 8,
    kPlutoBary = 9, kSun = 10, kMercury = 199, kVenus = 299, kMoon = 301, kEarth = 399
};

struct Vec {
    double x = 0, y = 0, z = 0;
};

// Fichier projeté en lecture seule. Libéré à la destruction ; non copiable (Spk est gardé par pointeur dans Set).
struct MappedFile {
    const uint8_t* base = nullptr;
    uint64_t size = 0;

    MappedFile() = default;
    MappedFile(const MappedFile&) = delete;
    MappedFile& operator=(const MappedFile&) = delete;
    ~MappedFile() { close(); }

    bool open(const std::string& path, std::string& error) {
        close();
#ifdef _WIN32
        file_ = CreateFileA(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file_ == INVALID_HANDLE_VALUE) { error = "fichier introuvable : " + path; return false; }
        LARGE_INTEGER sz;
        GetFileSizeEx(file_, &sz);
        size = static_cast<uint64_t>(sz.QuadPart);
        mapping_ = CreateFileMappingA(file_, nullptr, PAGE_READONLY, 0, 0, nullptr);
        base = mapping_ ? static_cast<const uint8_t*>(MapViewOfFile(mapping_, FILE_MAP_READ, 0, 0, 0)) : nullptr;
#else
        fd_ = ::open(path.c_str(), O_RDONLY);
        if (fd_ < 0) { error = "fichier introuvable : " + path; return false; }
        struct stat st {};
        if (::fstat(fd_, &st) == 0 && st.st_size > 0) {
            size = static_cast<uint64_t>(st.st_size);
            void* p = ::mmap(nullptr, static_cast<size_t>(size), PROT_READ, MAP_PRIVATE, fd_, 0);
            base = p == MAP_FAILED ? nullptr : static_cast<const uint8_t*>(p);
        }
#endif
        if (!base) { error = "projection en mémoire impossible : " + path; return false; }
        return true;
    }

    void close() {
#ifdef _WIN32
        if (base) UnmapViewOfFile(base);
        if (mapping_) CloseHandle(mapping_);
        if (file_ != INVALID_HANDLE_VALUE) CloseHandle(file_);
        file_ = INVALID_HANDLE_VALUE;
        mapping_ = nullptr;
#else
        if (base) ::munmap(const_cast<uint8_t*>(base), static_cast<size_t>(size));
        if (fd_ >= 0) ::close(fd_);
        fd_ = -1;
#endif
        base = nullptr;
        size = 0;
    }

private:
#ifdef _WIN32
    HANDLE file_ = INVALID_HANDLE_VALUE, mapping_ = nullptr;
#else
    int fd_ = -1;
#endif
};

class Spk {
public:
    bool open(const std::string& path, std::string& error) {
        if (!map_.open(path, error)) return false;
        base_ = map_.base;
        size_ = map_.size;
        if (size_ < 1024 || std::memcmp(base_, "DAF/SPK", 7) != 0) { error = "ce n'est pas un fichier SPK du NAIF"; return false; }
        if (std::memcmp(base_ + 88, "LTL-IEEE", 8) != 0) { error = "fichier SPK non petit-boutiste"; return false; }
        int32_t nd, ni, fward;
        std::memcpy(&nd, base_ + 8, 4);
        std::memcpy(&ni, base_ + 12, 4);
        std::memcpy(&fward, base_ + 76, 4);
        if (nd != 2 || ni != 6) { error = "fichier SPK inattendu (ND, NI)"; return false; }
        // Chaîne des enregistrements de résumés : suivant, précédent, nombre, puis les résumés (2 réels, 6 entiers).
        for (int rec = fward; rec > 0;) {
            const uint8_t* r = record(rec);
            if (!r) { error = "fichier SPK tronqué"; return false; }
            double next, count;
            std::memcpy(&next, r, 8);
            std::memcpy(&count, r + 16, 8);
            for (int i = 0; i < static_cast<int>(count); ++i) {
                const uint8_t* s = r + 24 + i * 40;
                Segment seg;
                int32_t ints[6];
                std::memcpy(&seg.start, s, 8);
                std::memcpy(&seg.end, s + 8, 8);
                std::memcpy(ints, s + 16, 24);
                seg.target = ints[0];
                seg.center = ints[1];
                seg.frame = ints[2];
                seg.type = ints[3];
                const uint64_t first = static_cast<uint64_t>(ints[4]), last = static_cast<uint64_t>(ints[5]);
                if ((seg.type != 2 && seg.type != 3) || seg.frame != 1 || last * 8 > size_ || last < first + 4) continue;      // segments Tchebychev, ICRF
                const double* tail = word(last - 3);      // les 4 derniers réels : début, durée d'un intervalle, taille d'un enregistrement, nombre
                seg.init = tail[0];
                seg.intlen = tail[1];
                seg.rsize = static_cast<int>(tail[2]);
                seg.n = static_cast<int>(tail[3]);
                seg.data = word(first);
                if (seg.rsize < 5 || seg.n < 1) continue;
                segments_.push_back(seg);
            }
            rec = static_cast<int>(next);
        }
        if (segments_.empty()) { error = "aucun segment lisible"; return false; }
        return true;
    }

    // Plage de dates couverte par tous les segments (secondes TDB depuis J2000,0).
    double firstEt() const { double v = -1e300; for (const auto& s : segments_) v = std::max(v, s.start); return v; }
    double lastEt() const { double v = 1e300; for (const auto& s : segments_) v = std::min(v, s.end); return v; }

    // Un pas de la chaîne : position et vitesse d'un corps par rapport à son centre dans ce fichier. false : pas ici.
    bool step(int body, double et, Vec& pos, Vec& vel, int& center) const {
        const Segment* seg = find(body, et);
        if (!seg) return false;
        evaluate(*seg, et, pos, vel);
        center = seg->center;
        return true;
    }

    // Position et vitesse d'un corps par rapport au centre de masse du système solaire, en km et km/s, repère ICRF.
    bool state(int body, double et, Vec& pos, Vec& vel) const {
        pos = {};
        vel = {};
        for (int guard = 0; body != kSsb && guard < 8; ++guard) {
            const Segment* seg = find(body, et);
            if (!seg) return false;
            Vec p, v;
            evaluate(*seg, et, p, v);
            pos = {pos.x + p.x, pos.y + p.y, pos.z + p.z};
            vel = {vel.x + v.x, vel.y + v.y, vel.z + v.z};
            body = seg->center;
        }
        return body == kSsb;
    }


private:
    struct Segment {
        double start = 0, end = 0, init = 0, intlen = 0;
        int target = 0, center = 0, frame = 0, type = 0, rsize = 0, n = 0;
        const double* data = nullptr;
    };

    const uint8_t* record(int rec) const {      // enregistrements de 1024 octets, numérotés à partir de 1
        const uint64_t off = static_cast<uint64_t>(rec - 1) * 1024;
        return off + 1024 <= size_ ? base_ + off : nullptr;
    }
    const double* word(uint64_t address) const { return reinterpret_cast<const double*>(base_ + (address - 1) * 8); }      // adresses en réels, à partir de 1

    const Segment* find(int target, double et) const {
        for (const auto& s : segments_)
            if (s.target == target && et >= s.start && et <= s.end) return &s;
        return nullptr;
    }

    static void evaluate(const Segment& seg, double et, Vec& pos, Vec& vel) {
        int i = static_cast<int>(std::floor((et - seg.init) / seg.intlen));
        i = std::min(std::max(i, 0), seg.n - 1);
        const double* r = seg.data + static_cast<size_t>(i) * seg.rsize;
        const double mid = r[0], radius = r[1];
        const int nc = (seg.rsize - 2) / (seg.type == 3 ? 6 : 3);      // type 3 : les coefficients de vitesse suivent ceux de position (non lus : on dérive)
        const double t = (et - mid) / radius;
        // Polynômes de Tchebychev T_k(t) et leurs dérivées, par récurrence.
        double T[32], D[32];
        T[0] = 1; T[1] = t; D[0] = 0; D[1] = 1;
        const int n = std::min(nc, 32);
        for (int k = 2; k < n; ++k) {
            T[k] = 2 * t * T[k - 1] - T[k - 2];
            D[k] = 2 * T[k - 1] + 2 * t * D[k - 1] - D[k - 2];
        }
        double p[3] = {0, 0, 0}, v[3] = {0, 0, 0};
        for (int a = 0; a < 3; ++a) {
            const double* c = r + 2 + a * nc;
            for (int k = 0; k < n; ++k) {
                p[a] += c[k] * T[k];
                v[a] += c[k] * D[k];
            }
            v[a] /= radius;
        }
        pos = {p[0], p[1], p[2]};
        vel = {v[0], v[1], v[2]};
    }

    MappedFile map_;
    const uint8_t* base_ = nullptr;
    uint64_t size_ = 0;
    std::vector<Segment> segments_;
};

// Plusieurs fichiers lus ensemble : un corps peut être donné dans un fichier par rapport à un centre décrit dans un
// autre (Io par rapport au centre de masse de Jupiter dans jup365.bsp, ce centre de masse par rapport à celui du
// système solaire dans de440.bsp). Les fichiers sont interrogés dans l'ordre où ils ont été ajoutés.
class Set {
public:
    bool add(const std::string& path, std::string& error) {
        auto f = std::make_unique<Spk>();
        if (!f->open(path, error)) return false;
        files_.push_back(std::move(f));
        return true;
    }
    bool empty() const { return files_.empty(); }
    bool state(int body, double et, Vec& pos, Vec& vel) const {
        pos = {};
        vel = {};
        for (int guard = 0; body != kSsb && guard < 8; ++guard) {
            Vec p, v;
            int center = 0;
            bool found = false;
            for (const auto& f : files_)
                if (f->step(body, et, p, v, center)) { found = true; break; }
            if (!found) return false;
            pos = {pos.x + p.x, pos.y + p.y, pos.z + p.z};
            vel = {vel.x + v.x, vel.y + v.y, vel.z + v.z};
            body = center;
        }
        return body == kSsb;
    }

private:
    std::vector<std::unique_ptr<Spk>> files_;
};

// Équatorial J2000 (ICRF) -> écliptique J2000 : rotation autour de l'axe x de l'obliquité.
inline Vec toEcliptic(Vec e) {
    const double c = std::cos(kObliquityJ2000), s = std::sin(kObliquityJ2000);
    return {e.x, c * e.y + s * e.z, -s * e.y + c * e.z};
}

// Jour julien (TDB) -> secondes TDB depuis J2000,0.
inline double etOfJd(double jd) { return (jd - 2451545.0) * 86400.0; }

}  // namespace eph
