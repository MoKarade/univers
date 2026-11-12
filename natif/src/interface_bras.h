// Appli PC « Univers » : les bras spiraux à l'écran (partie de l'interface, voir interface.h).
// Les objets mesurés qui tracent les bras sont dessinés par traceurs_bras.h ; ici : le nom de chaque bras posé au milieu
// de ses masers, la légende des points, la fiche d'un traceur au clic et le bouton « Galaxie de face ».
// Noms des bras : codes donnés à chaque maser par Reid et al. 2019 (ApJ 885, 131). Seuls les codes dont le nom français
// est sûr sont traduits ; les autres gardent le code des auteurs.
#pragma once
#include <algorithm>
#include <cmath>
#include <map>
#include <vector>

#include "interface_methode.h"

namespace {

// Nom d'un bras d'après le code de Reid et al. 2019 ; les deux moitiés d'un même bras (proche, lointaine) sont réunies.
std::string armName(const std::string& code) {
    if (code == "Per") return "Bras de Persée";
    if (code == "SgN" || code == "SgF") return "Bras du Sagittaire";
    if (code == "ScN" || code == "ScF") return "Bras de l'Écu-Centaure";
    if (code == "Nor") return "Bras de la Règle";
    if (code == "Out") return "Bras extérieur";
    if (code == "Loc") return "Bras local";
    if (code == "3kN" || code == "3kF") return "Bras de 3 kpc";
    if (code == "GC") return "Région du centre";
    return code.empty() || code == "???" ? std::string() : "Segment « " + code + " » (Reid et al. 2019)";
}

const ImU32 kArmInk = IM_COL32(255, 150, 190, 235);

// Nom de chaque bras, au milieu de ses masers (au moins 5), à la date montrée.
void drawArmLabels(const Sim& sim, const UiState& ui, const Camera& cam, float w, float h) {
    if (!sim.armTracers || !sim.armTracerWorld || !sim.armTracersShown || sim.dist < 8000.0) return;
    struct Sum {
        Vec3 p{0, 0, 0};
        int n = 0;
    };
    std::map<std::string, Sum> arms;
    const auto& t = *sim.armTracers;
    const auto& world = *sim.armTracerWorld;
    for (size_t i = 0; i < t.size(); ++i) {
        if (!t[i].maser) continue;
        const std::string name = armName(t[i].arm);
        if (name.empty() || name.rfind("Segment", 0) == 0) continue;
        Sum& s = arms[name];
        s.p = {s.p.x + world[i].x, s.p.y + world[i].y, s.p.z + world[i].z};
        ++s.n;
    }
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    // Les bras aux masers les plus nombreux d'abord ; un nom qui en recouvrirait un autre n'est pas écrit.
    std::vector<std::pair<int, std::string>> order;
    for (const auto& [name, s] : arms)
        if (s.n >= 5) order.push_back({-s.n, name});
    std::sort(order.begin(), order.end());
    std::vector<ImVec4> placed;
    for (const auto& [minusN, name] : order) {
        const Sum& s = arms[name];
        double x = 0, y = 0;
        if (!cam.project({s.p.x / s.n, s.p.y / s.n, s.p.z / s.n}, w, h, x, y)) continue;
        const ImVec2 size = ImGui::CalcTextSize(name.c_str());
        const ImVec2 at{static_cast<float>(x) - size.x * 0.5f, static_cast<float>(y) - size.y - 6 * ui.s};
        const ImVec4 box{at.x - 4, at.y - 2, at.x + size.x + 4, at.y + size.y + 2};
        bool overlaps = false;
        for (const ImVec4& r : placed) overlaps |= box.x < r.z && box.z > r.x && box.y < r.w && box.w > r.y;
        if (overlaps) continue;
        placed.push_back(box);
        dl->AddText(ImGui::GetFont(), ImGui::GetFontSize(), {at.x + 1, at.y + 1}, IM_COL32(0, 0, 0, 210), name.c_str());
        dl->AddText(ImGui::GetFont(), ImGui::GetFontSize(), at, kArmInk, name.c_str());
    }
}

// Légende des points, dans le texte du bas de l'écran.
void armLegend(const Sim& sim) {
    if (!sim.armTracers || !sim.armTracersShown || sim.dist < 3000.0) return;
    ImGui::TextColored(ImGui::ColorConvertU32ToFloat4(kArmInk), "Points roses : régions où naissent des étoiles massives, distance mesurée par radio (Reid et al. 2019) ; elles jalonnent les bras.");
    ImGui::TextDisabled("Points bleutés : amas d'étoiles de moins de 100 millions d'années ; gris : amas plus vieux (Hunt & Reffert 2023). Clic : la fiche.");
    if (std::fabs(sim.years - kStartYears) >= 3.0e4)
    {
        char speed[64];
        std::snprintf(speed, sizeof speed, "%.1f ± %.1f", sim.armPatternKmsKpc, sim.armPatternErrorKmsKpc);
        std::string fr = speed;
        std::replace(fr.begin(), fr.end(), '.', ',');
        ImGui::TextDisabled("Leur dessin d'aujourd'hui tourne d'un bloc à la vitesse mesurée des bras (%s km/s par kpc, Dias et al. 2019) : calculé.", fr.c_str());
    }
    if (sim.loneGalaxyShare > 0)
        ImGui::TextDisabled("Voie lactée entière calculée : bras calculés, position non prévisible (le dessin mesuré ne se prolonge pas au-delà de 200 à 400 millions d'années).");
}

// Clic sur l'image, hors d'un astre nommé : le traceur le plus proche à moins de 9 pixels (les masers d'abord).
void clickArmTracer(const Sim& sim, UiState& ui, const Camera& cam, float w, float h, int hovered) {
    if (hovered >= 0 || ImGui::GetIO().WantCaptureMouse || !sim.armTracers || !sim.armTracerWorld || !sim.armTracersShown) return;
    const ImVec2 drag = ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f);
    if (!ImGui::IsMouseReleased(ImGuiMouseButton_Left) || drag.x != 0 || drag.y != 0) return;
    const ImVec2 m = ImGui::GetIO().MousePos;
    const auto& t = *sim.armTracers;
    const auto& world = *sim.armTracerWorld;
    int best = -1;
    double bestD = 9.0 * ui.s * 9.0 * ui.s;
    for (size_t i = 0; i < t.size(); ++i) {
        double x = 0, y = 0;
        if (!cam.project(world[i], w, h, x, y)) continue;
        const double d = ((x - m.x) * (x - m.x) + (y - m.y) * (y - m.y)) * (t[i].maser ? 0.5 : 1.0);
        if (d < bestD) {
            bestD = d;
            best = static_cast<int>(i);
        }
    }
    ui.armSel = best;
}

