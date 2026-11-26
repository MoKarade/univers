// Appli PC « Univers » : apparence de l'interface (refonte du 20/11/2026, demande de Marc : « pas du tout user friendly,
// pas du tout belle »). Tout ce qui fixe le look est ici : couleurs, polices, icônes et petits éléments réutilisés
// (bouton-icône, pastille de statut, carte, ligne de valeur). Les autres fichiers de l'interface ne choisissent plus de
// couleur eux-mêmes : ils prennent un jeton d'ici.
//
// Direction : « verre fumé » sur le ciel. Fonds bleu nuit translucides, bord clair très fin, un seul accent chaud (ambre,
// la couleur de la sélection et de « maintenant »), cyan pour les « et si… ». Le statut d'une valeur a sa propre couleur
// (mesuré vert, calculé bleu, modèle violet, supposé orange), toujours la même partout.
#pragma once
#include <imgui.h>

#include <fstream>

#include "interface_outils.h"

namespace univers {

// ---------------------------------------------------------------- jetons de couleur

namespace theme {
constexpr ImU32 kText = IM_COL32(234, 238, 246, 255);
constexpr ImU32 kMuted = IM_COL32(148, 158, 178, 255);
constexpr ImU32 kFaint = IM_COL32(98, 108, 130, 255);
constexpr ImU32 kAccent = IM_COL32(255, 186, 96, 255);      // sélection, « maintenant », bouton actif
constexpr ImU32 kAccentSoft = IM_COL32(255, 186, 96, 46);
constexpr ImU32 kWhatIf = IM_COL32(110, 215, 235, 230);      // « et si… »
constexpr ImU32 kSurface = IM_COL32(11, 15, 26, 214);        // fond des cartes posées sur le ciel
constexpr ImU32 kSurfaceHi = IM_COL32(20, 26, 42, 245);      // menus, fenêtres au premier plan
constexpr ImU32 kLine = IM_COL32(255, 255, 255, 20);         // bord fin
constexpr ImU32 kHover = IM_COL32(255, 255, 255, 16);
constexpr ImU32 kShadow = IM_COL32(0, 0, 0, 90);
// Statuts
constexpr ImU32 kMesure = IM_COL32(96, 212, 156, 255);
constexpr ImU32 kCalcule = IM_COL32(122, 170, 255, 255);
constexpr ImU32 kModele = IM_COL32(186, 146, 255, 255);
constexpr ImU32 kSuppose = IM_COL32(245, 150, 92, 255);
constexpr ImU32 kInconnu = IM_COL32(140, 148, 166, 255);

inline ImVec4 v4(ImU32 c) { return ImGui::ColorConvertU32ToFloat4(c); }
inline ImU32 alpha(ImU32 c, float a) { return (c & 0x00FFFFFFu) | (static_cast<ImU32>(std::clamp(a, 0.0f, 1.0f) * 255.0f + 0.5f) << 24); }

inline ImU32 statutCouleur(ui_outils::Statut s) {
    using ui_outils::Statut;
    switch (s) {
        case Statut::Mesure:
        case Statut::Publie: return kMesure;
        case Statut::Calcule: return kCalcule;
        case Statut::Modele: return kModele;
        case Statut::Suppose: return kSuppose;
        default: return kInconnu;
    }
}
}  // namespace theme

// Anciens noms, encore utilisés par d'autres fichiers (noms posés sur l'image, orbites).
const ImU32 kInkSoft = theme::kMuted, kAccent = theme::kAccent, kOrbit = IM_COL32(120, 150, 210, 105);
const ImU32 kInk = IM_COL32(206, 218, 240, 255);

// ---------------------------------------------------------------- icônes (police Segoe Fluent Icons de Windows 11)

// Points de code de la police d'icônes de Windows (Segoe Fluent Icons, ou Segoe MDL2 Assets sous Windows 10 : mêmes codes).
// Sans cette police, gIcons reste faux et chaque bouton montre un mot à la place.
namespace ico {
constexpr const char* kSearch = "\xEE\x9C\xA1";      // U+E721
constexpr const char* kBack = "\xEE\x9C\xAB";        // U+E72B
constexpr const char* kPlay = "\xEE\x9D\xA8";        // U+E768
constexpr const char* kPause = "\xEE\x9D\xA9";       // U+E769
constexpr const char* kClose = "\xEE\x9C\x91";       // U+E711
constexpr const char* kHelp = "\xEE\xA2\x97";        // U+E897
constexpr const char* kInfo = "\xEE\xA5\x86";        // U+E946
constexpr const char* kCalendar = "\xEE\x9E\x87";    // U+E787
constexpr const char* kLayers = "\xEE\xA0\x9E";      // U+E81E
constexpr const char* kSun = "\xEE\x9C\x86";         // U+E706
constexpr const char* kGlobe = "\xEE\x9D\xB4";       // U+E774
constexpr const char* kLocation = "\xEE\xA0\x9D";    // U+E81D
constexpr const char* kHome = "\xEE\xA0\x8F";        // U+E80F
constexpr const char* kTour = "\xEE\xA3\xB0";        // U+E8F0 (itinéraire)
constexpr const char* kRewind = "\xEE\xAE\x9E";      // U+EB9E
constexpr const char* kForward = "\xEE\xAE\x9D";     // U+EB9D
constexpr const char* kClock = "\xEE\xA0\x9C";       // U+E81C (historique : « maintenant »)
constexpr const char* kChevronDown = "\xEE\x9C\x8D"; // U+E70D
constexpr const char* kEye = "\xEE\xA2\x90";         // U+E890
constexpr const char* kZoomIn = "\xEE\xA2\xA3";      // U+E8A3
}  // namespace ico

// ---------------------------------------------------------------- polices

// Échelle de l'interface : la police est chargée pour le plus grand écran du PC, puis réduite pour une fenêtre plus petite.
inline float gFontMaxScale = 1.0f;
inline bool gIcons = false;                 // police d'icônes trouvée et fusionnée
inline ImFont* gFontSmall = nullptr;        // légendes, statuts, sources
inline ImFont* gFontBold = nullptr;         // titres de section, valeurs mises en avant

// Police de Windows avec les accents et les signes utilisés ; à défaut, la police intégrée (sans accents).
// Elle est chargée à la taille voulue pour la hauteur de l'écran principal (1 à 2,5 fois la taille de base de 1080 lignes).
// Les icônes (Segoe Fluent Icons) sont fusionnées dans chaque taille : « \xEE\x9C\xA1 Chercher » s'écrit d'un seul texte.
inline void loadFonts(ImFont*& normal, ImFont*& big) {
    ImGuiIO& io = ImGui::GetIO();
    static const ImWchar ranges[] = {0x0020, 0x00FF, 0x0100, 0x017F, 0x0391, 0x03C9, 0x2000, 0x206F, 0x2190, 0x2193, 0x2212, 0x2212, 0x2318, 0x2318,
                                     0x2600, 0x2600, 0x25CF, 0x25CF, 0};
    static const ImWchar iconRanges[] = {0xE700, 0xF8FF, 0};
    gFontMaxScale = std::clamp(static_cast<float>(GetSystemMetrics(SM_CYSCREEN)) / 1080.0f, 1.0f, 2.5f);
    const char* regular = "C:\\Windows\\Fonts\\segoeui.ttf";
    const char* semibold = std::ifstream("C:\\Windows\\Fonts\\seguisb.ttf").good() ? "C:\\Windows\\Fonts\\seguisb.ttf" : regular;
    const char* icons = std::ifstream("C:\\Windows\\Fonts\\SegoeIcons.ttf").good() ? "C:\\Windows\\Fonts\\SegoeIcons.ttf"
                        : std::ifstream("C:\\Windows\\Fonts\\segmdl2.ttf").good()  ? "C:\\Windows\\Fonts\\segmdl2.ttf"
                                                                                    : nullptr;
    auto add = [&](const char* path, float size) -> ImFont* {
        ImFont* f = io.Fonts->AddFontFromFileTTF(path, size * gFontMaxScale, nullptr, ranges);
        if (f && icons) {
            ImFontConfig cfg;
            cfg.MergeMode = true;
            cfg.PixelSnapH = true;
            cfg.GlyphOffset = {0, size * gFontMaxScale * 0.12f};      // les icônes s'alignent sur le milieu des lettres
            cfg.GlyphMinAdvanceX = size * gFontMaxScale;              // largeur fixe : les boutons-icônes sont carrés
            io.Fonts->AddFontFromFileTTF(icons, size * gFontMaxScale * 0.92f, &cfg, iconRanges);
        }
        return f;
    };
    if (std::ifstream(regular).good()) {
        normal = add(regular, 17.0f);
        big = add(semibold, 25.0f);
        gFontSmall = add(regular, 14.0f);
        gFontBold = add(semibold, 17.0f);
        gIcons = icons != nullptr;
    }
    if (!normal) {
        gFontMaxScale = 1.0f;
        normal = big = gFontSmall = gFontBold = io.Fonts->AddFontDefault();
        gIcons = false;
    }
}

// Texte d'un bouton-icône : l'icône si la police est là, sinon le mot.
inline std::string iconLabel(const char* icon, const char* word) { return gIcons ? std::string(icon) : std::string(word); }

// ---------------------------------------------------------------- style ImGui

inline void applyStyle() {
    ImGuiStyle& st = ImGui::GetStyle();
    st.WindowRounding = 14;
    st.ChildRounding = 10;
    st.FrameRounding = 9;
    st.GrabRounding = 9;
    st.PopupRounding = 12;
    st.TabRounding = 9;
    st.ScrollbarRounding = 9;
    st.WindowBorderSize = 1;
    st.PopupBorderSize = 1;
    st.FrameBorderSize = 0;
    st.WindowPadding = {16, 14};
    st.FramePadding = {11, 7};
    st.ItemSpacing = {10, 8};
    st.ItemInnerSpacing = {8, 6};
    st.CellPadding = {8, 5};
    st.IndentSpacing = 18;
    st.ScrollbarSize = 10;
    st.GrabMinSize = 12;
    st.SeparatorTextBorderSize = 1;
    st.SeparatorTextPadding = {0, 6};
    st.SelectableTextAlign = {0, 0.5f};
    ImVec4* c = st.Colors;
    using theme::v4;
    c[ImGuiCol_WindowBg] = v4(theme::kSurface);
    c[ImGuiCol_ChildBg] = {0, 0, 0, 0};
    c[ImGuiCol_PopupBg] = v4(theme::kSurfaceHi);
    c[ImGuiCol_Border] = v4(IM_COL32(255, 255, 255, 26));
    c[ImGuiCol_Text] = v4(theme::kText);
    c[ImGuiCol_TextDisabled] = v4(theme::kMuted);
    c[ImGuiCol_FrameBg] = v4(IM_COL32(255, 255, 255, 14));
    c[ImGuiCol_FrameBgHovered] = v4(IM_COL32(255, 255, 255, 26));
    c[ImGuiCol_FrameBgActive] = v4(IM_COL32(255, 255, 255, 34));
    c[ImGuiCol_Button] = v4(IM_COL32(255, 255, 255, 14));
    c[ImGuiCol_ButtonHovered] = v4(IM_COL32(255, 255, 255, 30));
    c[ImGuiCol_ButtonActive] = v4(theme::alpha(theme::kAccent, 0.55f));
    c[ImGuiCol_Header] = v4(IM_COL32(255, 255, 255, 12));
    c[ImGuiCol_HeaderHovered] = v4(IM_COL32(255, 255, 255, 24));
    c[ImGuiCol_HeaderActive] = v4(theme::alpha(theme::kAccent, 0.35f));
    c[ImGuiCol_Separator] = v4(theme::kLine);
    c[ImGuiCol_SeparatorHovered] = v4(theme::kLine);
    c[ImGuiCol_SeparatorActive] = v4(theme::kLine);
    c[ImGuiCol_TitleBg] = v4(theme::kSurfaceHi);
    c[ImGuiCol_TitleBgActive] = v4(theme::kSurfaceHi);
    c[ImGuiCol_TitleBgCollapsed] = v4(theme::kSurfaceHi);
    c[ImGuiCol_SliderGrab] = v4(theme::kAccent);
    c[ImGuiCol_SliderGrabActive] = v4(IM_COL32(255, 214, 160, 255));
    c[ImGuiCol_CheckMark] = v4(theme::kAccent);
    c[ImGuiCol_PlotHistogram] = v4(theme::kAccent);
    c[ImGuiCol_PlotLines] = v4(theme::kAccent);
    c[ImGuiCol_ScrollbarBg] = {0, 0, 0, 0};
    c[ImGuiCol_ScrollbarGrab] = v4(IM_COL32(255, 255, 255, 34));
    c[ImGuiCol_ScrollbarGrabHovered] = v4(IM_COL32(255, 255, 255, 60));
    c[ImGuiCol_ScrollbarGrabActive] = v4(IM_COL32(255, 255, 255, 80));
    c[ImGuiCol_Tab] = v4(IM_COL32(255, 255, 255, 10));
    c[ImGuiCol_TabHovered] = v4(IM_COL32(255, 255, 255, 30));
    c[ImGuiCol_TabSelected] = v4(theme::alpha(theme::kAccent, 0.30f));
    c[ImGuiCol_TextSelectedBg] = v4(theme::alpha(theme::kAccent, 0.35f));
    c[ImGuiCol_NavHighlight] = v4(theme::alpha(theme::kAccent, 0.6f));
    c[ImGuiCol_ModalWindowDimBg] = {0.0f, 0.0f, 0.03f, 0.55f};
    c[ImGuiCol_TableHeaderBg] = v4(IM_COL32(255, 255, 255, 12));
    c[ImGuiCol_TableBorderLight] = v4(theme::kLine);
    c[ImGuiCol_TableBorderStrong] = v4(theme::kLine);
    c[ImGuiCol_TableRowBgAlt] = v4(IM_COL32(255, 255, 255, 6));
}

// ---------------------------------------------------------------- petits éléments

// Bouton carré à icône, avec bulle d'aide. `on` : état actif (fond ambre doux, icône ambre).
inline bool iconButton(const char* id, const char* icon, const char* word, const char* tip, bool on = false, float size = 0) {
    const float sz = size > 0 ? size : ImGui::GetFrameHeight();
    ImGui::PushID(id);
    if (on) {
        ImGui::PushStyleColor(ImGuiCol_Button, theme::v4(theme::kAccentSoft));
        ImGui::PushStyleColor(ImGuiCol_Text, theme::v4(theme::kAccent));
    }
    const std::string label = iconLabel(icon, word);
    const bool hit = gIcons ? ImGui::Button(label.c_str(), {sz, sz}) : ImGui::Button(label.c_str(), {0, sz});
    if (on) ImGui::PopStyleColor(2);
    if (tip && ImGui::IsItemHovered(ImGuiHoveredFlags_DelayShort)) ImGui::SetTooltip("%s", tip);
    ImGui::PopID();
    return hit;
}

// Pastille de texte (statut, nature d'un astre) posée dans la ligne courante.
inline void chip(const char* text, ImU32 col, bool filled = false) {
    ImFont* f = gFontSmall ? gFontSmall : ImGui::GetFont();
    ImGui::PushFont(f);
    const ImVec2 ts = ImGui::CalcTextSize(text);
    const float padX = ImGui::GetFontSize() * 0.55f, padY = ImGui::GetFontSize() * 0.12f;
    const ImVec2 p = ImGui::GetCursorScreenPos();
    const ImVec2 size{ts.x + 2 * padX, ts.y + 2 * padY};
    ImDrawList* dl = ImGui::GetWindowDrawList();
    dl->AddRectFilled(p, {p.x + size.x, p.y + size.y}, theme::alpha(col, filled ? 0.9f : 0.16f), size.y * 0.5f);
    if (!filled) dl->AddRect(p, {p.x + size.x, p.y + size.y}, theme::alpha(col, 0.45f), size.y * 0.5f);
    dl->AddText({p.x + padX, p.y + padY}, filled ? IM_COL32(12, 14, 22, 255) : col, text);
    ImGui::Dummy(size);
    ImGui::PopFont();
}

// Pastille de statut d'une valeur (mesuré, calculé, modèle, supposé…), alignée sur le milieu de la ligne de texte.
inline void statusChip(ui_outils::Statut st) {
    if (st == ui_outils::Statut::Aucun) return;
    const float lift = (ImGui::GetTextLineHeight() - (gFontSmall ? gFontSmall->FontSize * ImGui::GetIO().FontGlobalScale : ImGui::GetTextLineHeight())) * 0.5f;
    ImGui::SetCursorPosY(ImGui::GetCursorPosY() + std::max(0.0f, lift - 1.0f));
    chip(ui_outils::statutMot(st), theme::statutCouleur(st));
}

// Texte secondaire, petite police, qui revient à la ligne.
inline void smallNote(const char* text, ImU32 col = theme::kMuted) {
    ImGui::PushFont(gFontSmall ? gFontSmall : ImGui::GetFont());
    ImGui::PushStyleColor(ImGuiCol_Text, theme::v4(col));
    ImGui::TextWrapped("%s", text);
    ImGui::PopStyleColor();
    ImGui::PopFont();
}

// Titre de petite section, en capitales espacées (« VALEURS », « ORBITE »).
inline void sectionLabel(const char* text) {
    ImGui::PushFont(gFontSmall ? gFontSmall : ImGui::GetFont());
    ImGui::PushStyleColor(ImGuiCol_Text, theme::v4(theme::kFaint));
    ImGui::TextUnformatted(ui_outils::majuscules(text).c_str());
    ImGui::PopStyleColor();
    ImGui::PopFont();
}

// Ligne de valeur d'une fiche : libellé gris, valeur, pastille de statut ; le reste du statut (source, méthode) en petit
// dessous. Aucun texte n'est retiré : seule la mise en page change. Signature d'origine gardée (appelée partout).
inline void row(const char* label, const std::string& value, const char* status, float s) {
    const float avail = ImGui::GetContentRegionAvail().x;
    const float col = std::min(avail * 0.42f, std::max(150.0f * s, ImGui::CalcTextSize(label).x + 14.0f * s));
    const float x0 = ImGui::GetCursorPosX();
    ImGui::PushStyleColor(ImGuiCol_Text, theme::v4(theme::kMuted));
    ImGui::PushTextWrapPos(x0 + col - 10.0f * s);
    ImGui::TextUnformatted(label);
    ImGui::PopTextWrapPos();
    ImGui::PopStyleColor();
    const float labelBottom = ImGui::GetCursorPosY();
    ImGui::SameLine(x0 + col);
    const float vx = ImGui::GetCursorPosX();
    ImGui::PushTextWrapPos(0.0f);
    ImGui::TextUnformatted(value.c_str());
    ImGui::PopTextWrapPos();
    const ui_outils::Statut st = ui_outils::statutDe(status);
    const std::string rest = ui_outils::statutReste(status, st);
    if (st != ui_outils::Statut::Aucun) {
        const float chipW = ImGui::CalcTextSize(ui_outils::statutMot(st)).x * 0.85f + 20.0f * s;
        ImGui::SameLine();
        if (ImGui::GetContentRegionAvail().x < chipW) {      // plus de place sur la ligne : la pastille passe dessous
            ImGui::NewLine();
            ImGui::SetCursorPosX(vx);
        }
        statusChip(st);
    }
    if (!rest.empty()) {
        ImGui::SetCursorPosX(vx);
        ImGui::PushFont(gFontSmall ? gFontSmall : ImGui::GetFont());
        ImGui::PushStyleColor(ImGuiCol_Text, theme::v4(theme::kFaint));
        ImGui::PushTextWrapPos(0.0f);
        ImGui::TextUnformatted(rest.c_str());
        ImGui::PopTextWrapPos();
        ImGui::PopStyleColor();
        ImGui::PopFont();
    }
    if (ImGui::GetCursorPosY() < labelBottom) ImGui::SetCursorPosY(labelBottom);
    ImGui::Dummy({0, 2.0f * s});
}

// Fond d'une fenêtre « carte » : ombre douce sous le verre. À appeler juste après ImGui::Begin.
inline void cardShadow() {
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    const ImVec2 p = ImGui::GetWindowPos(), sz = ImGui::GetWindowSize();
    const float r = ImGui::GetStyle().WindowRounding;
    for (int k = 1; k <= 3; ++k) {
        const float g = 3.0f * k;
        dl->AddRectFilled({p.x - g, p.y - g + 4}, {p.x + sz.x + g, p.y + sz.y + g + 4}, IM_COL32(0, 0, 0, 22), r + g);
    }
}

}  // namespace univers