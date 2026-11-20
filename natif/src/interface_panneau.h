// Appli PC « Univers » : panneau d'information à droite, le « bac à sable » (demande de Marc, 18/11/2026 : interface
// très retravaillée, informative, avec images, explications, courbes et analyses ; paramètres modifiables ; orbites de
// tout objet). Trois onglets :
//   Astre    : image, explication, valeurs (mesurées ou calculées, dites telles), courbe de son orbite et analyse ;
//   Univers  : l'époque choisie sur la frise, la courbe de l'expansion, la composition et le destin de l'univers ;
//   Réglages : énergie noire, matière, vitesse d'expansion, matière noire et barre de la Voie lactée. Ce qui est recalculé
//              en direct le dit ; ce qui ne l'est pas (le film précalculé de la rencontre avec Andromède) le dit aussi.
// Fermé, le panneau laisse une fine colonne de trois boutons sur le bord droit.
#pragma once
#include <cstdarg>

#include "interface_cosmo_courbes.h"
#include "interface_images.h"
#include "interface_savoir.h"
#include "interface_temps.h"
#include "orbites_objet.h"

namespace {

struct BacState {
    int tab = 0;               // 0 Astre, 1 Univers, 2 Réglages
    bool open = true;
    bool showOrbit = true;     // orbite de l'astre suivi tracée dans la vue
    int lastFocus = -1;
    int epoch = -1;            // époque choisie sur la frise (rang dans kEpochs), -1 : aucune
    double pickSinceBigBangGa = -1;      // instant choisi dans la partie « histoire » de la frise
    SandboxGalaxy sandbox;
    ObjectTrack track;
    CosmoHistory history, reference;
    float panelLeft = 1e9f;    // bord gauche du panneau (image précédente), pour ne pas poser d'autres fenêtres dessous
    float friseTop = 1e9f;     // haut de la frise (image précédente)
};
BacState gBac;

// Texte secondaire qui revient à la ligne (le panneau est étroit).
void note(const char* fmt, ...) {
    char buf[1024];
    va_list args;
    va_start(args, fmt);
    std::vsnprintf(buf, sizeof buf, fmt, args);
    va_end(args);
    ImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyleColorVec4(ImGuiCol_TextDisabled));
    ImGui::TextWrapped("%s", buf);
    ImGui::PopStyleColor();
}

const ImU32 kWhatIf = IM_COL32(110, 215, 235, 230);
const ImU32 kGrid = IM_COL32(120, 135, 165, 60);

// ---------------------------------------------------------------- courbe

