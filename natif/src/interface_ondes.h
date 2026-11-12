// Ondes gravitationnelles détectées (GWOSC, catalogues officiels de LIGO, Virgo et KAGRA) : une fenêtre ouverte
// depuis « Aller à ». Fichier ondes_gravitationnelles.tsv écrit par pipeline/natif/ondes_gravitationnelles.py
// (même tri que la page : catalogues « confident », le plus récent par événement, p_astro >= 0,5).
// Pas de point dans l'espace : la direction de chaque source n'est connue que par une large tache sur le ciel,
// pas publiée dans ce fichier ; on montre donc ce qui est mesuré : date, masses, distance.
#pragma once
#include "interface_bras.h"

namespace {

struct GravWave {
    std::string name, date, catalog;
    std::string m1, m2, mf, dist, z, pAstro;      // texte prêt à afficher (« 34,6 (32 à 39) »), vide si non publié
    double distMpc = 0;
};

std::vector<GravWave> gGravWaves;

// « v;basse;haute » -> « v (basse à haute) », virgule décimale ; vide si la valeur n'est pas publiée.
std::string gwRange(const std::string& s, double* value = nullptr) {
    if (s.empty()) return "";
    std::vector<std::string> p;
    size_t from = 0;
    for (size_t c; (c = s.find(';', from)) != std::string::npos; from = c + 1) p.push_back(s.substr(from, c - from));
    p.push_back(s.substr(from));
    auto fr = [](std::string t) { std::replace(t.begin(), t.end(), '.', ','); return t; };
    if (value) *value = std::atof(p[0].c_str());
    std::string out = fr(p[0]);
    if (p.size() == 3 && !p[1].empty() && !p[2].empty()) out += " (" + fr(p[1]) + " à " + fr(p[2]) + ")";
    return out;
}

void loadGravWaves(const std::string& path) {
    std::ifstream f(path);
    for (std::string line; std::getline(f, line);) {
        std::vector<std::string> c;
        size_t from = 0;
        for (size_t t; (t = line.find('\t', from)) != std::string::npos; from = t + 1) c.push_back(line.substr(from, t - from));
        c.push_back(line.substr(from));
        if (c.size() < 9) continue;
        GravWave g;
        g.name = c[0];
        g.date = c[1].substr(0, 10);
        g.catalog = c[2];
        g.m1 = gwRange(c[3]);
        g.m2 = gwRange(c[4]);
        g.mf = gwRange(c[5]);
        g.dist = gwRange(c[6], &g.distMpc);
        g.z = gwRange(c[7]);
        g.pAstro = c[8];
        gGravWaves.push_back(g);
    }
}

void drawGravWaves(UiState& ui, float w, float h) {
    ui.gwCount = static_cast<int>(gGravWaves.size());
    if (const char* e = std::getenv("UNIVERS_ECRAN"); e && std::string(e) == "ondes") ui.gwOpen = true;      // contrôle par capture
    if (!ui.gwOpen || gGravWaves.empty()) return;
    ImGui::SetNextWindowSize(ImVec2(std::min(w * 0.8f, px(ui, 980)), std::min(h * 0.7f, px(ui, 620))), ImGuiCond_Appearing);
    ImGui::SetNextWindowPos(ImVec2(w * 0.5f, h * 0.5f), ImGuiCond_Appearing, ImVec2(0.5f, 0.5f));
    if (!ImGui::Begin("Ondes gravitationnelles détectées", &ui.gwOpen, ImGuiWindowFlags_NoSavedSettings)) {
        ImGui::End();
        return;
    }
    ImGui::TextWrapped("%d fusions de trous noirs ou d'étoiles à neutrons, mesurées par LIGO, Virgo et KAGRA (GWOSC, "
                       "catalogues officiels). Masses en masses du Soleil, distance en mégaparsecs (1 Mpc = 3,26 millions "
                       "d'années-lumière) ; entre parenthèses, la fourchette publiée (90 %%).", static_cast<int>(gGravWaves.size()));
    ImGui::TextDisabled("Pas de point dans l'espace : la direction de la plupart des sources n'est connue qu'à des dizaines de degrés près (GW170817 est l'exception : sa galaxie, NGC 4993, a été vue).");
    const ImGuiTableFlags flags = ImGuiTableFlags_RowBg | ImGuiTableFlags_ScrollY | ImGuiTableFlags_BordersInnerH | ImGuiTableFlags_Resizable;
    if (ImGui::BeginTable("ondes", 6, flags)) {
        ImGui::TableSetupScrollFreeze(0, 1);
        for (const char* c : {"Date (UTC)", "Nom", "Masse 1", "Masse 2", "Masse finale", "Distance (Mpc)"}) ImGui::TableSetupColumn(c);
        ImGui::TableHeadersRow();
        ImGuiListClipper clip;
        clip.Begin(static_cast<int>(gGravWaves.size()));
        while (clip.Step())
            for (int i = clip.DisplayStart; i < clip.DisplayEnd; ++i) {
                const GravWave& g = gGravWaves[static_cast<size_t>(i)];
                ImGui::TableNextRow();
                const std::string* cells[] = {&g.date, &g.name, &g.m1, &g.m2, &g.mf, &g.dist};
                for (int k = 0; k < 6; ++k) {
                    ImGui::TableSetColumnIndex(k);
                    ImGui::TextUnformatted(cells[k]->empty() ? "non publiée" : cells[k]->c_str());
                }
                if (ImGui::IsItemHovered()) ImGui::SetTooltip("%s ; catalogue %s ; probabilité d'origine astrophysique %s", g.name.c_str(),
                                                              g.catalog.c_str(), g.pAstro.empty() ? "non publiée" : g.pAstro.c_str());
            }
        ImGui::EndTable();
    }
    ImGui::End();
}

}  // namespace
