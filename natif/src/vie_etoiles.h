// Appli PC « Univers » : la vie de chaque étoile. Éclat et couleur MESURÉS aujourd'hui, plus le changement CALCULÉ par
// les modèles entre aujourd'hui et la date affichée (choix de Marc, 13/11/2026 : « que du mesuré » au présent).
//
// Fichiers (dossier vie/ des données, pipeline/natif) :
//   mist_traces.bin     trajectoires MIST v1.2 dans les bandes de Gaia et de Johnson (mist_gaia.py) ;
//   naines_blanches.bin refroidissement des naines blanches, modèles de Montréal (naines_blanches.py) ;
//   vie_a.bin, vie_b.bin, vie_principal.bin : place de chaque étoile sur sa trajectoire (etoiles_vie.py).
//
// Calcul (sur le processeur, dans des fils à part ; la carte graphique ne reçoit que les étoiles qui changent) :
//   âge aujourd'hui = âge du modèle au point de l'étoile ; âge à la date = âge aujourd'hui + temps écoulé depuis les mesures ;
//   magnitude affichée = magnitude mesurée + (magnitude du modèle à la date - magnitude du modèle aujourd'hui), idem couleur.
//   Avant la naissance : l'étoile n'est pas là. Après la trace : supernova (courbe de lumière moyenne d'une supernova de
//   type II, puis rien de visible : étoile à neutrons ou trou noir), ou naine blanche qui refroidit (modèles de Montréal).
// À la date des mesures, aucun mot n'est changé : l'image est celle d'avant, octet pour octet.
#pragma once
#include "commun.h"
#include <atomic>
#include <mutex>
#include <thread>