// Une courbe (et sa variante « et si… ») avec ses bornes, la date montrée et la valeur sous la souris.
void plotSeries(const UiState& ui, const char* id, const std::vector<double>& x, const std::vector<float>& y, const std::vector<float>* y2,
                double xNow, const char* xUnit, double xScale, const char* yUnit, float height, double xOrigin = 0.0) {
    if (x.size() < 2 || y.size() != x.size()) return;
    const float wAvail = ImGui::GetContentRegionAvail().x;
    const ImVec2 p0 = ImGui::GetCursorScreenPos();
    ImGui::InvisibleButton(id, {wAvail, height});
    const bool hov = ImGui::IsItemHovered();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const float padL = px(ui, 6), padB = px(ui, 18);
    const ImVec2 a{p0.x + padL, p0.y + px(ui, 4)}, b{p0.x + wAvail, p0.y + height - padB};
    float lo = *std::min_element(y.begin(), y.end()), hi = *std::max_element(y.begin(), y.end());
    if (y2 && y2->size() == x.size()) {
        lo = std::min(lo, *std::min_element(y2->begin(), y2->end()));
        hi = std::max(hi, *std::max_element(y2->begin(), y2->end()));
    }
    if (hi - lo < 1e-9f * std::max(1.0f, std::fabs(hi))) { hi += 0.5f; lo -= 0.5f; }
    const bool positive = lo >= 0;
    const float pad = (hi - lo) * 0.08f;
    lo -= pad;
    hi += pad;
    if (positive) lo = std::max(lo, 0.0f);      // une distance ou une taille ne descend pas sous zéro
    const double x0 = x.front(), x1 = x.back();
    auto X = [&](double v) { return a.x + static_cast<float>((v - x0) / (x1 - x0)) * (b.x - a.x); };
    auto Y = [&](float v) { return b.y - (v - lo) / (hi - lo) * (b.y - a.y); };
    dl->AddRectFilled(a, b, IM_COL32(12, 16, 28, 160), 6.0f * ui.s);
    for (int k = 1; k < 4; ++k) dl->AddLine({a.x, a.y + (b.y - a.y) * k / 4}, {b.x, a.y + (b.y - a.y) * k / 4}, kGrid);
    auto line = [&](const std::vector<float>& v, ImU32 col, bool dashed) {
        for (size_t i = 1; i < v.size(); ++i) {
            if (dashed && (i / 4) % 2) continue;
            dl->AddLine({X(x[i - 1]), Y(v[i - 1])}, {X(x[i]), Y(v[i])}, col, 1.6f * ui.s);
        }
    };
    if (y2 && y2->size() == x.size()) line(*y2, kWhatIf, true);
    line(y, kAccent, false);
    if (xNow >= x0 && xNow <= x1) {
        const float xn = X(xNow);
        dl->AddLine({xn, a.y}, {xn, b.y}, IM_COL32(255, 255, 255, 120), 1.0f * ui.s);
    }
    char buf[96];
    std::snprintf(buf, sizeof buf, "%s %s", frNum(hi, 3).c_str(), yUnit);
    dl->AddText({a.x + px(ui, 4), a.y + px(ui, 2)}, IM_COL32(200, 206, 220, 200), buf);
    std::snprintf(buf, sizeof buf, "%s %s", frNum(lo, 3).c_str(), yUnit);
    dl->AddText({a.x + px(ui, 4), b.y - ImGui::GetFontSize() - px(ui, 2)}, IM_COL32(200, 206, 220, 200), buf);
    std::snprintf(buf, sizeof buf, "%s", (frNum((x0 - xOrigin) * xScale, 3) + " " + xUnit).c_str());
    dl->AddText({a.x, b.y + px(ui, 2)}, IM_COL32(170, 178, 196, 200), buf);
    std::snprintf(buf, sizeof buf, "%s", (frNum((x1 - xOrigin) * xScale, 3) + " " + xUnit).c_str());
    dl->AddText({b.x - ImGui::CalcTextSize(buf).x, b.y + px(ui, 2)}, IM_COL32(170, 178, 196, 200), buf);
    if (!hov) return;
    const float mx = ImGui::GetIO().MousePos.x;
    const double xv = x0 + (mx - a.x) / (b.x - a.x) * (x1 - x0);
    const size_t i = static_cast<size_t>(std::clamp<long>(std::lower_bound(x.begin(), x.end(), xv) - x.begin(), 0, static_cast<long>(x.size()) - 1));
    dl->AddCircleFilled({X(x[i]), Y(y[i])}, 3.5f * ui.s, kAccent);
    if (y2 && y2->size() == x.size()) dl->AddCircleFilled({X(x[i]), Y((*y2)[i])}, 3.5f * ui.s, kWhatIf);
    if (y2 && y2->size() == x.size())
        ImGui::SetTooltip("%s %s : %s %s (réel)  •  %s %s (et si…)", frNum((x[i] - xOrigin) * xScale, 4).c_str(), xUnit, frNum(y[i], 4).c_str(), yUnit,
                          frNum((*y2)[i], 4).c_str(), yUnit);
    else
        ImGui::SetTooltip("%s %s : %s %s", frNum((x[i] - xOrigin) * xScale, 4).c_str(), xUnit, frNum(y[i], 4).c_str(), yUnit);
}

// ---------------------------------------------------------------- analyse d'une orbite

struct OrbitFacts {
    double rMin = 0, rMax = 0, tMin = 0, zMax = 0, periodMa = 0;
    bool ok = false;
};

// Étoile : rayons extrêmes, hauteur au-dessus du plan, durée moyenne d'un tour (angle parcouru sur la fenêtre).
OrbitFacts starFacts(const std::vector<phys::Vec3>& g, const std::vector<double>& t) {
    OrbitFacts f;
    if (g.size() < 3 || t.size() != g.size()) return f;
    f.rMin = 1e300;
    double turned = 0, prev = std::atan2(g[0].y, g[0].x);
    for (size_t i = 0; i < g.size(); ++i) {
        const double R = std::sqrt(g[i].x * g[i].x + g[i].y * g[i].y);
        if (R < f.rMin) { f.rMin = R; f.tMin = t[i]; }
        f.rMax = std::max(f.rMax, R);
        f.zMax = std::max(f.zMax, std::fabs(g[i].z));
        const double ang = std::atan2(g[i].y, g[i].x);
        double d = ang - prev;
        if (d > kPi) d -= 2 * kPi;
        if (d < -kPi) d += 2 * kPi;
        turned += d;
        prev = ang;
    }
    const double span = (t.back() - t.front()) / 1.0e6;
    if (std::fabs(turned) > 1e-6) f.periodMa = span * 2 * kPi / std::fabs(turned);
    f.ok = true;
    return f;
}

// ---------------------------------------------------------------- onglet Astre

// Dates de la rencontre rejouée (groupe_local_scenario.h) : valeurs mesurées, puis tes réglages.
std::string mergeText(const scenario::Result& r) {
    return r.mergeM31Ga > 0 ? "dans " + frNum(r.mergeM31Ga, 3) + " milliards d'années" : "pas avant 10 milliards d'années";
}

