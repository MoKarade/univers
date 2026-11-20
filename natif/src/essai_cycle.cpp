// Contrôle du cycle de vie des étoiles (cycle_etoile.h, cycle_matiere.h) sur le vrai fichier vie_cycle.bin.
// Usage : essai_cycle <vie_cycle.bin>     (aucune carte graphique)
#include <cstdio>

#include "cycle_matiere.h"

namespace {
int echecs = 0;
void verifie(bool ok, const char* quoi, double val = 0) {
    std::printf("%s  %-70s %.6g\n", ok ? "PASSE" : "ECHEC", quoi, val);
    if (!ok) ++echecs;
}
double bilanEcart(const cycle::Vie& v, const std::vector<cycle::Paquet>& pq, double a) {
    cycle::Bilan b;
    cycle::couches(v, pq, a, &b);
    const double somme = b.etoile + b.nuage + b.vents + b.ejecta + b.neutrinos + b.milieu;
    return std::fabs(somme - b.coeur) / b.coeur;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::printf("usage : essai_cycle vie_cycle.bin\n");
        return 2;
    }
    cycle::Grille g;
    verifie(g.load(argv[1]), "lecture de vie_cycle.bin");
    if (!g.ready) return 1;
    verifie(g.traces.size() == 182 && g.naines.size() == 9, "182 traces MIST et 9 tables de Montréal", static_cast<double>(g.traces.size()));

    // ---- Soleil
    const cycle::Vie sol = cycle::vieEtoile(g, true, 4.83, 0.653);
    const cycle::Etat now = sol.etat(cycle::kAgeSoleilAns);
    verifie(std::fabs(now.lum - 1.0) < 0.15, "Soleil aujourd'hui : L du modèle à 15 % de 1 L☉ (l'écran garde la mesure)", now.lum);
    verifie(std::fabs(now.rayon - 1.0) < 0.05, "Soleil aujourd'hui : R du modèle à 5 % de 1 R☉", now.rayon);
    verifie(now.etape == cycle::Etape::Sequence, "Soleil aujourd'hui : séquence principale");
    const cycle::Vu vu0 = cycle::vuA(sol, 0.0);
    verifie(std::fabs(vu0.rayonKm - 695700.0) < 1.0, "écran aujourd'hui : rayon mesuré exact (km)", vu0.rayonKm);
    // plus grand rayon et sa date
    double rMax = 0, tMax = 0;
    for (double t = 0; t < 7.2e9; t += 1.0e5) {
        const cycle::Vu v = cycle::vuA(sol, t);
        if (v.rayonKm > rMax) { rMax = v.rayonKm; tMax = t; }
    }
    std::printf("       Soleil : plus grand rayon %.0f R☉ (%.3f UA) dans %.4f Ga\n", rMax / 695700.0, rMax / 1.495978707e8, tMax / 1e9);
    verifie(rMax / 695700.0 > 150 && rMax / 695700.0 < 300, "Soleil : géante rouge de 150 à 300 R☉ (MIST)", rMax / 695700.0);
    verifie(tMax > 6.5e9 && tMax < 7.0e9, "Soleil : sommet de la géante rouge entre +6,5 et +7 Ga", tMax / 1e9);
    const double finSeq = sol.debutEtape(cycle::Etape::Geante) - cycle::kAgeSoleilAns;
    std::printf("       Soleil : quitte la séquence principale dans %.3f Ga, naine blanche dans %.4f Ga\n", finSeq / 1e9,
                (sol.debutEtape(cycle::Etape::NaineBlanche) - cycle::kAgeSoleilAns) / 1e9);
    verifie(finSeq > 4.5e9 && finSeq < 6.0e9, "Soleil : fin de la séquence principale dans 4,5 à 6 Ga", finSeq / 1e9);
    const cycle::Etat wd = sol.etat(cycle::kAgeSoleilAns + 9.0e9);
    verifie(wd.etape == cycle::Etape::NaineBlanche, "Soleil dans 9 Ga : naine blanche");
    verifie(std::fabs(wd.masse - 0.54) < 0.02, "naine blanche : 0,54 M☉ (MIST)", wd.masse);
    verifie(wd.rayon > 0.008 && wd.rayon < 0.016, "naine blanche : rayon de 0,008 à 0,016 R☉ (taille de la Terre)", wd.rayon);
    std::printf("       naine blanche dans 9 Ga : Teff %.0f K, L %.2e L☉\n", wd.teff, wd.lum);

    // ---- continuité : pas de saut de forme ni d'éclat sur une durée courte, même aux raccords
    double pire = 0, pireT = 0;
    for (double a = 1.0e6; a < sol.ageFin() + 2.0e9; a *= 1.0 + 1e-6) {
        if (a > 1e9 && a < sol.ageFin() - 5e7) a = sol.ageFin() - 5e7;      // la séquence principale est lente : on saute
        const cycle::Etat x = sol.etat(a), y = sol.etat(a * (1.0 + 1e-9));
        if (x.rayon <= 0 || y.rayon <= 0) continue;
        const double d = std::fabs(std::log10(y.rayon / x.rayon));
        if (d > pire) { pire = d; pireT = a; }
        if (a > sol.ageFin() + 1e9) break;
    }
    verifie(pire < 0.01, "Soleil : rayon continu (écart entre deux dates à 1e-9 près)", pire);
    std::printf("       pire écart à %.6e ans\n", pireT);
    const cycle::Etat avant = sol.etat(sol.ageFin() - 1.0), apres = sol.etat(sol.ageFin() + 1.0);
    verifie(std::fabs(std::log10(apres.lum / avant.lum)) < 0.05, "raccord trace MIST -> refroidissement de Montréal : éclat", std::log10(apres.lum / avant.lum));
    verifie(std::fabs(std::log10(apres.rayon / avant.rayon)) < 0.15, "raccord trace MIST -> refroidissement de Montréal : rayon", std::log10(apres.rayon / avant.rayon));

