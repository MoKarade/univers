// Appli PC « Univers » : comment est obtenu ce qui est à l'écran, et où en sont les calculs de fond (partie de
// l'interface, voir interface.h).
//  - Demande de Marc (12/11/2026) : « je veux voir quand ça montre ce qui a été calculé en amont sur carte graphique ou
//    approximation ». Une ligne permanente en haut à droite ; le tableau famille par famille au clic. Le contenu vient de
//    sim.calcStates, rempli à chaque image par fenetre.cpp : rien n'est recalculé ici.
//  - « Je veux un indicateur qui montre où ça en est » : les calculs de fond du PC (sim.tasks, avancement.h), une ligne
//    avec une barre tant qu'une tâche tourne ; le détail au clic. Une durée n'est écrite que si elle est mesurée.
#pragma once
#include "interface_lumiere.h"

namespace {

const char* howWord(CalcMode m) {
    switch (m) {
        case CalcMode::Measured: return "mesuré";
        case CalcMode::Exact: return "calculé";
        case CalcMode::Precomputed: return "précalculé";
        case CalcMode::Approx: return "approximation";
        default: return "non montré";
    }
}

ImVec4 howColor(CalcMode m) {
    switch (m) {
        case CalcMode::Measured: return {0.55f, 0.82f, 0.59f, 1.0f};
        case CalcMode::Exact: return {0.55f, 0.71f, 0.94f, 1.0f};
        case CalcMode::Precomputed: return {0.47f, 0.78f, 0.78f, 1.0f};
        case CalcMode::Approx: return {1.0f, 0.77f, 0.43f, 1.0f};
        default: return {0.59f, 0.63f, 0.70f, 1.0f};
    }
}

// La ligne permanente : les approximations et les calculs en retard s'il y en a.
std::string howSummary(const Sim& sim, bool& warn) {
    std::string approx;
    long lag = 0;
    for (const CalcState& c : sim.calcStates) {
        if (c.mode == CalcMode::Approx) approx += (approx.empty() ? "" : ", ") + c.family;
        lag = std::max(lag, c.mode == CalcMode::Hidden ? 0L : c.lagSteps);
    }
    warn = !approx.empty() || lag > 0;
    if (!approx.empty()) return "Comment c'est obtenu : approximation pour " + approx;
    if (lag > 0) return "Comment c'est obtenu : calcul exact en retard de " + frInt(static_cast<double>(lag)) + " millions d'années";
    return "Comment c'est obtenu : mesuré, lu ou calculé (détail au clic)";
}

// Durée en mots : « 40 s », « 3 min », « 1 h 20 », « 2,5 j ».
std::string frDuration(double s) {
    if (s < 60) return frInt(std::max(1.0, s)) + " s";
    if (s < 3600) return frInt(s / 60) + " min";
    if (s < 86400) {
        const int h = static_cast<int>(s / 3600), m = static_cast<int>((s - h * 3600.0) / 60);
        return std::to_string(h) + " h " + (m < 10 ? "0" : "") + std::to_string(m);
    }
    return frNum(s / 86400, 2) + " j";
}

int runningTasks(const Sim& sim) {
    int n = 0;
    for (const TaskProgress& t : sim.tasks) n += !t.finished;
    return n;
}

void howTable(const Sim& sim) {
    ImGui::TextDisabled("À la date et à l'échelle affichées, pour chaque famille d'objets :");
    if (!ImGui::BeginTable("methode", 3, ImGuiTableFlags_RowBg | ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_NoHostExtendX)) return;
    for (const CalcState& c : sim.calcStates) {
        ImGui::TableNextRow();
        ImGui::TableNextColumn();
        ImGui::TextUnformatted(c.family.c_str());
        ImGui::TableNextColumn();
        ImGui::TextColored(howColor(c.mode), "%s", howWord(c.mode));
        ImGui::TableNextColumn();
        if (c.lagSteps > 0 && c.mode != CalcMode::Hidden)
            ImGui::TextDisabled("%s ; calcul exact en retard de %s millions d'années", c.detail.c_str(), frInt(static_cast<double>(c.lagSteps)).c_str());
        else ImGui::TextDisabled("%s", c.detail.c_str());
    }
    ImGui::EndTable();
    ImGui::Spacing();
    ImGui::TextDisabled("mesuré : lu dans un catalogue d'observations   •   précalculé : calculé d'avance (NASA, JPL, ou ici) puis lu");
    ImGui::TextDisabled("calculé : calculé ici pendant que tu regardes   •   approximation : méthode approchée, plus rapide");
}

void tasksTable(const Sim& sim) {
    if (sim.tasks.empty()) {
        ImGui::TextDisabled("Aucun calcul de fond en cours sur le PC.");
        return;
    }
    if (!ImGui::BeginTable("calculs", 3, ImGuiTableFlags_RowBg | ImGuiTableFlags_SizingFixedFit | ImGuiTableFlags_NoHostExtendX)) return;
    for (const TaskProgress& t : sim.tasks) {
        ImGui::TableNextRow();
        ImGui::TableNextColumn();
        ImGui::TextUnformatted(t.name.c_str());
        if (!t.detail.empty()) ImGui::TextDisabled("%s", t.detail.c_str());
        ImGui::TableNextColumn();
        const std::string over = t.total > 0 ? frInt(t.percent) + " %" : std::string("—");
        ImGui::ProgressBar(t.total > 0 ? static_cast<float>(t.percent / 100.0) : 0.0f, {ImGui::GetFontSize() * 9, 0}, over.c_str());
        ImGui::TableNextColumn();
        std::string where = t.total > 0 ? frInt(t.done) + " sur " + frInt(t.total) + (t.unit.empty() ? "" : " " + t.unit) : t.state;
        if (t.finished) where += " ; terminé";
        else if (t.stale) where += " ; plus de nouvelles depuis plus de 3 minutes";
        else if (t.remainingSeconds >= 0) where += " ; encore environ " + frDuration(t.remainingSeconds) + " (estimation au rythme mesuré)";
        else where += " ; durée restante inconnue";
        if (t.stale) ImGui::TextColored(howColor(CalcMode::Approx), "%s", where.c_str());
        else ImGui::TextDisabled("%s", where.c_str());
    }
    ImGui::EndTable();
}

void drawHow(const Sim& sim, UiState& ui, float w, ImGuiWindowFlags fixed) {
    if (sim.calcStates.empty() && sim.tasks.empty()) return;
    if (!ui.details && runningTasks(sim) == 0 && !ui.howOpen && !ui.tasksOpen) return;      // minimaliste : rien à montrer
    // Sous la complétude, en haut à droite.
    const float y = ui.completenessBottom + px(ui, 8);
    ImGui::SetNextWindowPos({w - px(ui, 16), y}, 0, {1, 0});
    ImGui::SetNextWindowSizeConstraints({ui.completenessW, 0}, {std::max(ui.completenessW, px(ui, 200)), FLT_MAX});      // même largeur que la carte du dessus
    ImGui::Begin("methode-ligne", nullptr, fixed);
    cardShadow();
    if (!sim.calcStates.empty() && ui.details) {      // minimaliste : « comment c'est obtenu » seulement avec les détails
        bool warn = false;
        const std::string line = howSummary(sim, warn) + " (clic : détail)";
        if (warn) ImGui::PushStyleColor(ImGuiCol_Text, howColor(CalcMode::Approx));
        if (ImGui::Selectable(line.c_str(), ui.howOpen)) ui.howOpen = !ui.howOpen;
        if (warn) ImGui::PopStyleColor();
    }
    // Calculs de fond : une ligne et la barre de la tâche la moins avancée, tant qu'une tâche tourne.
    const int running = runningTasks(sim);
    if (running > 0) {
        const TaskProgress* slow = nullptr;
        for (const TaskProgress& t : sim.tasks)
            if (!t.finished && (!slow || t.percent < slow->percent)) slow = &t;
        const std::string line = ui.details ? "Calculs de fond en cours : " + std::to_string(running) + " (clic : où ça en est)"
                                            : "Calculs en cours : " + std::to_string(running);
        if (ImGui::Selectable(line.c_str(), ui.tasksOpen)) ui.tasksOpen = !ui.tasksOpen;
        if (slow && slow->total > 0) {
            const std::string over = slow->name + " : " + frInt(slow->percent) + " %";
            ImGui::ProgressBar(static_cast<float>(slow->percent / 100.0), {-1.0f, ui.details ? ImGui::GetFontSize() * 0.9f : px(ui, 6)}, ui.details ? over.c_str() : "");
            if (!ui.details && ImGui::IsItemHovered()) ImGui::SetTooltip("%s", over.c_str());
        }
    }
    ui.completenessBottom = ImGui::GetWindowPos().y + ImGui::GetWindowHeight();      // la fiche se place en dessous
    ui.howW = ImGui::GetWindowWidth();
    ImGui::End();

    const ImGuiWindowFlags panel = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings;
    if (ui.howOpen) {
        ImGui::SetNextWindowPos({w * 0.5f, ImGui::GetIO().DisplaySize.y * 0.5f}, 0, {0.5f, 0.5f});
        ImGui::SetNextWindowBgAlpha(0.97f);
        ImGui::SetNextWindowFocus();
        ImGui::Begin("Comment c'est obtenu", &ui.howOpen, panel);
        howTable(sim);
        if (ImGui::Button("Fermer")) ui.howOpen = false;
        ImGui::End();
    }
    if (ui.tasksOpen) {
        ImGui::SetNextWindowPos({w * 0.5f, ImGui::GetIO().DisplaySize.y * 0.3f}, 0, {0.5f, 0.5f});
        ImGui::SetNextWindowBgAlpha(0.97f);
        ImGui::Begin("Calculs de fond du PC", &ui.tasksOpen, panel);
        ImGui::TextDisabled("Relu toutes les 2 secondes. Une durée restante n'est donnée que si le rythme est mesuré.");
        tasksTable(sim);
        if (ImGui::Button("Fermer##calculs")) ui.tasksOpen = false;
        ImGui::End();
    }
}

}  // namespace