void groupFacts(const UiState& ui, const ObjectTrack& tr) {
    if (!tr.groupBase.ok) return;
    row("Voie lactée et Andromède fusionnent", mergeText(tr.groupBase), "calculé, valeurs mesurées", ui.s);
    if (tr.groupWhatIf.ok) {
        ImGui::TextColored(ImGui::ColorConvertU32ToFloat4(kWhatIf), "Et si… (tes réglages)");
        row("Elles fusionnent", mergeText(tr.groupWhatIf), "calculé", ui.s);
        if (tr.groupWhatIf.periM31Ga > 0)
            row("Premier passage d'Andromède", "dans " + frNum(tr.groupWhatIf.periM31Ga, 3) + " milliards d'années, à " +
                frNum(tr.groupWhatIf.periM31Kpc * orbite::kKpcLy / 1000.0, 3) + " milliers d'al", "calculé", ui.s);
        note("Modèle simplifié : centres des cinq galaxies seulement (pas leurs formes), même physique que la référence de l'appli.");
    } else {
        note("Onglet Réglages : change l'énergie noire ou la matière noire pour voir la rencontre « et si… ».");
    }
}

// Les gestes de l'ancienne fiche : s'approcher, revenir, prochaine éclipse, revenir au Soleil.
void bodyActions(Sim& sim, UiState& ui, int f) {
    const Body& b = sim.bodies[static_cast<size_t>(f)];
    bool line = false;
    auto next = [&]() { if (line) ImGui::SameLine(); line = true; };
    if (sim.dist > 1.5 * sim.arriveDist(f, 1e300) && !sim.flying) {
        next();
        if (ImGui::Button("S'en approcher")) goToBody(sim, ui, f);
    }
    // Planètes connues de cette étoile (exoplanetes.h) : vol jusqu'à 4 fois la plus grande orbite.
    if (b.planetsReachLy > 0 && sim.dist > 20.0 * b.planetsReachLy && !sim.flying) {
        next();
        if (ImGui::Button("Voir ses planètes")) sim.flyTo(f, 4.0 * b.planetsReachLy);
    }
    // Trou noir central de masse mesurée (trous_noirs.h) : vol jusqu'à 40 rayons de Schwarzschild, l'anneau de photons en vue.
    if (b.blackHole >= 0 && sim.dist > 400.0 * b.blackHoleRsLy && !sim.flying) {
        next();
        if (ImGui::Button("Voir son trou noir")) sim.flyTo(f, 40.0 * b.blackHoleRsLy);
    }
    if (!sim.history.empty()) {
        next();
        if (ImGui::Button("← Retour")) {
            ui.tour = -1;
            sim.back();
        }
    }
    const uint32_t naif = static_cast<uint32_t>(b.naif);
    if ((naif == eph::kEarth || naif == eph::kMoon) && b.kind == Kind::Planet) {
        const int ne = nextEclipse(sim.years);
        if (ne >= 0) {
            next();
            if (ImGui::Button("Prochaine éclipse")) showEclipse(sim, ui, ne);
            if (ImGui::IsItemHovered()) ImGui::SetTooltip("%s", kEclipses[ne].label);
        }
    }
    if (f != 0 && sim.visible(0)) {
        next();
        if (ImGui::Button("Revenir au Soleil")) goToBody(sim, ui, 0, 45.0 * kAuInLy);
    }
}

void bodyOrbit(Sim& sim, UiState& ui, const Body& b, int f);

void tabBody(Sim& sim, UiState& ui, const Camera& cam) {
    const int f = sim.focus;
    const Body& b = sim.bodies[static_cast<size_t>(f)];
    ImGui::PushFont(ui.big);
    ImGui::TextWrapped("%s", b.name.c_str());
    ImGui::PopFont();
    note("%s", natureOf(b).c_str());
    bodyActions(sim, ui, f);
    const BodyText* bt = bodyText(b.name);
    if (bt && bt->image && gUiImages) {
        if (const UiImages::Entry* e = gUiImages->get(bt->image)) {
            const float wImg = ImGui::GetContentRegionAvail().x;
            const float hImg = wImg * static_cast<float>(e->h) / static_cast<float>(std::max(1, e->w));
            ImGui::Image(reinterpret_cast<ImTextureID>(e->set), {wImg, hImg});
            note("Carte de sa surface (Solar System Scope, CC BY 4.0, d'après la NASA).");
        }
    }
    ImGui::Spacing();
    ImGui::TextWrapped("%s", bt ? bt->text : b.structure ? structureText() : kindText(static_cast<int>(b.kind)));
    ImGui::Spacing();

    // Orbite : courbe et analyse.
    if (ImGui::CollapsingHeader("Orbite", ImGuiTreeNodeFlags_DefaultOpen)) bodyOrbit(sim, ui, b, f);
    if (ImGui::CollapsingHeader("Valeurs", ImGuiTreeNodeFlags_DefaultOpen)) cardRows(sim, ui, cam, f);
}

