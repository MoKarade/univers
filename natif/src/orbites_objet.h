// Appli PC « Univers » : l'orbite de N'IMPORTE QUEL astre suivi (demande de Marc, 18/11/2026 : « voir les orbites de
// n'importe quel objet »), et la même orbite recalculée avec les réglages du bac à sable.
//
// D'où vient chaque tracé (rien n'est dessiné qui ne soit pas calculé ou mesuré) :
//   - planètes et lunes : déjà tracées par drawOrbits (éphémérides de la NASA) ;
//   - sondes : leur trajectoire réelle du JPL, sur toute la durée fournie ;
//   - astéroïdes et comètes : leur orbite mesurée (JPL), un tour (ou ±150 ans si l'orbite est ouverte) ;
//   - Soleil et étoiles nommées : leur orbite autour du centre de la Voie lactée, calculée ici avec exactement le même
//     modèle et le même départ mesuré que l'appli (Sim::exact), sur ±250 millions d'années autour de la date montrée ;
//   - galaxies du Groupe local : leur chemin calculé autour de la Voie lactée (film de la rencontre là où il existe,
//     centres de référence ailleurs), même logique que Sim::refreshGalaxies.
// Les points sont gardés dans le repère du centre de la Galaxie, puis replacés à chaque image dans le repère affiché
// (qui suit le Soleil) : le tracé reste juste quand le temps défile, sans tout recalculer.
#pragma once
#include <algorithm>
#include <cmath>
#include <future>
#include <span>
#include <vector>

#include "groupe_local_scenario.h"
#include "simulation.h"

namespace univers {

// Réglages du bac à sable qui changent le mouvement des étoiles (partagés par le panneau et les tracés).
struct SandboxGalaxy {
    float haloFactor = 1.0f;      // masse de la matière noire de la Voie lactée, en fois la valeur du modèle
    bool bar = true;               // barre centrale de la Voie lactée
    bool useCosmologyLambda = true;      // énergie noire locale tirée des réglages de l'expansion (H0² Ω_Λ)
    bool differs(const cosmo::Params& c) const {
        const cosmo::Params ref{};
        return std::fabs(haloFactor - 1.0f) > 1e-4f || !bar || (useCosmologyLambda && (std::fabs(c.ode - ref.ode) > 1e-6 || std::fabs(c.h0 - ref.h0) > 1e-6));
    }
    phys::galaxie::Potentiel potential(const cosmo::Params& c) const {
        phys::galaxie::Potentiel p;
        p.GMs *= haloFactor;
        p.barre = bar;
        // H0 en km/s/kpc (1 Mpc = 1000 kpc) ; Ω_Λ de l'expansion. Avec les valeurs mesurées : exactement kLambdaKmsKpc2.
        if (useCosmologyLambda) p.lambda = (c.h0 / 1000.0) * (c.h0 / 1000.0) * c.ode;
        return p;
    }
    // Même réglage pour la rencontre du Groupe local (groupe_local_scenario.h) : masses des halos et énergie noire.
    scenario::Settings groupSettings(const cosmo::Params& c) const {
        scenario::Settings g;
        g.massFactor = haloFactor;
        if (useCosmologyLambda) g.K = (c.h0 / 1000.0) * (c.h0 / 1000.0) * c.ode;
        return g;
    }
};

struct ObjectTrack {
    static constexpr double kHalfWindowGa = 0.25;      // étoiles : ±250 millions d'années
    int focus = -1;
    int kind = -1;            // 0 : étoile ou Soleil (repère galactique) ; 1 : galaxie ; 2 : autour du Soleil ; -1 : aucun
    double centreYears = 1e300;
    double asteroidSpan = 0;  // astéroïde : durée tracée (années)
    std::vector<double> t;    // dates (années depuis J2000)
    std::vector<phys::Vec3> g, gWhatIf;      // kind 0 et 1 : kpc, repère phys::galaxie ; kind 2 : années-lumière, héliocentrique
    std::vector<float> r, rWhatIf;           // distance au centre (kpc) ou au Soleil (UA) : pour la courbe du panneau
    bool hasWhatIf = false;
    const char* note = "";
    // Galaxies du Groupe local : la rencontre rejouée (valeurs mesurées, puis tes réglages), pour les dates du panneau.
    scenario::Result groupBase, groupWhatIf;
    int galaxyIndex = -1;

