// Appli PC « Univers » : frise du temps de l'univers, en bas de l'écran (demande de Marc, 18/11/2026 : « une frise du
// temps de l'univers où choisir la période »).
//
// Deux parties, côte à côte :
//   À gauche, toute l'histoire, du Big Bang à −1 milliard d'années, en échelle logarithmique (3 minutes et 13 milliards
//   d'années tiennent sur la même ligne). Sa couleur est la température du rayonnement à cet instant (calculée avec les
//   réglages en cours : 2,7255 K / a). Un clic choisit une époque : le panneau « Univers » l'explique. La vue 3D n'y va
//   pas : avant −1 milliard d'années, les étoiles mesurées ne peuvent pas être remontées.
//   À droite, le temps que l'appli simule, de −1 milliard d'années à la fin du calcul (environ +10 milliards), centré sur
//   aujourd'hui en échelle « logarithmique des deux côtés » : un siècle, un million d'années et un milliard d'années y
//   ont chacun leur place. Un clic ou un glisser y pose la date (sim.years, bornée comme ailleurs).
#pragma once
#include "interface_panneau.h"

namespace {

struct FriseGeom {
    float x0, x1, y0, y1;       // cadre
    float aL, aR, bL, bR;       // partie « histoire » [aL, aR], partie « simulée » [bL, bR]
    double logLo, logHi;        // histoire : log10(années depuis le Big Bang)
    double sLo, sHi;            // simulée : s(dt) = signe(dt) log10(1 + |dt| / 1 an)
};

double symLog(double dt) { return dt >= 0 ? std::log10(1.0 + dt) : -std::log10(1.0 - dt); }
double symLogInv(double s) { return s >= 0 ? std::pow(10.0, s) - 1.0 : 1.0 - std::pow(10.0, -s); }

// Couleur d'une température de rayonnement : bleu nuit à froid, puis rouge, orange, blanc. Repère visuel seulement :
// la valeur exacte est dans l'info-bulle.
ImU32 heatColor(double kelvin) {
    const double u = std::clamp((std::log10(std::max(kelvin, 1.0)) - 0.4) / 3.6, 0.0, 1.0);      // 2,5 K à 10 000 K
    const float r = static_cast<float>(std::clamp(u * 2.2 - 0.25, 0.08, 1.0)), g = static_cast<float>(std::clamp(u * 1.8 - 0.75, 0.10, 1.0));
    const float b = static_cast<float>(u < 0.35 ? 0.35 + u * 0.6 : std::clamp((u - 0.75) * 3.0, 0.15, 1.0));
    return ImGui::ColorConvertFloat4ToU32({r, g, b, 0.95f});
}


void drawFrise(Sim& sim, UiState& ui, float h, float height) {
    CosmoHistory& hist = gBac.history;
    hist.update(sim.cosmology);
    const double ageYears = hist.ageGa * 1e9;
    const float m = px(ui, 16);
    ImGui::SetNextWindowPos({m, h - m}, 0, {0, 1});
    ImGui::SetNextWindowSize({std::max(px(ui, 300), std::min(gBac.panelLeft, ImGui::GetIO().DisplaySize.x) - 2 * m), height});
    ImGui::Begin("frise", nullptr, ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoTitleBar |
                                       ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoScrollbar);
    gBac.friseTop = ImGui::GetWindowPos().y;
    const ImVec2 o = ImGui::GetCursorScreenPos();
    const float W = ImGui::GetContentRegionAvail().x, H = ImGui::GetContentRegionAvail().y;
    ImGui::InvisibleButton("##frise", {W, H});
    const bool hov = ImGui::IsItemHovered(), active = ImGui::IsItemActive();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const float labelH = ImGui::GetFontSize();
    FriseGeom g{};
    g.x0 = o.x;
    g.x1 = o.x + W;
    g.y0 = o.y + labelH + px(ui, 6);
    g.y1 = g.y0 + px(ui, 16);
    g.aL = g.x0;
    g.aR = g.x0 + W * 0.28f;
    g.bL = g.aR + px(ui, 18);
    g.bR = g.x1;
    const double histEnd = std::max(ageYears + (sim.minYears() - kStartYears), 1.0);      // −1 milliard d'années
    g.logLo = std::log10(1.0 / 525960.0);      // 1 minute
    g.logHi = std::log10(histEnd);
    g.sLo = symLog(sim.minYears() - kStartYears);
    g.sHi = symLog(sim.maxYears() - kStartYears);
    auto xHist = [&](double yearsBB) { return g.aL + static_cast<float>((std::log10(std::max(yearsBB, 1e-12)) - g.logLo) / (g.logHi - g.logLo)) * (g.aR - g.aL); };
    auto xSim = [&](double dt) { return g.bL + static_cast<float>((symLog(dt) - g.sLo) / (g.sHi - g.sLo)) * (g.bR - g.bL); };

    // Partie histoire : couleur de la température du rayonnement.
    const int slices = 90;
    for (int i = 0; i < slices; ++i) {
        const double l = g.logLo + (g.logHi - g.logLo) * (i + 0.5) / slices;
        const double a = hist.aAtSinceBigBang(std::pow(10.0, l) / 1e9);
        const ImU32 col = heatColor(a > 0 ? 2.7255 / a : 1e4);
        dl->AddRectFilled({g.aL + (g.aR - g.aL) * i / slices, g.y0}, {g.aL + (g.aR - g.aL) * (i + 1) / slices + 0.5f, g.y1}, col);
    }
    dl->AddText({g.aL, o.y}, IM_COL32(200, 206, 220, 220), "Histoire de l'univers");
    // Lien entre les deux parties.
    dl->AddText({g.aR + px(ui, 3), g.y0 - px(ui, 3)}, IM_COL32(170, 178, 196, 200), "›");
    // Partie simulée.
    dl->AddRectFilled({g.bL, g.y0}, {g.bR, g.y1}, IM_COL32(40, 56, 92, 230), 4.0f * ui.s);
    const char* simTitle = "Temps simulé (clic ou glisser : y aller)";
    dl->AddText({g.bL, o.y}, IM_COL32(200, 206, 220, 220), simTitle);
    // Graduations de la partie simulée.
    struct Tick { double dt; const char* label; };
    const Tick ticks[] = {{-1e9, "−1 Ga"}, {-1e6, "−1 Ma"}, {-1e3, "−1000 ans"}, {0, "aujourd'hui"}, {1e3, "+1000 ans"}, {1e6, "+1 Ma"}, {1e9, "+1 Ga"}, {1e10, "+10 Ga"}};
    const float tickY = g.y1 + px(ui, 3);
    float lastRight = -1e9f;
    for (const Tick& t : ticks) {
        if (t.dt < sim.minYears() - kStartYears - 1 || t.dt > sim.maxYears() - kStartYears + 1) continue;
        const float x = xSim(t.dt);
        dl->AddLine({x, g.y0}, {x, g.y1}, IM_COL32(150, 165, 200, 160));
        const float tw = ImGui::CalcTextSize(t.label).x;
        const float tx = std::clamp(x - tw * 0.5f, g.bL, g.bR - tw);
        if (tx < lastRight + px(ui, 8)) continue;      // pas de nom posé sur le précédent
        dl->AddText({tx, tickY}, t.dt == 0 ? kAccent : IM_COL32(150, 160, 180, 200), t.label);
        lastRight = tx + tw;
    }
    // Époques : un point sur la frise, son nom au survol.
    int hovEpoch = -1;
    const ImVec2 mouse = ImGui::GetIO().MousePos;
    for (int i = 0; i < kEpochCount; ++i) {
        const Epoch& e = kEpochs[i];
        const double dt = e.fromBigBang ? e.years - ageYears : e.years;
        const double bb = e.fromBigBang ? e.years : ageYears + e.years;
        float x;
        if (dt < sim.minYears() - kStartYears) x = xHist(std::max(bb, std::pow(10.0, g.logLo)));
        else if (dt <= sim.maxYears() - kStartYears) x = xSim(dt);
        else continue;
        const ImVec2 c{x, (g.y0 + g.y1) * 0.5f};
        const bool isNear = hov && std::fabs(mouse.x - x) < px(ui, 7) && std::fabs(mouse.y - c.y) < px(ui, 14);
        if (isNear) hovEpoch = i;
        dl->AddCircleFilled(c, (isNear || gBac.epoch == i ? 5.0f : 3.5f) * ui.s, IM_COL32(255, 255, 255, 235));
        dl->AddCircle(c, (isNear || gBac.epoch == i ? 5.0f : 3.5f) * ui.s, IM_COL32(10, 14, 24, 255), 0, 1.2f * ui.s);
    }
    // Premier passage d'Andromède (calculé par le film de la rencontre).
    if (sim.firstPassageGa > 0) {
        const float x = xSim(sim.firstPassageGa * 1e9);
        dl->AddTriangleFilled({x, g.y0 - px(ui, 1)}, {x - px(ui, 4), g.y0 - px(ui, 7)}, {x + px(ui, 4), g.y0 - px(ui, 7)}, kWhatIf);
        if (hov && std::fabs(mouse.x - x) < px(ui, 6) && mouse.y < g.y1) hovEpoch = -2;
    }
    // Date montrée.
    const double now = sim.years - kStartYears;
    const float xn = xSim(now);
    dl->AddLine({xn, g.y0 - px(ui, 4)}, {xn, g.y1 + px(ui, 4)}, kAccent, 2.5f * ui.s);
    // Survol et clic.
    if (hov || active) {
        if (hovEpoch >= 0) {
            const Epoch& e = kEpochs[hovEpoch];
            ImGui::SetTooltip("%s\n%s", e.label, e.fromBigBang ? sinceBigBangText(e.years).c_str() : relativeToToday(kStartYears + e.years).c_str());
        } else if (hovEpoch == -2) {
            ImGui::SetTooltip("Andromède passe au plus près de la Voie lactée\n%s (calculé)", relativeToToday(kStartYears + sim.firstPassageGa * 1e9).c_str());
        } else if (mouse.x >= g.bL - px(ui, 4)) {
            const double dt = std::clamp(symLogInv(g.sLo + (std::clamp(mouse.x, g.bL, g.bR) - g.bL) / (g.bR - g.bL) * (g.sHi - g.sLo)), sim.minYears() - kStartYears, sim.maxYears() - kStartYears);
            ImGui::SetTooltip("%s", relativeToToday(kStartYears + dt).c_str());
        } else if (mouse.x <= g.aR) {
            const double bb = std::pow(10.0, g.logLo + (mouse.x - g.aL) / (g.aR - g.aL) * (g.logHi - g.logLo));
            const double a = hist.aAtSinceBigBang(bb / 1e9);
            ImGui::SetTooltip("%s\nRayonnement : %s K (calculé)\nClic : l'expliquer (la vue 3D ne remonte pas si loin)", sinceBigBangText(bb).c_str(),
                              a > 0 ? frNum(2.7255 / a, 3).c_str() : "?");
        }
    }
    if (ImGui::IsItemClicked()) {
        if (hovEpoch >= 0) {
            const Epoch& e = kEpochs[hovEpoch];
            gBac.epoch = hovEpoch;
            gBac.pickSinceBigBangGa = -1;
            gBac.open = true;
            gBac.tab = 1;
            const double dt = e.fromBigBang ? e.years - ageYears : e.years;
            if (dt >= sim.minYears() - kStartYears && dt <= sim.maxYears() - kStartYears) sim.years = kStartYears + dt;
        } else if (hovEpoch == -2) {
            sim.years = std::clamp(kStartYears + sim.firstPassageGa * 1e9, sim.minYears(), sim.maxYears());
        } else if (mouse.x <= g.aR) {
            gBac.epoch = -1;
            gBac.pickSinceBigBangGa = std::pow(10.0, g.logLo + (mouse.x - g.aL) / (g.aR - g.aL) * (g.logHi - g.logLo)) / 1e9;
            gBac.open = true;
            gBac.tab = 1;
        }
    }
    if (active && mouse.x >= g.bL - px(ui, 4) && hovEpoch == -1) {
        const double dt = symLogInv(g.sLo + (std::clamp(mouse.x, g.bL, g.bR) - g.bL) / (g.bR - g.bL) * (g.sHi - g.sLo));
        sim.years = std::clamp(kStartYears + dt, sim.minYears(), sim.maxYears());
    }
    ImGui::End();
}

}  // namespace