// Courbe de l'orbite de l'astre suivi et son analyse (réelle, et « et si… » avec les réglages).
void bodyOrbit(Sim& sim, UiState& ui, const Body& b, int f) {
    gBac.track.update(sim, gBac.sandbox, ImGui::IsMouseDown(ImGuiMouseButton_Left) && ImGui::IsAnyItemActive());
    ObjectTrack& tr = gBac.track;
    const bool planet = b.kind == Kind::Planet;
    ImGui::Checkbox("Tracer son orbite dans la vue", &gBac.showOrbit);
    if (planet) {
        ui.orbits.update(sim);
        const auto& trk = ui.orbits.tracks[static_cast<size_t>(f)];
        if (!trk.valid || trk.pts.size() < 2 || b.periodYears <= 0) {
            note("Orbite inconnue à cette date.");
            return;
        }
        std::vector<double> xs;
        std::vector<float> rs;
        const double unit = b.parent > 0 ? kLyInKm / 1000.0 : 1.0 / kAuInLy;      // lune : milliers de km ; planète : UA
        for (size_t k = 0; k < trk.pts.size(); ++k) {
            xs.push_back(trk.atYears - sim.years + (static_cast<double>(k) / (trk.pts.size() - 1) - 0.5) * b.periodYears);      /* depuis la date montrée */
            rs.push_back(static_cast<float>(std::sqrt(dot(trk.pts[k], trk.pts[k])) * unit));
        }
        const bool days = b.periodYears < 2.0;
        ImGui::TextUnformatted(b.parent > 0 ? "Distance à sa planète sur un tour" : "Distance au Soleil sur un tour");
        plotSeries(ui, "##orb", xs, rs, nullptr, 0.0, days ? "jours" : "ans", days ? 365.25 : 1.0, b.parent > 0 ? "milliers de km" : "UA", px(ui, 130));
        const auto mm = std::minmax_element(rs.begin(), rs.end());
        row("Au plus près", frNum(*mm.first, 4) + (b.parent > 0 ? " milliers de km" : " UA"), "calculé (éphémérides)", ui.s);
        row("Au plus loin", frNum(*mm.second, 4) + (b.parent > 0 ? " milliers de km" : " UA"), "calculé (éphémérides)", ui.s);
        note("Axe : temps compté depuis la date montrée (trait blanc).");
        return;
    }
    if (tr.kind < 0) {
        note("%s", *tr.note ? tr.note : "Pas d'orbite connue pour cet astre.");
        return;
    }
    if (tr.kind == 0) {
        ImGui::TextUnformatted("Distance au centre de la Voie lactée");
        plotSeries(ui, "##orb", tr.t, tr.r, tr.hasWhatIf ? &tr.rWhatIf : nullptr, sim.years, "Ma", 1e-6, "kpc", px(ui, 140), kStartYears);
        note("Axe : millions d'années depuis aujourd'hui ; trait blanc : date montrée.");
        const OrbitFacts real = starFacts(tr.g, tr.t);
        if (real.ok) {
            row("Durée d'un tour de la Galaxie", frNum(real.periodMa, 3) + " millions d'années", "calculé", ui.s);
            row("Entre", frNum(real.rMin * orbite::kKpcLy / 1000.0, 3) + " et " + frNum(real.rMax * orbite::kKpcLy / 1000.0, 3) + " milliers d'al du centre", "calculé", ui.s);
            row("S'écarte du plan jusqu'à", frInt(real.zMax * orbite::kKpcLy) + " al", "calculé", ui.s);
        }
        if (tr.hasWhatIf) {
            const OrbitFacts wi = starFacts(tr.gWhatIf, tr.t);
            ImGui::Spacing();
            ImGui::TextColored(ImGui::ColorConvertU32ToFloat4(kWhatIf), "Et si… (tes réglages)");
            if (wi.ok) {
                row("Durée d'un tour", frNum(wi.periodMa, 3) + " millions d'années", "calculé", ui.s);
                row("Entre", frNum(wi.rMin * orbite::kKpcLy / 1000.0, 3) + " et " + frNum(wi.rMax * orbite::kKpcLy / 1000.0, 3) + " milliers d'al du centre", "calculé", ui.s);
            }
            note("Même départ mesuré ; seuls tes réglages changent (onglet Réglages).");
        } else {
            note("Onglet Réglages : change la matière noire ou l'énergie noire pour voir son orbite « et si… ».");
        }
    } else if (tr.kind == 1) {
        ImGui::TextUnformatted("Distance au centre de la Voie lactée");
        plotSeries(ui, "##orb", tr.t, tr.r, tr.hasWhatIf ? &tr.rWhatIf : nullptr, sim.years, "Ga", 1e-9, "kpc", px(ui, 140), kStartYears);
        note("Axe : milliards d'années depuis aujourd'hui ; trait blanc : date montrée.");
        groupFacts(ui, tr);
        // Galaxie déchirée par les marées (film de la rencontre, film_ancres.h) : ses étoiles sont toutes gardées et se mêlent
        // peu à peu à la Voie lactée ; on dit quelle part reste groupée autour de son cœur.
        if (const double f = sim.groupedShare(b.name); f >= 0) {
            row("Étoiles encore groupées autour de son cœur", frInt(100.0 * f) + " %", "calculé (film de la rencontre)", ui.s);
            if (f < 0.3) note("Déchirée par les marées : toutes ses étoiles sont gardées (aucune n'est retirée) et se mêlent peu à peu à la Voie lactée. Le repère suit le centre de ses étoiles.");
        }
        // Premier rapprochement après aujourd'hui (premier minimum de la distance).
        for (size_t i = 1; i + 1 < tr.r.size(); ++i)
            if (tr.t[i] > sim.years && tr.r[i] < tr.r[i - 1] && tr.r[i] <= tr.r[i + 1]) {
                row("Prochain passage au plus près", frNum(tr.r[i] * orbite::kKpcLy / 1000.0, 3) + " milliers d'al, " + relativeToToday(tr.t[i]), "calculé", ui.s);
                break;
            }
    } else {
        ImGui::TextUnformatted("Distance au Soleil");
        plotSeries(ui, "##orb", tr.t, tr.r, nullptr, sim.years, "ans", 1.0, "UA", px(ui, 130), kStartYears);
        note("Axe : années depuis aujourd'hui ; trait blanc : date montrée.");
        const auto mm = std::minmax_element(tr.r.begin(), tr.r.end());
        row("Au plus près", frNum(*mm.first, 4) + " UA", "calculé", ui.s);
        row("Au plus loin", frNum(*mm.second, 4) + " UA", "calculé", ui.s);
    }
    note("%s", tr.note);
}