    // Réglages avec lesquels le tracé « et si… » a été calculé (comparés champ par champ).
    SandboxGalaxy usedSandbox;
    double usedH0 = 0, usedOde = 0;
    int usedAsteroid = -2;
    bool sameSettings(const SandboxGalaxy& s, const cosmo::Params& c) const {
        return s.haloFactor == usedSandbox.haloFactor && s.bar == usedSandbox.bar && s.useCosmologyLambda == usedSandbox.useCosmologyLambda && c.h0 == usedH0 &&
               c.ode == usedOde;
    }
    // Repère affiché à cette image : place du Soleil (une fois par image, pas une fois par point).
    phys::Vec3 frameSun{0, 0, 0};
    Vec3 frameShift{0, 0, 0};
    void prepareFrame(const Sim& sim) {
        if (kind == 0) frameSun = sim.sunGalacto();
        if (kind == 1) frameShift = sim.sunShift();
    }

    // settling : un curseur est en train de bouger ; un changement de réglages attend qu'on le lâche (un calcul complet
    // par image ralentirait la fenêtre).
    void update(const Sim& sim, const SandboxGalaxy& sb, bool settling = false) {
        collect(sim.lastAdvance == 0.0);      // orbite recalculée à part : reprise dès qu'elle est prête (attendue à l'arrêt)
        if (settling && sim.focus == focus && !sameSettings(sb, sim.cosmology)) return;
        const int f = sim.focus;
        const Body& b = sim.bodies[static_cast<size_t>(f)];
        const bool star = b.kind == Kind::Star || b.kind == Kind::Sun;
        // Étoiles : on recentre la fenêtre quand la date s'en éloigne d'un cinquième ; astéroïdes : idem sur leur durée.
        const bool recentre = (star && std::fabs(sim.years - centreYears) > 0.2 * kHalfWindowGa * 1e9) ||
                              (b.kind == Kind::Asteroid && std::fabs(sim.years - centreYears) > 0.2 * std::max(asteroidSpan, 1e-3));
        const int ast = b.kind == Kind::Asteroid ? sim.asteroidSel : -2;      // un seul emplacement pour tous les astéroïdes
        if (f == focus && ast == usedAsteroid && sameSettings(sb, sim.cosmology) && !recentre) return;
        // Même étoile, mêmes réglages, le temps défile : la fenêtre glisse. L'orbite est intégrée depuis aujourd'hui (des
        // milliers de pas d'un million d'années loin dans le temps : jusqu'à ~60 ms) ; le calcul se fait dans un fil à part
        // avec exactement les mêmes données, et l'ancien tracé reste en attendant (quelques images).
        if (star && kind == 0 && f == focus && ast == usedAsteroid && sameSettings(sb, sim.cosmology) && sim.lastAdvance != 0.0) {
            if (!pending_.valid()) startStar(sim, sb);
            return;
        }
        if (pending_.valid()) (void)pending_.get();      // autre astre ou autres réglages : le calcul en cours ne sert plus
        focus = f;
        usedAsteroid = ast;
        usedSandbox = sb;
        usedH0 = sim.cosmology.h0;
        usedOde = sim.cosmology.ode;
        centreYears = sim.years;
        t.clear(); g.clear(); gWhatIf.clear(); r.clear(); rWhatIf.clear();
        hasWhatIf = false;
        kind = -1;
        note = "";
        if (star) buildStar(sim, sb);
        else if (b.kind == Kind::Galaxy) buildGalaxy(sim, b, sb);
        else if (b.kind == Kind::Probe) buildProbe(sim, b);
        else if (b.kind == Kind::Asteroid) buildAsteroid(sim);
    }