// Fiche du traceur choisi, à gauche, et un cercle autour de lui.
void drawArmCard(const Sim& sim, UiState& ui, const Camera& cam, float w, float h, ImGuiWindowFlags fixed) {
    if (ui.armSel < 0 || !sim.armTracers || !sim.armTracerWorld || !sim.armTracersShown || static_cast<size_t>(ui.armSel) >= sim.armTracers->size()) {
        ui.armSel = -1;
        return;
    }
    const ArmTracer& t = (*sim.armTracers)[static_cast<size_t>(ui.armSel)];
    double x = 0, y = 0;
    if (cam.project((*sim.armTracerWorld)[static_cast<size_t>(ui.armSel)], w, h, x, y))
        ImGui::GetBackgroundDrawList()->AddCircle({static_cast<float>(x), static_cast<float>(y)}, 9 * ui.s, kArmInk, 32, 1.5f * ui.s);
    ImGui::SetNextWindowPos({px(ui, 16), h * 0.30f});
    ImGui::Begin("traceur", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(t.name.c_str());
    ImGui::PopFont();
    const double dist = std::sqrt(dot(t.pos, t.pos));
    row("Nature", t.maser ? "région où naissent des étoiles massives (maser)" : "amas d'étoiles", "", ui.s);
    if (t.maser && !armName(t.arm).empty()) row("Bras", armName(t.arm), "attribué par les auteurs", ui.s);
    row("Distance au Soleil", frDistance(dist) + " (à " + frNum(t.distanceError * 100.0, 0) + " % près)", "mesuré", ui.s);
    if (!t.maser) row("Âge", t.ageMyr >= 1000.0 ? frNum(t.ageMyr / 1000.0, 2) + " milliards d'années" : frNum(t.ageMyr, 0) + " millions d'années", "mesuré", ui.s);
    ImGui::TextDisabled(t.maser ? "Source : Reid et al. 2019 (parallaxe mesurée par un réseau de radiotélescopes)." : "Source : Hunt & Reffert 2023 (amas ouverts de Gaia DR3).");
    if (std::fabs(sim.years - kStartYears) >= 3.0e4) ImGui::TextDisabled("Place à cette date : calculée (dessin des bras tourné d'un bloc).");
    if (ImGui::Button("Fermer##traceur")) ui.armSel = -1;
    ImGui::End();
}

// Bouton « Galaxie de face » de la barre du haut : le centre de la Voie lactée vu du pôle nord de la Galaxie.
void faceOnButton(Sim& sim, UiState& ui) {
    int centre = -1;
    for (int i = 0; i < static_cast<int>(sim.bodies.size()); ++i)
        if (sim.bodies[static_cast<size_t>(i)].name == "Centre de la Voie lactée") centre = i;
    if (centre < 0 || !sim.visible(centre)) return;
    if (ImGui::Button("Galaxie de face")) {      // sur une deuxième ligne : la première touche déjà la barre du temps
        goToBody(sim, ui, centre, 110000.0);
        sim.yaw = 180.0 * kPi / 180.0;      // pôle nord de la Galaxie : longitude écliptique 180,0°, latitude 29,8°
        sim.pitch = 29.8 * kPi / 180.0;
        sim.touched = true;
    }
    if (ImGui::IsItemHovered()) ImGui::SetTooltip("Voir la Voie lactée d'en haut, avec ses bras mesurés");
}

// Bascule globale « 100 % mesuré » / « meilleur rendu » (choix de Marc, 12/11/2026), touche F4.
void viewModeButton(Sim& sim) {
    if (ImGui::Button(sim.bestLook ? "Vue : meilleur rendu" : "Vue : 100 % mesuré")) sim.bestLook = !sim.bestLook;
    if (ImGui::IsItemHovered())
        ImGui::SetTooltip(sim.bestLook ? "Meilleur rendu : quelques corrections NON mesurées sont permises pour une plus belle image ;\nchacune est dite à l'écran. Clic ou F4 : revenir à 100 %% mesuré."
                                       : "100 %% mesuré : seulement ce qui a été mesuré, et ce qui en est calculé.\nClic ou F4 : meilleur rendu (quelques corrections non mesurées, signalées).");
    if (!ImGui::GetIO().WantTextInput && ImGui::IsKeyPressed(ImGuiKey_F4, false)) sim.bestLook = !sim.bestLook;
}

}  // namespace