// ---------------------------------------------------------------- onglet Univers

std::string sinceBigBangText(double years) {
    if (years < 1.0 / 525960.0 * 60) return frNum(years * 525960.0, 2) + " minutes après le Big Bang";
    if (years < 1.0) return frNum(years * 365.25, 3) + " jours après le Big Bang";
    if (years < 1e6) return frInt(years) + " ans après le Big Bang";
    if (years < 1e9) return frNum(years / 1e6, 3) + " millions d'années après le Big Bang";
    return frNum(years / 1e9, 4) + " milliards d'années après le Big Bang";
}


void tabUniverse(Sim& sim, UiState& ui) {
    CosmoHistory& h = gBac.history;
    h.update(sim.cosmology);
    gBac.reference.update(cosmo::Params{});
    const bool changed = !CosmoHistory::same(sim.cosmology, cosmo::Params{});
    if (gBac.epoch >= 0) {
        const Epoch& e = kEpochs[gBac.epoch];
        ImGui::PushFont(ui.big);
        ImGui::TextWrapped("%s", e.label);
        ImGui::PopFont();
        const double sinceBB = e.fromBigBang ? e.years / 1e9 : h.ageGa + e.years / 1e9;
        if (e.fromBigBang && e.years <= 0) note("Le début du temps.");
        else note("%s", e.fromBigBang ? sinceBigBangText(e.years).c_str() : relativeToToday(kStartYears + e.years).c_str());
        ImGui::TextWrapped("%s", e.text);
        const double a = h.aAtSinceBigBang(sinceBB);
        if (a > 0 && e.years != 0) {
            row("L'univers était", a < 1 ? frNum(1.0 / a, 3) + " fois plus petit" : frNum(a, 3) + " fois plus grand", "calculé, tes réglages", ui.s);
            row("Température du fond diffus", frNum(2.7255 / a, 3) + " K", "calculé", ui.s);
        }
        ImGui::Separator();
    } else if (gBac.pickSinceBigBangGa > 0) {
        const double a = h.aAtSinceBigBang(gBac.pickSinceBigBangGa);
        ImGui::TextUnformatted(("Il y a " + frNum(h.ageGa - gBac.pickSinceBigBangGa, 3) + " milliards d'années").c_str());
        if (a > 0) {
            row("L'univers était", frNum(1.0 / a, 3) + " fois plus petit", "calculé", ui.s);
            row("Température du fond diffus", frNum(2.7255 / a, 3) + " K", "calculé", ui.s);
        }
        note("Avant −1 milliard d'années, les étoiles mesurées ne peuvent pas être remontées : la vue 3D ne va pas si loin.");
        ImGui::Separator();
    }
    row("Âge de l'univers", frNum(h.ageGa, 4) + " milliards d'années", changed ? "calculé, tes réglages" : "calculé, Planck 2018", ui.s);
    // Courbe : taille de l'univers (a) depuis le Big Bang jusqu'à +40 milliards d'années.
    std::vector<double> xs;
    std::vector<float> ys, yr;
    for (int i = 0; i <= 200; ++i) {
        const double t = (h.ageGa + 40.0) * i / 200.0;
        const double a1 = h.aAtSinceBigBang(t), a0 = gBac.reference.aAtSinceBigBang(t);
        xs.push_back(t);
        ys.push_back(static_cast<float>(a1 < 0 ? (h.rip ? 50.0 : 0.0) : std::min(a1, 50.0)));
        yr.push_back(static_cast<float>(a0 < 0 ? 0.0 : std::min(a0, 50.0)));
    }
    ImGui::TextUnformatted("Taille de l'univers (1 = aujourd'hui)");
    plotSeries(ui, "##a", xs, changed ? ys : yr, changed ? &yr : nullptr, h.ageGa, "Ga", 1.0, "", px(ui, 150));
    if (changed) note("Orange : tes réglages. Bleu pointillé : valeurs mesurées (Planck 2018).");
    note("Axe : milliards d'années depuis le Big Bang ; trait blanc : aujourd'hui.");
    // Composition aujourd'hui.
    const cosmo::Params& c = sim.cosmology;
    struct Part { const char* label; double v; ImU32 col; } parts[] = {
        {"Énergie noire", c.ode, IM_COL32(110, 215, 235, 255)}, {"Matière (dont noire)", c.om, IM_COL32(255, 196, 110, 255)},
        {"Rayonnement", c.omegaR(), IM_COL32(240, 120, 120, 255)}};
    ImGui::Spacing();
    ImGui::TextUnformatted("De quoi est fait l'univers aujourd'hui");
    {
        const float wBar = ImGui::GetContentRegionAvail().x, hBar = px(ui, 14);
        const ImVec2 p0 = ImGui::GetCursorScreenPos();
        ImGui::Dummy({wBar, hBar});
        ImDrawList* dl = ImGui::GetWindowDrawList();
        double sum = 0;
        for (const Part& p : parts) sum += std::max(0.0, p.v);
        float x = p0.x;
        for (const Part& p : parts) {
            const float wPart = static_cast<float>(std::max(0.0, p.v) / std::max(sum, 1e-9)) * wBar;
            dl->AddRectFilled({x, p0.y}, {x + wPart, p0.y + hBar}, p.col, 3.0f * ui.s);
            x += wPart;
        }
        for (const Part& p : parts) {
            ImGui::ColorButton(p.label, ImGui::ColorConvertU32ToFloat4(p.col), ImGuiColorEditFlags_NoTooltip, {px(ui, 10), px(ui, 10)});
            ImGui::SameLine();
            note("%s : %s %%", p.label, frNum(100.0 * p.v, 3).c_str());
        }
    }
    const double q = h.q0();
    row("L'expansion aujourd'hui", q < 0 ? "accélère" : "ralentit", "calculé", ui.s);
    const double ok = c.omegaK();
    row("Forme de l'espace", std::fabs(ok) < 0.005 ? "plat" : ok > 0 ? "ouvert" : "fermé", "calculé", ui.s);
    if (h.crunch) row("Destin", "retombe sur lui-même dans " + frNum(h.endGa, 3) + " milliards d'années", "calculé", ui.s);
    else if (h.rip) row("Destin", "se déchire dans " + frNum(h.endGa, 3) + " milliards d'années", "calculé", ui.s);
    else row("Destin", "s'agrandit sans fin (au moins 60 milliards d'années)", "calculé", ui.s);
}