    // ---- masse conservée
    const auto pqSol = cycle::paquets(sol);
    double ecart = 0;
    for (double a : {-3.0e6, -1.0e6, -2.0e5, 1.0e3, 4.5e9, 1.1e10, 1.1336e10, 1.1463e10, 1.2e10, 1.6e10}) ecart = std::max(ecart, bilanEcart(sol, pqSol, a));
    verifie(ecart < 1e-6, "Soleil : masse conservée à toute date (écart relatif)", ecart);
    const cycle::Vie m20 = cycle::vieDe(g, 20.0);
    const auto pq20 = cycle::paquets(m20);
    ecart = 0;
    for (double a : {-1.0e6, 1.0e5, 5.0e6, 9.0e6, m20.ageFin() - 1.0, m20.ageFin() + 0.1, m20.ageFin() + 1.0e3, m20.ageFin() + 1.0e5}) ecart = std::max(ecart, bilanEcart(m20, pq20, a));
    verifie(ecart < 1e-6, "20 M☉ : masse conservée à toute date (neutrinos comptés)", ecart);

    // ---- restes (Fryer et al. 2012)
    verifie(!m20.reste.trouNoir && m20.reste.gravite > 1.2 && m20.reste.gravite < 1.8, "20 M☉ : étoile à neutrons de 1,2 à 1,8 M☉", m20.reste.gravite);
    const cycle::Vie m30 = cycle::vieDe(g, 30.0);
    verifie(m30.reste.trouNoir, "30 M☉ : trou noir", m30.reste.gravite);
    const cycle::Vie m60 = cycle::vieDe(g, 60.0);
    verifie(m60.reste.trouNoir && !m60.reste.explose, "60 M☉ : effondrement direct en trou noir, sans explosion", m60.reste.gravite);
    const cycle::Etat sn = m20.etat(m20.ageFin() + 50.0 / 365.25);
    verifie(sn.etape == cycle::Etape::Supernova && std::fabs(sn.magV - cycle::kSnPlateau) < 0.01, "20 M☉ : supernova au plateau (M_V -16,7)", sn.magV);
    verifie(sn.rayon > std::pow(10.0, m20.logR.back()), "supernova : la photosphère part du rayon de l'étoile et grandit", sn.rayon);

    // ---- nébuleuse : le Soleil ionise sa nébuleuse planétaire (vent rapide qui pousse le vent lent)
    {
        const float blanc[3] = {1, 1, 1};
        double lMax = 0, rAuMax = 0;
        for (double dt = 0; dt <= 40.0e3; dt += 4.0e3) {
            const double a = sol.debutEtape(cycle::Etape::Nebuleuse) + dt;
            const cycle::Etat c = sol.etat(a);
            const cycle::Profil p = cycle::profil(cycle::couches(sol, pqSol, a), c, blanc);
            std::printf("       nébuleuse du Soleil, +%5.0f ans : cœur %6.0f K %7.1f L☉, masse ionisée %.3f M☉, lumière %7.2f L☉, coquille %.2f al\n", dt, c.teff, c.lum,
                        p.ionise, p.lumiere, cycle::kVitesseCoquilleKms / cycle::kCkms * (a - cycle::debutVentRapide(sol)));
            if (p.lumiere > lMax) { lMax = p.lumiere; rAuMax = cycle::kVitesseCoquilleKms / cycle::kCkms * (a - cycle::debutVentRapide(sol)); }
        }
        verifie(lMax > 1.0, "nébuleuse planétaire du Soleil : plus de 1 L☉ de lumière visible à son plus fort", lMax);
        (void)rAuMax;
    }
    verifie(cycle::photonsIonisants(1e4, 40000) > 1e46 && cycle::photonsIonisants(1e4, 40000) < 1e49, "photons ionisants d'un corps noir de 40 000 K et 10⁴ L☉", cycle::photonsIonisants(1e4, 40000));

    // ---- placement d'une étoile par l'éclat et la couleur
    const cycle::Vie soleilPlace = cycle::vieEtoile(g, false, 4.83, 0.653);
    verifie(soleilPlace.ok() && std::fabs(soleilPlace.m0 - 1.0) < 0.15, "placement d'une étoile comme le Soleil : 0,85 à 1,15 M☉", soleilPlace.m0);
    // Bételgeuse (M_V ≈ -5,85, B-V ≈ 1,85, valeurs du catalogue de l'appli, ordre de grandeur)
    const cycle::Vie bet = cycle::vieEtoile(g, false, -5.85, 1.85);
    std::printf("       Bételgeuse placée : %.1f M☉ (%.1f à %.1f), fin dans %.0f à %.0f milliers d'années\n", bet.m0, bet.mBas, bet.mHaut, bet.finBas / 1e3, bet.finHaut / 1e3);
    verifie(bet.ok() && bet.m0 > 10 && bet.fin == 2, "Bételgeuse : plus de 10 M☉, finit en supernova", bet.m0);

    std::printf("%s (%d échec%s)\n", echecs ? "ÉCHEC" : "TOUT PASSE", echecs, echecs > 1 ? "s" : "");
    return echecs ? 1 : 0;
}