    // Point du tracé dans le repère affiché, à la date montrée.
    Vec3 world(const Sim& sim, const phys::Vec3& p) const {
        (void)sim;
        if (kind == 2) return {p.x, p.y, p.z};
        if (kind == 1) {
            const Vec3 w = Sim::fromGalactocentric(p), s = frameShift;
            return {w.x + s.x, w.y + s.y, w.z + s.z};
        }
        const phys::Vec3 s = frameSun;
        return orbite::versEcliptique({(p.x - s.x) * orbite::kKpcLy, (p.y - s.y) * orbite::kKpcLy, (p.z - s.z) * orbite::kKpcLy});
    }

private:
    // Calcul d'orbite d'étoile fait à part (startStar) : mêmes vecteurs que buildStar.
    struct StarJob {
        std::vector<double> t;
        std::vector<phys::Vec3> g, gWhatIf;
        std::vector<float> r, rWhatIf;
        bool hasWhatIf = false;
    };
    std::future<StarJob> pending_;

    void startStar(const Sim& sim, const SandboxGalaxy& sb) {
        sim.ensureExact();
        const int idx = sim.bodies[static_cast<size_t>(sim.focus)].kind == Kind::Sun ? 0 : sim.exactOf[static_cast<size_t>(sim.focus)];
        if (idx < 0) return;
        centreYears = sim.years;
        const double now = sim.years / 1.0e9;
        const double lo = std::max(now - kHalfWindowGa, (sim.minYears()) / 1.0e9), hi = std::min(now + kHalfWindowGa, sim.maxYears() / 1.0e9);
        const phys::Vec3 p0 = sim.exact.g0[static_cast<size_t>(idx)], v0 = sim.exact.v0[static_cast<size_t>(idx)];
        const bool whatIf = sb.differs(sim.cosmology);
        const phys::galaxie::Potentiel pw = sb.potential(sim.cosmology);
        pending_ = std::async(std::launch::async, [p0, v0, lo, hi, whatIf, pw] {
            StarJob j;
            integrateTo(p0, v0, phys::galaxie::Potentiel{}, lo, hi, &j.t, j.g, j.r);
            j.hasWhatIf = whatIf;
            if (whatIf) integrateTo(p0, v0, pw, lo, hi, nullptr, j.gWhatIf, j.rWhatIf);
            return j;
        });
    }
    // Reprend le calcul fait à part s'il est prêt (ou l'attend si wait).
    void collect(bool wait) {
        if (!pending_.valid()) return;
        if (!wait && pending_.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
        StarJob j = pending_.get();
        t = std::move(j.t); g = std::move(j.g); r = std::move(j.r);
        gWhatIf = std::move(j.gWhatIf); rWhatIf = std::move(j.rWhatIf);
        hasWhatIf = j.hasWhatIf;
    }

    void buildStar(const Sim& sim, const SandboxGalaxy& sb) {
        sim.ensureExact();
        const int idx = sim.bodies[static_cast<size_t>(sim.focus)].kind == Kind::Sun ? 0 : sim.exactOf[static_cast<size_t>(sim.focus)];
        if (idx < 0) return;
        kind = 0;
        const double now = sim.years / 1.0e9;
        const double lo = std::max(now - kHalfWindowGa, (sim.minYears()) / 1.0e9), hi = std::min(now + kHalfWindowGa, sim.maxYears() / 1.0e9);
        const phys::Vec3 p0 = sim.exact.g0[static_cast<size_t>(idx)], v0 = sim.exact.v0[static_cast<size_t>(idx)];
        integrate(p0, v0, phys::galaxie::Potentiel{}, lo, hi, true, g, r);
        hasWhatIf = sb.differs(sim.cosmology);
        if (hasWhatIf) {
            integrate(p0, v0, sb.potential(sim.cosmology), lo, hi, false, gWhatIf, rWhatIf);
        }
        note = "Orbite autour du centre de la Voie lactée, calculée ici (départ : position et vitesse mesurées).";
    }

    // Intégration d'une seule étoile au pas de l'appli (1 million d'années), un point tous les 1 Ma de lo à hi.
    void integrate(phys::Vec3 p0, phys::Vec3 v0, const phys::galaxie::Potentiel& P, double lo, double hi, bool keepTimes,
                   std::vector<phys::Vec3>& out, std::vector<float>& dist) {
        integrateTo(p0, v0, P, lo, hi, keepTimes ? &t : nullptr, out, dist);
    }
    static void integrateTo(phys::Vec3 p0, phys::Vec3 v0, const phys::galaxie::Potentiel& P, double lo, double hi, std::vector<double>* times,
                            std::vector<phys::Vec3>& out, std::vector<float>& dist) {
        const phys::Vec3 pos[1] = {p0}, vel[1] = {v0};
        phys::galaxie::Orbites o(std::span<const phys::Vec3>(pos, 1), std::span<const phys::Vec3>(vel, 1), P);
        o.avance(lo, 1);
        const int n = std::max(2, static_cast<int>(std::lround((hi - lo) / 0.001)) + 1);
        for (int i = 0; i < n; ++i) {
            const double tg = lo + (hi - lo) * i / (n - 1);
            o.avance(tg, 1);
            const phys::Vec3 q = o.position(0);
            out.push_back(q);
            dist.push_back(static_cast<float>(std::sqrt(q.x * q.x + q.y * q.y + q.z * q.z)));
            if (times) times->push_back(tg * 1.0e9);
        }
    }

    // Même règle que Sim::refreshGalaxies (Sim::filmCentre) : film de la rencontre là où il existe (écart de départ effacé sur 100 Ma),
    // centres de référence ailleurs.
    static bool galaxyAt(const Sim& sim, int ci, double tGa, phys::Vec3& out) {
        if (sim.filmCovers(tGa) && ci < sim.film.galaxies() && sim.filmCentre(ci, tGa, out, true)) return true;      // ancre si elle existe
        return sim.centres && sim.centres->ready && sim.centres->centre(ci, tGa, out);
    }

    void buildGalaxy(const Sim& sim, const Body& b, const SandboxGalaxy& sb) {
        const int ci = sim.centres && sim.centres->ready ? CentresReference::indexOf(b.name) : -1;
        if (ci < 0) {
            note = b.structure ? "Grande structure : pas d'orbite (elle bouge avec l'expansion de l'univers)."
                 : b.cluster   ? "Amas de galaxies : pas d'orbite calculée, seule sa position mesurée est connue."
                               : "Pas d'orbite calculée pour cette galaxie : seule sa position mesurée est connue.";
            return;
        }
        kind = 1;
        const double lo = std::max(sim.centres->firstGa(), (sim.minYears() - kStartYears) / 1.0e9 - 2.0), hi = std::min(sim.centres->lastGa(), (sim.maxYears() - kStartYears) / 1.0e9);
        for (double tg = lo; tg <= hi + 1e-9; tg += 0.01) {
            phys::Vec3 q;
            if (!galaxyAt(sim, ci, tg, q)) continue;
            t.push_back(kStartYears + tg * 1.0e9);      /* dates de l'appli : années depuis J2000 */
            g.push_back(q);
            r.push_back(static_cast<float>(std::sqrt(q.x * q.x + q.y * q.y + q.z * q.z)));
        }
        note = "Chemin autour de la Voie lactée, calculé (rencontre du Groupe local) ; distance au centre de la Voie lactée.";
        galaxyIndex = ci;
        // Rencontre rejouée : une fois avec les valeurs mesurées (référence, gardée), une fois avec tes réglages.
        static scenario::Result base;
        if (!base.ok) base = scenario::run(*sim.centres, scenario::Settings{});
        groupBase = base;
        groupWhatIf = scenario::Result{};
        const cosmo::Params ref{};
        const bool changed = std::fabs(sb.haloFactor - 1.0f) > 1e-4f ||
                             (sb.useCosmologyLambda && (std::fabs(sim.cosmology.ode - ref.ode) > 1e-6 || std::fabs(sim.cosmology.h0 - ref.h0) > 1e-6));
        if (!changed || !base.ok) return;
        groupWhatIf = scenario::run(*sim.centres, sb.groupSettings(sim.cosmology));
        if (!groupWhatIf.ok || groupWhatIf.tGa.size() < 2) return;
        // Variante alignée sur les dates du tracé : le passé ne change pas (les réglages agissent à partir d'aujourd'hui).
        const double step = groupWhatIf.tGa[1] - groupWhatIf.tGa[0];
        for (size_t i = 0; i < t.size(); ++i) {
            const double tg = (t[i] - kStartYears) / 1.0e9;
            phys::Vec3 q = g[i];
            if (tg >= 0) {
                const double x = tg / step;
                const size_t k = std::min(static_cast<size_t>(x), groupWhatIf.tGa.size() - 2);
                const double u = std::clamp(x - static_cast<double>(k), 0.0, 1.0);
                const phys::Vec3 a = groupWhatIf.pos[k][static_cast<size_t>(ci)], b2 = groupWhatIf.pos[k + 1][static_cast<size_t>(ci)];
                q = {a.x + u * (b2.x - a.x), a.y + u * (b2.y - a.y), a.z + u * (b2.z - a.z)};
            }
            gWhatIf.push_back(q);
            rWhatIf.push_back(static_cast<float>(std::sqrt(q.x * q.x + q.y * q.y + q.z * q.z)));
        }
        hasWhatIf = true;
    }

    void buildProbe(const Sim& sim, const Body& b) {
        if (!sim.probes || b.probe < 0 || static_cast<size_t>(b.probe) >= sim.probes->size()) return;
        const sondes::Probe& pr = (*sim.probes)[static_cast<size_t>(b.probe)];
        kind = 2;
        const double a = pr.firstJd(), z = pr.lastJd();
        for (int i = 0; i <= 900; ++i) {
            const double jd = a + (z - a) * i / 900.0;
            double pos[3], vel[3];
            if (!pr.at(jd, pos, vel)) continue;
            t.push_back((jd - 2451545.0) / 365.25);
            g.push_back({pos[0] / kLyInKm, pos[1] / kLyInKm, pos[2] / kLyInKm});
            r.push_back(static_cast<float>(std::sqrt(pos[0] * pos[0] + pos[1] * pos[1] + pos[2] * pos[2]) / 1.495978707e8));
        }
        note = "Trajectoire réelle du JPL (NASA) sur toute la durée fournie ; distance au Soleil.";
    }

    void buildAsteroid(const Sim& sim) {
        if (!sim.asteroidCat || sim.asteroidSel < 0) return;
        const size_t k = static_cast<size_t>(sim.asteroidSel);
        const asteroides::Catalogue& c = *sim.asteroidCat;
        kind = 2;
        const bool open = c.eccentricity(k) >= 1.0;
        const double span = open ? 300.0 : std::min(c.periodYears(k), 300.0);
        asteroidSpan = span;
        const double mid = sim.years;
        for (int i = 0; i <= 600; ++i) {
            const double y = mid + (static_cast<double>(i) / 600.0 - 0.5) * span;
            const double jd = 2451545.0 + y * 365.25;
            if (std::fabs(jd - c.epochJd) > 300.0 * 365.25) continue;
            double au[3];
            c.position(k, jd, au);
            t.push_back(y);
            g.push_back({au[0] * kAuInLy, au[1] * kAuInLy, au[2] * kAuInLy});
            r.push_back(static_cast<float>(std::sqrt(au[0] * au[0] + au[1] * au[1] + au[2] * au[2])));
        }
        note = "Orbite mesurée (JPL), sans l'attraction des planètes ; distance au Soleil.";
    }
};

}  // namespace univers