// ---------------------------------------------------------------- onglet Réglages

void tabSettings(Sim& sim, UiState& ui) {
    cosmo::Params& c = sim.cosmology;
    float h0 = static_cast<float>(c.h0), om = static_cast<float>(c.om), ode = static_cast<float>(c.ode), w0 = static_cast<float>(c.w0), wa = static_cast<float>(c.wa);
    ImGui::TextWrapped("Change les lois de l'univers. Les galaxies lointaines, la courbe de l'univers et l'orbite « et si… » de l'astre suivi "
                       "se recalculent aussitôt.");
    ImGui::Spacing();
    ImGui::SeparatorText("Essais rapides");
    auto preset = [&](const char* label, double nh0, double nom, double node, double nw0, double nwa, const char* tip) {
        if (ImGui::Button(label)) {
            c.h0 = nh0; c.om = nom; c.ode = node; c.w0 = nw0; c.wa = nwa;
            sim.cosmologyDirty = true;
        }
        if (ImGui::IsItemHovered()) ImGui::SetTooltip("%s", tip);
    };
    preset("Valeurs mesurées", 67.4, 0.315, 0.685, -1.0, 0.0, "Planck 2018 : l'univers tel qu'on le mesure.");
    ImGui::SameLine();
    preset("Sans énergie noire", 67.4, 1.0, 0.0, -1.0, 0.0, "Seulement de la matière : l'expansion ralentit toujours.");
    preset("Énergie noire x 1,3", 67.4, 0.11, 0.89, -1.0, 0.0, "Plus d'énergie noire, univers toujours plat.");
    ImGui::SameLine();
    preset("Grande Déchirure", 67.4, 0.315, 0.685, -1.5, 0.0, "Énergie noire « fantôme » (w0 = -1,5) : tout finit déchiré.");
    preset("Univers fermé", 67.4, 2.0, 0.0, -1.0, 0.0, "Beaucoup de matière, pas d'énergie noire : l'univers retombe sur lui-même.");
    {
        CosmoHistory& hc = gBac.history;
        hc.update(c);
        note("Résultat (calculé) : âge %s milliards d'années ; expansion qui %s ; %s.", frNum(hc.ageGa, 4).c_str(), hc.q0() < 0 ? "accélère" : "ralentit",
                            hc.crunch ? ("retombe dans " + frNum(hc.endGa, 3) + " milliards d'années").c_str()
                            : hc.rip  ? ("se déchire dans " + frNum(hc.endGa, 3) + " milliards d'années").c_str()
                                      : "s'agrandit sans fin");
    }
    ImGui::SeparatorText("Expansion de l'univers");
    ImGui::PushItemWidth(-px(ui, 4));
    bool changed = false;
    changed |= ImGui::SliderFloat("##h0", &h0, 50.0f, 90.0f, "Vitesse d'expansion : %.1f km/s par Mpc");
    changed |= ImGui::SliderFloat("##om", &om, 0.02f, 2.0f, "Part de matière : %.3f");
    changed |= ImGui::SliderFloat("##ode", &ode, 0.0f, 1.5f, "Part d'énergie noire : %.3f");
    changed |= ImGui::SliderFloat("##w0", &w0, -2.0f, -0.4f, "Énergie noire, w0 : %.2f");
    changed |= ImGui::SliderFloat("##wa", &wa, -2.0f, 1.0f, "Énergie noire, wa : %.2f");
    if (changed) {
        c.h0 = h0; c.om = om; c.ode = ode; c.w0 = w0; c.wa = wa;
        sim.cosmologyDirty = true;
    }
    note("w0 = -1 et wa = 0 : énergie noire constante. Mesuré : Planck 2018.");
    ImGui::SeparatorText("Notre galaxie");
    ImGui::SliderFloat("##halo", &gBac.sandbox.haloFactor, 0.2f, 3.0f, "Matière noire des galaxies : x %.2f");
    ImGui::Checkbox("Barre au centre de la Voie lactée", &gBac.sandbox.bar);
    ImGui::Checkbox("L'énergie noire agit aussi dans la galaxie", &gBac.sandbox.useCosmologyLambda);
    if (ImGui::Button("Galaxie comme mesurée")) gBac.sandbox = SandboxGalaxy{};
    ImGui::PopItemWidth();
    note("Ces réglages changent l'orbite « et si… » de l'astre suivi (étoile, Soleil ou galaxie du Groupe local), en bleu pointillé.");
    ImGui::SeparatorText("Rencontre avec Andromède");
    {
        static scenario::Result base, what;
        static scenario::Settings used{-1, -1};
        const bool moving = ImGui::IsMouseDown(ImGuiMouseButton_Left) && ImGui::IsAnyItemActive();
        const scenario::Settings now = gBac.sandbox.groupSettings(c);
        if (sim.centres && sim.centres->ready && !moving && (now.massFactor != used.massFactor || now.K != used.K)) {
            if (!base.ok) base = scenario::run(*sim.centres, scenario::Settings{});
            what = scenario::run(*sim.centres, now);
            used = now;
        }
        if (base.ok) {
            row("Fusion, valeurs mesurées", mergeText(base), "calculé", ui.s);
            if (what.ok) row("Fusion, tes réglages", mergeText(what), "calculé", ui.s);
            note("Rejouée en direct : centres des cinq galaxies du Groupe local (même physique que la référence de l'appli). "
                 "Choisis Andromède pour voir son chemin « et si… ».");
        } else {
            note("Centres de référence absents : rencontre non rejouée.");
        }
    }
    ImGui::SeparatorText("Ce qui ne change pas");
    ImGui::TextWrapped("Les formes des galaxies pendant la rencontre (film calculé à l'avance, plusieurs heures sur la carte graphique) "
                       "et le mouvement des millions d'étoiles affichées restent ceux des valeurs mesurées.");
}