namespace vie {

// Supernova de type II : plateau puis déclin (Anderson et al. 2014, ApJ 786, 67 : M_V au plateau ~ -16,7, plateau ~100 j,
// déclin radioactif ~0,01 mag/jour). [Probable : valeurs moyennes ; chaque supernova diffère, dit à l'écran]
constexpr double kSnPeak = -16.7, kSnPlateauDays = 100.0, kSnFadePerDay = 0.0098, kSnColor = 0.4;
constexpr float kHidden = 60.0f;      // magnitude absolue d'une étoile absente (pas née, ou reste invisible)
constexpr double kYearDays = 365.25;

struct Rec {      // 8 octets, etoiles_vie.py
    uint16_t trace, eep32;
    uint8_t flags, lo, hi, reserve;
};
static_assert(sizeof(Rec) == 8, "vie_*.bin : 8 octets par étoile");
enum Source : uint8_t { kUnknown = 0, kFlame = 1, kDiagram = 2, kDiagramRaw = 3 };

inline const uint8_t* mapFile(const std::string& path, uint64_t& size) {
    const HANDLE file = CreateFileA(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return nullptr;
    LARGE_INTEGER s;
    GetFileSizeEx(file, &s);
    size = static_cast<uint64_t>(s.QuadPart);
    const HANDLE mapping = CreateFileMappingA(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
    return mapping ? static_cast<const uint8_t*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0)) : nullptr;
}

// Trajectoires MIST (format : pipeline/natif/mist_gaia.py).
struct Traces {
    uint32_t n = 0, nEep = 0;
    const float* masses = nullptr;
    const uint32_t* used = nullptr;
    const uint8_t* ends = nullptr;      // 0 : naine blanche ; 1 : supernova
    const uint8_t* body = nullptr;
    size_t stride = 0;
    bool open(const std::string& path) {
        uint64_t size = 0;
        const uint8_t* b = mapFile(path, size);
        if (!b || size < 16 || std::memcmp(b, "UNIVMST1", 8) != 0) return false;
        std::memcpy(&n, b + 8, 4);
        std::memcpy(&nEep, b + 12, 4);
        size_t o = 16;
        masses = reinterpret_cast<const float*>(b + o);
        o += 4ull * n;
        used = reinterpret_cast<const uint32_t*>(b + o);
        o += 4ull * n;
        ends = b + o;
        o += n;
        o += (16 - o % 16) % 16;
        body = b + o;
        stride = 3ull * 8 * nEep + 6ull * 4 * nEep + nEep;
        return size >= o + stride * n;
    }
    const double* age(uint32_t t) const { return reinterpret_cast<const double*>(body + stride * t); }
    const double* calmLo(uint32_t t) const { return age(t) + nEep; }
    const double* calmHi(uint32_t t) const { return age(t) + 2 * nEep; }
    // bandes : 0 G, 1 BP-RP, 2 V, 3 B-V, 4 log L, 5 log Teff
    const float* band(uint32_t t, int k) const { return reinterpret_cast<const float*>(body + stride * t + 3ull * 8 * nEep) + static_cast<size_t>(k) * nEep; }
    uint8_t phase(uint32_t t, double e) const {
        return (body + stride * t + 3ull * 8 * nEep + 6ull * 4 * nEep)[std::clamp(static_cast<long>(e), 0L, static_cast<long>(used[t]) - 1)];
    }
    template <class T>
    static double at(const T* v, double e, uint32_t m) {
        const double c = std::clamp(e, 0.0, static_cast<double>(m - 1));
        const uint32_t j = std::min(static_cast<uint32_t>(c), m - 2);
        const double f = c - j;
        return (1 - f) * v[j] + f * v[j + 1];
    }
    // Point d'évolution (fractionnaire) à l'âge donné ; l'âge doit être dans la trace.
    double eepAt(uint32_t t, double a) const {
        const double* A = age(t);
        const uint32_t m = used[t];
        uint32_t lo = 0, hi = m - 1;
        while (hi - lo > 1) {
            const uint32_t mid = (lo + hi) / 2;
            if (A[mid] <= a) lo = mid;
            else hi = mid;
        }
        const double d = A[hi] - A[lo];
        return lo + (d > 0 ? std::clamp((a - A[lo]) / d, 0.0, 1.0) : 1.0);
    }
};

// Naines blanches (format : pipeline/natif/naines_blanches.py).
struct WhiteDwarfs {
    uint32_t nm = 0, np = 0;
    const float* masses = nullptr;
    const uint8_t* body = nullptr;
    bool open(const std::string& path) {
        uint64_t size = 0;
        const uint8_t* b = mapFile(path, size);
        if (!b || size < 16 || std::memcmp(b, "UNIVNBL1", 8) != 0) return false;
        std::memcpy(&nm, b + 8, 4);
        std::memcpy(&np, b + 12, 4);
        masses = reinterpret_cast<const float*>(b + 16);
        body = b + 16 + 4ull * nm;
        return size >= 16 + 4ull * nm + (8ull + 16ull) * np * nm;
    }
    // Masse finale d'après la masse initiale (Cummings et al. 2018, version MIST ; voir naines_blanches.py).
    static double finalMass(double mi) {
        if (mi < 2.85) return 0.080 * mi + 0.489;
        if (mi < 3.60) return 0.187 * mi + 0.184;
        return 0.107 * mi + 0.471;
    }
    // band : 0 G, 1 BP-RP, 2 V, 3 B-V ; tCool : années depuis la fin de la trace MIST.
    double value(double mi, double tCool, int band) const {
        const double mf = std::clamp(finalMass(mi), static_cast<double>(masses[0]), static_cast<double>(masses[nm - 1]));
        uint32_t k = 0;
        while (k + 2 < nm && masses[k + 1] < mf) ++k;
        const double w = std::clamp((mf - masses[k]) / (masses[k + 1] - masses[k]), 0.0, 1.0);
        return (1 - w) * one(k, tCool, band) + w * one(k + 1, tCool, band);
    }
    double one(uint32_t k, double t, int band) const {
        const uint8_t* s = body + static_cast<size_t>(k) * (8ull + 16ull) * np;
        const double* A = reinterpret_cast<const double*>(s);
        const float* v = reinterpret_cast<const float*>(s + 8ull * np) + static_cast<size_t>(band) * np;
        if (t <= A[0]) return v[0];
        if (t >= A[np - 1]) return v[np - 1];
        uint32_t j = 0;
        while (A[j + 1] < t) ++j;
        const double f = (t - A[j]) / std::max(A[j + 1] - A[j], 1.0);
        return (1 - f) * v[j] + f * v[j + 1];
    }
};

// Ce que le modèle dit d'une étoile à une date : écart de magnitude et de couleur au modèle d'aujourd'hui, ou absente.
struct Change {
    bool same = true;      // rien à changer (fenêtre calme, source inconnue, date des mesures)
    bool hidden = false;   // pas encore née, ou reste invisible
    double dMag = 0, dColor = 0;
};

class Engine {
public:
    Traces tr;
    WhiteDwarfs wd;
    bool ready = false;
    bool open(const std::string& dir) {
        ready = tr.open(dir + "/mist_traces.bin") && wd.open(dir + "/naines_blanches.bin");
        return ready;
    }
    // johnson : bandes V et B-V (catalogue principal) au lieu de G et BP-RP.
    Change at(const Rec& r, double dt, bool johnson) const {
        Change c;
        if ((r.flags & 3) == kUnknown || dt == 0.0 || r.trace >= tr.n) return c;
        const uint32_t t = r.trace, m = tr.used[t];
        const double e0 = r.eep32 / 32.0;
        const double* A = tr.age(t);
        const double now = Traces::at(A, e0, m), goal = now + dt;
        const uint32_t j0 = static_cast<uint32_t>(std::min<double>(std::lround(e0), m - 1));
        const double lo = tr.calmLo(t)[j0], hi = tr.calmHi(t)[j0];
        if (lo < hi && goal >= lo && goal <= hi) return c;
        const int bm = johnson ? 2 : 0, bc = johnson ? 3 : 1;
        const double magNow = Traces::at(tr.band(t, bm), e0, m), colNow = Traces::at(tr.band(t, bc), e0, m);
        c.same = false;
        if (goal < A[0]) { c.hidden = true; return c; }      // pas encore née
        if (goal <= A[m - 1]) {
            const double e = tr.eepAt(t, goal);
            c.dMag = Traces::at(tr.band(t, bm), e, m) - magNow;
            c.dColor = Traces::at(tr.band(t, bc), e, m) - colNow;
            return c;
        }
        const double after = goal - A[m - 1];
        if (tr.ends[t]) {      // supernova, puis plus rien de visible
            const double days = after * kYearDays;
            if (days > kSnPlateauDays + 2000.0) { c.hidden = true; return c; }
            // la courbe moyenne est en V ; l'écart G - V d'une supernova au plateau est faible [Supposition, dite en fiche]
            c.dMag = kSnPeak + std::max(0.0, days - kSnPlateauDays) * kSnFadePerDay - magNow;
            c.dColor = kSnColor - colNow;
            return c;
        }
        const int wm = johnson ? 2 : 0, wc = johnson ? 3 : 1;
        c.dMag = wd.value(tr.masses[t], after, wm) - magNow;
        c.dColor = wd.value(tr.masses[t], after, wc) - colNow;
        return c;
    }
    // Soleil : 1 masse solaire, âge mesuré par les météorites (4,567 milliards d'années, Connelly et al. 2012), [Fe/H] = 0.
    static constexpr double kSunAge = 4.567e9;
    Rec sunRec() const {
        Rec r{};
        const double lm = std::log(tr.masses[0]), step = std::log(tr.masses[1] / tr.masses[0]);
        r.trace = static_cast<uint16_t>(std::lround(-lm / step));
        r.flags = kDiagram;
        r.eep32 = static_cast<uint16_t>(std::lround(tr.eepAt(r.trace, kSunAge) * 32.0));
        r.lo = r.hi = 0;
        return r;
    }
    // Pour la fiche : masse initiale, âge aujourd'hui, âge à la date, phase, fin (années restantes depuis aujourd'hui).
    struct Card { bool known = false; uint8_t source = 0; double mass = 0, ageNow = 0, ageLo = 0, ageHi = 0, lifeLeft = 0; uint8_t phaseThen = 255; bool supernova = false; };
    Card card(const Rec& r, double dt) const {
        Card k;
        if ((r.flags & 3) == kUnknown || r.trace >= tr.n) return k;
        const uint32_t t = r.trace, m = tr.used[t];
        const double e0 = r.eep32 / 32.0;
        k.known = true;
        k.source = r.flags & 3;
        k.mass = tr.masses[t];
        k.ageNow = Traces::at(tr.age(t), e0, m);
        k.ageLo = r.lo == 255 ? 0 : k.ageNow / std::pow(10.0, r.lo / 100.0);
        k.ageHi = r.hi == 255 ? 0 : k.ageNow * std::pow(10.0, r.hi / 100.0);
        k.lifeLeft = tr.age(t)[m - 1] - k.ageNow;
        k.supernova = tr.ends[t] != 0;
        const double g = k.ageNow + dt;
        k.phaseThen = g < tr.age(t)[0] ? 254 : g > tr.age(t)[m - 1] ? (k.supernova ? 200 : 201) : tr.phase(t, tr.eepAt(t, g));
        return k;
    }
};

// Nom de phase pour la fiche (phases MIST, Dotter 2016 ; 200 et 201 : après la trace).
inline const char* phaseName(uint8_t p) {
    switch (p) {
        case 254: return "pas encore née (ou très jeune étoile en formation)";
        case 0: return "séquence principale (brûle l'hydrogène en son centre)";
        case 2: return "géante rouge (brûle l'hydrogène autour de son centre)";
        case 3: return "brûle l'hélium en son centre";
        case 4: case 5: return "géante de la branche asymptotique";
        case 6: return "devient naine blanche";
        case 9: return "étoile de Wolf-Rayet";
        case 200: return "a explosé en supernova (reste : étoile à neutrons ou trou noir, invisibles ici)";
        case 201: return "naine blanche qui refroidit";
        default: return "phase non suivie";
    }
}
inline const char* sourceName(uint8_t s) {
    switch (s) {
        case kFlame: return "âge et masse mesurés par Gaia (FLAME, DR3)";
        case kDiagram: return "âge déduit de l'éclat et de la couleur mesurés, poussière mesurée retirée";
        case kDiagramRaw: return "âge déduit de l'éclat et de la couleur mesurés (poussière non retirée)";
        default: return "inconnu";
    }
}

inline uint16_t floatToHalf(float f) {
    uint32_t x;
    std::memcpy(&x, &f, 4);
    const uint32_t s = (x >> 16) & 0x8000u;
    int e = static_cast<int>((x >> 23) & 0xff) - 127 + 15;
    uint32_t m = x & 0x7fffffu;
    if (e <= 0) return static_cast<uint16_t>(s);
    if (e >= 31) return static_cast<uint16_t>(s | 0x7c00u);
    m += 0x1000u;      // arrondi
    if (m & 0x800000u) { m = 0; ++e; if (e >= 31) return static_cast<uint16_t>(s | 0x7c00u); }
    return static_cast<uint16_t>(s | (static_cast<uint32_t>(e) << 10) | (m >> 13));
}

// Un jeu d'étoiles Gaia (gaia.bin ou gaia_b.bin) : mots mesurés, mots montrés, et ce que l'appli doit savoir des feuilles.
struct GaiaSet {
    const uint8_t* stars = nullptr;      // gaia.bin, 16 octets par étoile (magnitude f16 à +12, couleur u8 à +14)
    uint64_t n = 0;
    const Rec* rec = nullptr;
    std::vector<uint32_t> shown;         // dernier mot envoyé à la carte (ou mot mesuré)
    // feuilles : première étoile et nombre ; tranches de magnitude du résumé (gaia.bin)
    std::vector<std::pair<uint64_t, uint32_t>> leaves;
    uint32_t bins = 0;
    float bin0 = 0, binWidth = 1;
    std::vector<float> leafGain, leafDelta;      // calcul en cours : éclat gagné au plus (mag), écart de lumière par tranche (10^(-0,4 M))
    std::vector<float> gainShown, deltaShown;    // mêmes valeurs, pour la date montrée (lues par gaia.h, échangées après l'envoi)
    std::vector<std::pair<uint32_t, uint32_t>> changes;      // (étoile, mot) à envoyer
    uint64_t count[4]{};      // étoiles par source
    uint64_t changed = 0, hidden = 0;
    uint32_t measuredWord(uint64_t i) const {
        uint32_t w;
        std::memcpy(&w, stars + i * 16 + 12, 4);
        return w;
    }
    bool attach(const std::string& viePath, const uint8_t* gaiaStars, uint64_t count0) {
        uint64_t size = 0;
        const uint8_t* b = mapFile(viePath, size);
        if (!b || size < 16 || std::memcmp(b, "UNIVVIE1", 8) != 0) return false;
        uint64_t nv = 0;
        std::memcpy(&nv, b + 8, 8);
        if (nv != count0 || size < 16 + nv * 8) return false;
        stars = gaiaStars;
        n = nv;
        rec = reinterpret_cast<const Rec*>(b + 16);
        shown.resize(n);
        for (uint64_t i = 0; i < n; ++i) {
            shown[i] = measuredWord(i);
            ++count[rec[i].flags & 3];
        }
        return true;
    }
};

// Catalogue principal (étoiles brillantes nommées) : V et B-V, petites colonnes renvoyées entières à la carte.
struct MainSet {
    const float* mag = nullptr;
    const float* bv = nullptr;
    uint64_t n = 0;
    const Rec* rec = nullptr;
    std::vector<float> magShown, bvShown;      // date montrée (lues par l'interface, fil principal)
    std::vector<float> magNext, bvNext;        // calcul en cours (fil de fond), échangées à l'envoi
    bool dirty = false;
    bool attach(const std::string& viePath, const float* m, const float* b, uint64_t count0) {
        uint64_t size = 0;
        const uint8_t* f = mapFile(viePath, size);
        if (!f || size < 16 || std::memcmp(f, "UNIVVIE1", 8) != 0) return false;
        uint64_t nv = 0;
        std::memcpy(&nv, f + 8, 8);
        if (nv < count0 || size < 16 + nv * 8) return false;
        mag = m;
        bv = b;
        n = count0;
        rec = reinterpret_cast<const Rec*>(f + 16);
        magShown.assign(m, m + n);
        bvShown.assign(b, b + n);
        magNext = magShown;
        bvNext = bvShown;
        return true;
    }
};

// Calcul de fond : à chaque nouvelle date demandée, recalcule tous les jeux dans des fils, puis rend la main à l'appli,
// qui envoie les changements à la carte (applyGaia, applyMain) avant de redemander.
class Life {
public:
    Engine engine;
    std::vector<GaiaSet*> gaia;
    MainSet* main = nullptr;
    double sunDMag = 0, sunDBv = 0;
    bool sunHidden = false;
    std::atomic<bool> busy{false}, done{false};
    double computedDt = 0;      // date (années depuis les mesures) des derniers résultats prêts
    double appliedDt = 0;       // date des résultats envoyés à la carte
    double lastMs = 0;          // durée du dernier calcul complet
    bool request(double dt) {
        if (!engine.ready || busy.load() || done.load()) return false;
        if (dt == appliedDt) return false;
        busy = true;
        if (worker_.joinable()) worker_.join();
        worker_ = std::thread([this, dt] { run(dt); });
        return true;
    }
    ~Life() { if (worker_.joinable()) worker_.join(); }

private:
    std::thread worker_;
    void run(double dt) {
        const auto t0 = std::chrono::steady_clock::now();
        for (GaiaSet* s : gaia) runGaia(*s, dt);
        if (main) runMain(*main, dt);
        const Change sc = engine.at(engine.sunRec(), dt, true);
        sunDMag = sc.same ? 0 : sc.dMag;
        sunDBv = sc.same ? 0 : sc.dColor;
        sunHidden = !sc.same && sc.hidden;
        computedDt = dt;
        lastMs = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        done = true;
        busy = false;
    }
    void runGaia(GaiaSet& s, double dt) {
        const size_t nl = s.leaves.size();
        s.leafGain.assign(nl, 0.0f);
        s.leafDelta.assign(nl * std::max(1u, s.bins), 0.0f);
        const unsigned nt = std::max(1u, std::min(32u, std::thread::hardware_concurrency() > 2 ? std::thread::hardware_concurrency() - 2 : 1u));
        std::vector<std::vector<std::pair<uint32_t, uint32_t>>> local(nt);
        std::vector<uint64_t> hid(nt, 0);
        std::vector<std::thread> th;
        for (unsigned w = 0; w < nt; ++w) {
            th.emplace_back([&, w] {
                for (size_t L = w; L < nl; L += nt) {      // feuilles réparties : chaque fil écrit ses propres feuilles
                    const auto [first, cnt] = s.leaves[L];
                    float* delta = s.leafDelta.data() + L * std::max(1u, s.bins);
                    for (uint64_t i = first; i < first + cnt; ++i) {
                        const uint32_t w0 = s.measuredWord(i);
                        uint32_t word = w0;
                        const Change c = engine.at(s.rec[i], dt, false);
                        if (!c.same) {
                            uint16_t h0;
                            std::memcpy(&h0, s.stars + i * 16 + 12, 2);
                            const float m0 = halfToFloat(h0);
                            const float m1 = c.hidden ? kHidden : static_cast<float>(m0 + c.dMag);
                            uint32_t col = (w0 >> 16) & 255u;
                            if (col < 254 && !c.hidden) col = static_cast<uint32_t>(std::clamp<long>(col + std::lround(c.dColor / 0.03), 0, 253));
                            word = (w0 & 0xff000000u) | (col << 16) | floatToHalf(m1);
                            if (c.hidden) ++hid[w];
                            s.leafGain[L] = std::max(s.leafGain[L], m0 - m1);
                            if (s.bins) {
                                const int b = std::clamp(static_cast<int>(std::floor((m0 - s.bin0) / s.binWidth)), 0, static_cast<int>(s.bins) - 1);
                                delta[b] += static_cast<float>(std::pow(10.0, -0.4 * m1) - std::pow(10.0, -0.4 * m0));
                            }
                        }
                        if (word != s.shown[i]) local[w].push_back({static_cast<uint32_t>(i), word});
                    }
                }
            });
        }
        for (auto& t : th) t.join();
        s.changes.clear();
        s.hidden = 0;
        for (unsigned w = 0; w < nt; ++w) {
            s.changes.insert(s.changes.end(), local[w].begin(), local[w].end());
            s.hidden += hid[w];
        }
        s.changed = s.changes.size();
    }
    void runMain(MainSet& s, double dt) {
        for (uint64_t i = 0; i < s.n; ++i) {
            const Change c = engine.at(s.rec[i], dt, true);
            const float m = c.same ? s.mag[i] : c.hidden ? kHidden : static_cast<float>(s.mag[i] + c.dMag);
            const float b = c.same || c.hidden ? s.bv[i] : static_cast<float>(s.bv[i] + c.dColor);
            if (m != s.magShown[i] || b != s.bvShown[i]) s.dirty = true;
            s.magNext[i] = m;
            s.bvNext[i] = b;
        }
    }
};

// Écriture des mots changés dans le tampon d'étoiles de la carte (shaders/vie_ecrire.comp), par paquets.
class WordWriter {
public:
    static constexpr VkDeviceSize kBatch = 8u << 20;      // changements par paquet (64 Mo de tampon partagé)
    void create(const Gpu& g) {
        staging_ = createBuffer(g, kBatch * 8, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkMapMemory(g.dev, staging_.mem, 0, VK_WHOLE_SIZE, 0, &mapped_), "vie des étoiles : tampon");
        VkDescriptorSetLayoutBinding binds[2];
        for (uint32_t i = 0; i < 2; ++i) binds[i] = {i, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        dl.bindingCount = 2;
        dl.pBindings = binds;
        check(vkCreateDescriptorSetLayout(g.dev, &dl, nullptr, &setLayout_), "vie des étoiles : agencement");
        const VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 8};
        VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        dp.maxSets = 4;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        check(vkCreateDescriptorPool(g.dev, &dp, nullptr, &pool_), "vie des étoiles : réserve");
        cs_ = shader(g, "vie_ecrire.comp.spv");
        const VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, 4};
        VkPipelineLayoutCreateInfo li{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        li.setLayoutCount = 1;
        li.pSetLayouts = &setLayout_;
        li.pushConstantRangeCount = 1;
        li.pPushConstantRanges = &pcr;
        check(vkCreatePipelineLayout(g.dev, &li, nullptr, &layout_), "vie des étoiles : agencement du calcul");
        VkComputePipelineCreateInfo cp{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        cp.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};
        cp.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cp.stage.module = cs_;
        cp.stage.pName = "main";
        cp.layout = layout_;
        check(vkCreateComputePipelines(g.dev, VK_NULL_HANDLE, 1, &cp, nullptr, &pipe_), "vie des étoiles : calcul");
        ready = true;
    }
    // Un jeu de descripteurs par tampon d'étoiles (gaia.bin, gaia_b.bin).
    VkDescriptorSet bind(const Gpu& g, VkBuffer stars) {
        VkDescriptorSet set{};
        VkDescriptorSetAllocateInfo da{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        da.descriptorPool = pool_;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &setLayout_;
        check(vkAllocateDescriptorSets(g.dev, &da, &set), "vie des étoiles : jeu");
        const VkDescriptorBufferInfo infos[2] = {{stars, 0, VK_WHOLE_SIZE}, {staging_.buf, 0, VK_WHOLE_SIZE}};
        VkWriteDescriptorSet w[2];
        for (uint32_t i = 0; i < 2; ++i) {
            w[i] = {VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            w[i].dstSet = set;
            w[i].dstBinding = i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = &infos[i];
        }
        vkUpdateDescriptorSets(g.dev, 2, w, 0, nullptr);
        return set;
    }
    // Envoie tous les changements (paquets successifs, chacun attendu) puis met à jour les mots montrés.
    void write(const Gpu& g, VkDescriptorSet set, GaiaSet& s) {
        for (size_t off = 0; off < s.changes.size(); off += kBatch) {
            const uint32_t cnt = static_cast<uint32_t>(std::min<size_t>(kBatch, s.changes.size() - off));
            std::memcpy(mapped_, s.changes.data() + off, static_cast<size_t>(cnt) * 8);
            VkCommandBuffer cmd = beginOnce(g);
            VkMemoryBarrier before{VK_STRUCTURE_TYPE_MEMORY_BARRIER};      // les images en vol ont fini de lire les étoiles
            before.srcAccessMask = VK_ACCESS_SHADER_READ_BIT;
            before.dstAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &before, 0, nullptr, 0, nullptr);
            vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe_);
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout_, 0, 1, &set, 0, nullptr);
            vkCmdPushConstants(cmd, layout_, VK_SHADER_STAGE_COMPUTE_BIT, 0, 4, &cnt);
            vkCmdDispatch(cmd, (cnt + 255) / 256, 1, 1);
            VkMemoryBarrier after{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
            after.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            after.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0, 1, &after, 0, nullptr, 0, nullptr);
            endOnce(g, cmd);
        }
        for (const auto& [i, w] : s.changes) s.shown[i] = w;
        s.changes.clear();
        s.gainShown.swap(s.leafGain);
        s.deltaShown.swap(s.leafDelta);
    }
    void release(const Gpu& g) {
        if (!ready) return;
        vkUnmapMemory(g.dev, staging_.mem);
        destroy(g, staging_);
        vkDestroyPipeline(g.dev, pipe_, nullptr);
        vkDestroyPipelineLayout(g.dev, layout_, nullptr);
        vkDestroyDescriptorPool(g.dev, pool_, nullptr);
        vkDestroyDescriptorSetLayout(g.dev, setLayout_, nullptr);
        vkDestroyShaderModule(g.dev, cs_, nullptr);
        ready = false;
    }
    bool ready = false;

private:
    Buffer staging_;
    void* mapped_ = nullptr;
    VkDescriptorSetLayout setLayout_{};
    VkDescriptorPool pool_{};
    VkPipelineLayout layout_{};
    VkPipeline pipe_{};
    VkShaderModule cs_{};
};

}  // namespace vie
