// Appli PC « Univers » : l'essentiel d'un astre en tuiles (2e tour de l'interface, 20/11/2026 : « des informations plus
// digestibles »). En haut de la fiche, quatre chiffres au plus, en grand, chacun avec la couleur de son statut ; tout le
// détail (sources, méthodes, incertitudes) reste plus bas, dans « Toutes les valeurs ».
// Aucune valeur nouvelle : ce sont les mêmes que la fiche détaillée (cardRows), présentées autrement.
#pragma once
#include "interface_recherche.h"

namespace {

struct Tuile {
    std::string label, valeur;
    ui_outils::Statut statut = ui_outils::Statut::Aucun;
    std::string aide;      // bulle au survol : d'où vient ce chiffre
};

// Une tuile : petit libellé en capitales, valeur en grand, point de couleur du statut.
void drawTile(const UiState& ui, const Tuile& t, float w) {
    const ImVec2 p = ImGui::GetCursorScreenPos();
    ImFont* fs = gFontSmall ? gFontSmall : ImGui::GetFont();
    ImFont* fb = gFontBold ? gFontBold : ImGui::GetFont();
    const float scale = ImGui::GetIO().FontGlobalScale;
    const float hs = fs->FontSize * scale, hb = fb->FontSize * scale;
    const float pad = px(ui, 10), h = pad * 2 + hs + hb + px(ui, 4);
    ImGui::InvisibleButton(t.label.c_str(), {w, h});
    const bool hov = ImGui::IsItemHovered();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    dl->AddRectFilled(p, {p.x + w, p.y + h}, hov ? IM_COL32(255, 255, 255, 22) : IM_COL32(255, 255, 255, 12), px(ui, 10));
    const std::string up = ui_outils::majuscules(t.label);
    dl->AddText(fs, hs, {p.x + pad, p.y + pad}, theme::kFaint, up.c_str());
    // La valeur, réduite au besoin pour tenir dans la tuile.
    const float avail = w - 2 * pad - px(ui, 12);
    float size = hb;
    const float need = fb->CalcTextSizeA(size, FLT_MAX, 0, t.valeur.c_str()).x;
    if (need > avail) size = std::max(hs, size * avail / need);
    dl->AddText(fb, size, {p.x + pad, p.y + pad + hs + px(ui, 4) + (hb - size)}, theme::kText, t.valeur.c_str());
    if (t.statut != ui_outils::Statut::Aucun)
        dl->AddCircleFilled({p.x + w - pad - px(ui, 3), p.y + pad + hs * 0.5f}, px(ui, 3.5f), theme::statutCouleur(t.statut));
    if (hov) {
        ImGui::BeginTooltip();
        ImGui::TextUnformatted(t.label.c_str());
        if (t.statut != ui_outils::Statut::Aucun) {
            ImGui::SameLine();
            statusChip(t.statut);
        }
        if (!t.aide.empty()) ImGui::TextDisabled("%s", t.aide.c_str());
        ImGui::EndTooltip();
    }
}

std::string durationText(double years) {
    const double days = years * 365.25;
    if (years >= 1) return frNum(years, years >= 100 ? 0 : 2) + " ans";
    if (days >= 2) return frNum(days, days >= 100 ? 0 : 1) + " jours";
    return frNum(days * 24.0, 1) + " heures";
}

// Les chiffres-clés de l'astre suivi, tirés des mêmes données que la fiche détaillée.
std::vector<Tuile> keyFacts(const Sim& sim, int f) {
    using ui_outils::Statut;
    const Body& b = sim.bodies[static_cast<size_t>(f)];
    std::vector<Tuile> out;
    const Vec3 p = sim.position(f);
    const double dSun = std::sqrt(dot(p, p));
    const bool today = std::fabs(sim.years - kStartYears) < 1.0;
    auto childCount = [&](Kind k) {
        int n = 0;
        for (const Body& c : sim.bodies) n += c.kind == k && c.parent == f;
        return n;
    };
    switch (b.kind) {
        case Kind::Sun: {
            out.push_back({"Rayon", frInt(b.radiusKm) + " km", Statut::Mesure, "NASA Sun Fact Sheet"});
            out.push_back({"Température", frInt(4600.0 * (1.0 / (0.92 * b.bv + 1.7) + 1.0 / (0.92 * b.bv + 0.62))) + " K", Statut::Calcule,
                           "calculée d'après la couleur (surface)"});
            int planets = 0;      // Pluton est une planète naine : pas comptée parmi les planètes
            for (const Body& c : sim.bodies) planets += c.kind == Kind::Planet && c.parent == f && c.name != "Pluton";
            out.push_back({"Planètes", std::to_string(planets), Statut::Mesure, "placées par les éphémérides de la NASA"});
            break;
        }
        case Kind::Planet: {
            const bool computed = static_cast<size_t>(f) < sim.planetComputed.size() && sim.planetComputed[static_cast<size_t>(f)];
            const char* src = computed ? "calculée ici (gravité mutuelle)" : "éphémérides de la NASA";
            if (b.parent > 0) out.push_back({"Distance à " + sim.bodies[static_cast<size_t>(b.parent)].name, frDistance(distBetween(p, sim.position(b.parent))), computed ? Statut::Calcule : Statut::Mesure, src});
            else out.push_back({"Distance au Soleil", frDistance(dSun), computed ? Statut::Calcule : Statut::Mesure, src});
            if (b.radiusKm > 0) out.push_back({"Rayon", (b.radiusKm >= 100 ? frInt(b.radiusKm) : frNum(b.radiusKm)) + " km", Statut::Mesure, "rayon moyen"});
            else out.push_back({"Rayon", "non mesuré", Statut::Inconnu, ""});
            if (b.periodYears > 0) out.push_back({b.parent > 0 ? "Un tour de sa planète" : "Une année", durationText(b.periodYears), Statut::Mesure, "durée d'un tour"});
            if (const int moons = childCount(Kind::Planet); moons > 0) out.push_back({"Lunes dans l'appli", std::to_string(moons), Statut::Mesure, "éphémérides des satellites du JPL"});
            break;
        }
        case Kind::Star: {
            out.push_back({"Distance", frDistance(dSun), today ? Statut::Mesure : Statut::Calcule, today ? "parallaxe mesurée (Hipparcos, Gaia)" : "départ mesuré, orbite calculée"});
            out.push_back({"Température", frInt(4600.0 * (1.0 / (0.92 * b.bv + 1.7) + 1.0 / (0.92 * b.bv + 0.62))) + " K", Statut::Calcule, "calculée d'après la couleur"});
            if (b.radiusKm > 0) out.push_back({"Taille", frNum(b.radiusKm / rayon_etoile::kRsoleilKm, b.radiusKm > 1.0e7 ? 0 : 2) + " × le Soleil", Statut::Calcule, "approchée par l'éclat et la couleur"});
            if (!b.planetLines.empty()) out.push_back({"Planètes connues", std::to_string(b.planetLines.size()), Statut::Mesure, "NASA Exoplanet Archive"});
            else out.push_back({"Vitesse", frNum(sim.speedKms(f)) + " km/s", Statut::Mesure, "par rapport au Soleil"});
            break;
        }
        case Kind::Galaxy: {
            if (b.structure && b.name == "Univers observable") out.push_back({"Rayon", "46,2 milliards d'al", Statut::Calcule, "Planck 2018"});
            else if (b.structure && b.name == "Fond diffus cosmologique") out.push_back({"Rayon", "45,3 milliards d'al (z = 1 090)", Statut::Calcule, "Planck 2018 ; carte : Planck SMICA 2018, mesurée"});
            else out.push_back({"Distance", frDistance(dSun), sim.deepTime() ? Statut::Calcule : b.structure ? Statut::Publie : Statut::Mesure, sim.deepTime() ? "calcul de la rencontre avec Andromède" : "catalogue cité dans la fiche"});
            out.push_back({"Nature", natureOf(b), Statut::Aucun, ""});
            if (!b.blackHoleText.empty()) out.push_back({"Trou noir central", "masse mesurée", Statut::Mesure, b.blackHoleText});
            break;
        }
        case Kind::Probe: {
            out.push_back({"Distance au Soleil", frDistance(dSun), sim.years <= kStartYears ? Statut::Mesure : Statut::Calcule, "trajectoire JPL Horizons"});
            const int earth = bodyByName(sim, "Terre");
            if (earth >= 0 && sim.visible(earth)) out.push_back({"Distance à la Terre", frDistance(distBetween(p, sim.position(earth))), sim.years <= kStartYears ? Statut::Mesure : Statut::Calcule, "trajectoire JPL Horizons"});
            break;
        }
        case Kind::Asteroid: {
            out.push_back({"Distance au Soleil", frDistance(dSun), Statut::Calcule, "d'après son orbite mesurée (JPL)"});
            if (sim.asteroidCat && sim.asteroidSel >= 0) {
                const size_t k = static_cast<size_t>(sim.asteroidSel);
                if (sim.asteroidCat->eccentricity(k) < 1.0) out.push_back({"Une année", durationText(sim.asteroidCat->periodYears(k)), Statut::Mesure, "orbite du JPL"});
                else out.push_back({"Orbite", "ouverte : ne revient pas", Statut::Mesure, "orbite du JPL"});
            }
            break;
        }
        default: break;
    }
    if (out.size() > 4) out.resize(4);
    return out;
}

// Les tuiles en grille de deux colonnes.
void drawKeyFacts(const Sim& sim, const UiState& ui, int f) {
    const std::vector<Tuile> facts = keyFacts(sim, f);
    if (facts.empty()) return;
    const float gap = px(ui, 8);
    const float w = (ImGui::GetContentRegionAvail().x - gap) * 0.5f;
    for (size_t i = 0; i < facts.size(); ++i) {
        if (i % 2) ImGui::SameLine(0, gap);
        ImGui::PushID(static_cast<int>(i));
        drawTile(ui, facts[i], facts.size() == 1 ? w * 2 + gap : w);
        ImGui::PopID();
    }
}

// Texte d'un astre : les deux premières phrases d'abord ; « Lire la suite » montre le reste.
void drawSummaryText(const char* text, int focus) {
    static int openFor = -1;
    const std::string all = text;
    size_t cut = std::string::npos, from = 0;
    for (int k = 0; k < 2; ++k) {
        const size_t dot = all.find(". ", from);
        if (dot == std::string::npos) break;
        cut = dot + 1;
        from = dot + 2;
    }
    const bool longText = cut != std::string::npos && all.size() > cut + 40;
    const bool open = openFor == focus;
    ImGui::PushTextWrapPos(0.0f);
    ImGui::TextUnformatted(longText && !open ? all.substr(0, cut).c_str() : all.c_str());
    ImGui::PopTextWrapPos();
    if (!longText) return;
    ImGui::PushStyleColor(ImGuiCol_Text, theme::v4(theme::kAccent));
    ImGui::PushFont(gFontSmall ? gFontSmall : ImGui::GetFont());
    if (ImGui::Selectable(open ? "Moins##texte" : "Lire la suite##texte", false, 0, {ImGui::CalcTextSize("Lire la suite").x + 8, 0})) openFor = open ? -1 : focus;
    ImGui::PopFont();
    ImGui::PopStyleColor();
}

}  // namespace