// ---------------------------------------------------------------- panneau et colonne

void drawObjectOrbit(Sim& sim, UiState& ui, const Camera& cam, float w, float h) {
    if (!gBac.showOrbit) return;
    const Body& b = sim.bodies[static_cast<size_t>(sim.focus)];
    if (b.kind == Kind::Planet) return;      // déjà tracée par drawOrbits
    gBac.track.update(sim, gBac.sandbox, ImGui::IsMouseDown(ImGuiMouseButton_Left) && ImGui::IsAnyItemActive());
    const ObjectTrack& tr = gBac.track;
    if (tr.kind < 0 || tr.g.size() < 2) return;
    // Une orbite autour de la Galaxie (des dizaines de milliers d'al) n'est tracée que vue d'assez loin : de près, elle
    // traverserait l'écran comme une droite. Même règle pour le chemin d'une galaxie.
    if ((tr.kind == 0 && sim.dist < 300.0) || (tr.kind == 1 && sim.dist < 2.0e5)) return;
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    auto draw = [&](const std::vector<phys::Vec3>& pts, ImU32 col, bool dashed) {
        ImVec2 prev;
        bool hasPrev = false;
        for (size_t i = 0; i < pts.size(); ++i) {
            ImVec2 at;
            const bool ok = projectLoose(cam, tr.world(sim, pts[i]), w, h, at);
            // Le passé en plus pâle que l'avenir : on voit d'où l'astre vient et où il va.
            const bool past = tr.t.size() == pts.size() && tr.t[i] < sim.years;
            const ImU32 c = past ? (col & 0x00FFFFFF) | (static_cast<ImU32>(((col >> 24) & 0xFF) * 0.45f) << 24) : col;
            if (ok && hasPrev && !(dashed && (i / 6) % 2)) dl->AddLine(prev, at, c, 1.4f * ui.s);
            prev = at;
            hasPrev = ok;
        }
    };
    gBac.track.prepareFrame(sim);
    if (tr.hasWhatIf) draw(tr.gWhatIf, kWhatIf, true);
    draw(tr.g, IM_COL32(255, 196, 110, 170), false);
}

// Colonne des trois onglets, sur le bord droit, quand le panneau est fermé.
void drawRail(UiState& ui, float w, float h, ImGuiWindowFlags fixed) {
    ImGui::SetNextWindowPos({w - px(ui, 12), h * 0.42f}, 0, {1, 0.5f});
    ImGui::Begin("colonne", nullptr, fixed);
    const char* labels[] = {"Astre", "Univers", "Réglages"};
    for (int i = 0; i < 3; ++i)
        if (ImGui::Button(labels[i], {px(ui, 92), 0})) {
            gBac.open = true;
            gBac.tab = i;
        }
    ImGui::End();
    gBac.panelLeft = w;
}

// Contrôles sans fenêtre : UNIVERS_PANNEAU=astre | univers[:<époque>] | reglages | ferme, suivi au besoin de
// « ,halo:<facteur> », « ,w0:<valeur> », « ,ode:<valeur> » (réglages posés avant la capture).
void panelTestHook(Sim& sim) {
    static bool done = false;
    if (done) return;
    done = true;
    const char* env = std::getenv("UNIVERS_PANNEAU");
    if (!env) return;
    std::string s = env;
    size_t at = 0;
    while (at <= s.size()) {
        const size_t comma = s.find(',', at);
        const std::string part = s.substr(at, comma == std::string::npos ? std::string::npos : comma - at);
        const size_t colon = part.find(':');
        const std::string key = part.substr(0, colon), val = colon == std::string::npos ? "" : part.substr(colon + 1);
        if (key == "astre") gBac.tab = 0;
        else if (key == "univers") { gBac.tab = 1; if (!val.empty()) gBac.epoch = std::clamp(std::atoi(val.c_str()), 0, kEpochCount - 1); }
        else if (key == "reglages") gBac.tab = 2;
        else if (key == "ferme") gBac.open = false;
        else if (key == "halo") gBac.sandbox.haloFactor = static_cast<float>(std::atof(val.c_str()));
        else if (key == "w0") { sim.cosmology.w0 = std::atof(val.c_str()); sim.cosmologyDirty = true; }
        else if (key == "ode") { sim.cosmology.ode = std::atof(val.c_str()); sim.cosmologyDirty = true; }
        else if (key == "om") { sim.cosmology.om = std::atof(val.c_str()); sim.cosmologyDirty = true; }
        if (comma == std::string::npos) break;
        at = comma + 1;
    }
    gBac.lastFocus = sim.focus;
}

void drawPanel(Sim& sim, UiState& ui, const Camera& cam, float w, float h, float top, float bottom) {
    panelTestHook(sim);
    if (sim.focus != gBac.lastFocus) {
        gBac.lastFocus = sim.focus;
        if (gBac.tab != 0 && !ImGui::GetIO().WantCaptureMouse) gBac.tab = 0;      // un nouvel astre : sa fiche
    }
    const ImGuiWindowFlags flags = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoTitleBar |
                                   ImGuiWindowFlags_NoSavedSettings;
    if (!gBac.open) {
        drawRail(ui, w, h, flags | ImGuiWindowFlags_AlwaysAutoResize);
        return;
    }
    const float pw = std::min(px(ui, 440), w * 0.4f);
    ImGui::SetNextWindowPos({w - px(ui, 16), top}, 0, {1, 0});
    ImGui::SetNextWindowSize({pw, std::max(px(ui, 200), bottom - top)});
    ImGui::PushStyleColor(ImGuiCol_SliderGrab, ImVec4{1.0f, 0.77f, 0.43f, 0.95f});
    ImGui::PushStyleColor(ImGuiCol_SliderGrabActive, ImVec4{1.0f, 0.85f, 0.60f, 1.0f});
    ImGui::PushStyleColor(ImGuiCol_CheckMark, ImVec4{1.0f, 0.77f, 0.43f, 1.0f});
    ImGui::Begin("panneau", nullptr, flags);
    gBac.panelLeft = ImGui::GetWindowPos().x;
    const char* labels[] = {"Astre", "Univers", "Réglages"};
    for (int i = 0; i < 3; ++i) {
        if (i) ImGui::SameLine();
        const bool on = gBac.tab == i;
        if (on) ImGui::PushStyleColor(ImGuiCol_Button, ImVec4{0.80f, 0.58f, 0.25f, 0.85f});
        if (ImGui::Button(labels[i])) gBac.tab = i;
        if (on) ImGui::PopStyleColor();
    }
    ImGui::SameLine(ImGui::GetContentRegionMax().x - px(ui, 28));
    if (ImGui::SmallButton(" × ")) gBac.open = false;
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Fermer le panneau");
    ImGui::Separator();
    ImGui::BeginChild("contenu", {0, 0}, ImGuiChildFlags_None, ImGuiWindowFlags_NoBackground);
    if (gBac.tab == 0) tabBody(sim, ui, cam);
    else if (gBac.tab == 1) tabUniverse(sim, ui);
    else tabSettings(sim, ui);
    ImGui::EndChild();
    ImGui::End();
    ImGui::PopStyleColor(3);
}

}  // namespace
