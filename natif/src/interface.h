// Appli PC « Univers » : ce qui est écrit et cliquable à l'écran (Dear ImGui), habillé aux couleurs de la page.
// Tout ce qu'il faut savoir pour s'en servir est écrit à l'écran : rien n'est à lire ailleurs.
#pragma once
#include <imgui.h>

#include "simulation.h"

namespace {

const ImU32 kInkSoft = IM_COL32(150, 160, 178, 255), kAccent = IM_COL32(255, 196, 110, 255), kOrbit = IM_COL32(110, 140, 200, 110);

void applyStyle() {
    ImGuiStyle& st = ImGui::GetStyle();
    st.WindowRounding = 10;
    st.FrameRounding = 7;
    st.GrabRounding = 7;
    st.PopupRounding = 8;
    st.WindowBorderSize = 1;
    st.WindowPadding = {14, 12};
    st.FramePadding = {10, 6};
    st.ItemSpacing = {8, 7};
    ImVec4* c = st.Colors;
    c[ImGuiCol_WindowBg] = {0.035f, 0.045f, 0.075f, 0.86f};
    c[ImGuiCol_PopupBg] = {0.05f, 0.065f, 0.11f, 0.97f};
    c[ImGuiCol_Border] = {0.30f, 0.36f, 0.50f, 0.35f};
    c[ImGuiCol_Text] = {0.91f, 0.93f, 0.96f, 1.0f};
    c[ImGuiCol_TextDisabled] = {0.59f, 0.63f, 0.70f, 1.0f};
    c[ImGuiCol_FrameBg] = {0.10f, 0.13f, 0.20f, 0.9f};
    c[ImGuiCol_FrameBgHovered] = {0.16f, 0.20f, 0.30f, 1.0f};
    c[ImGuiCol_FrameBgActive] = {0.20f, 0.25f, 0.36f, 1.0f};
    c[ImGuiCol_Button] = {0.11f, 0.14f, 0.22f, 0.95f};
    c[ImGuiCol_ButtonHovered] = {0.20f, 0.25f, 0.38f, 1.0f};
    c[ImGuiCol_ButtonActive] = {0.80f, 0.58f, 0.25f, 1.0f};
    c[ImGuiCol_Header] = {0.16f, 0.20f, 0.30f, 0.9f};
    c[ImGuiCol_HeaderHovered] = {0.22f, 0.28f, 0.42f, 1.0f};
    c[ImGuiCol_HeaderActive] = {0.80f, 0.58f, 0.25f, 1.0f};
    c[ImGuiCol_Separator] = {0.30f, 0.36f, 0.50f, 0.35f};
}

// Police de Windows avec les accents et les signes utilisés ; à défaut, la police intégrée (sans accents).
void loadFonts(ImFont*& normal, ImFont*& big) {
    ImGuiIO& io = ImGui::GetIO();
    static const ImWchar ranges[] = {0x0020, 0x00FF, 0x2010, 0x2027, 0x2212, 0x2212, 0};
    const char* path = "C:\\Windows\\Fonts\\segoeui.ttf";
    if (std::ifstream(path).good()) {
        normal = io.Fonts->AddFontFromFileTTF(path, 18.0f, nullptr, ranges);
        big = io.Fonts->AddFontFromFileTTF(path, 26.0f, nullptr, ranges);
    }
    if (!normal) normal = big = io.Fonts->AddFontDefault();
}

bool containsNoCase(const std::string& hay, const char* needle) {
    if (!needle[0]) return true;
    auto low = [](unsigned char c) { return static_cast<char>(std::tolower(c)); };
    std::string h(hay.size(), ' '), n(needle);
    std::transform(hay.begin(), hay.end(), h.begin(), low);
    std::transform(n.begin(), n.end(), n.begin(), low);
    return h.find(n) != std::string::npos;
}

void row(const char* label, const std::string& value, const char* status) {
    ImGui::TextDisabled("%s", label);
    ImGui::SameLine(190);
    ImGui::TextUnformatted(value.c_str());
    if (status[0]) {
        ImGui::SameLine();
        ImGui::TextDisabled("(%s)", status);
    }
}

// Projection sans rejet des points hors de l'écran (pour les tracés) ; false si le point est derrière la caméra.
bool projectLoose(const Camera& cam, Vec3 p, float w, float h, ImVec2& out) {
    const Vec3 d = p - cam.pos;
    const double z = dot(d, cam.fwd);
    if (z <= 0) return false;
    out = {static_cast<float>((dot(d, cam.right) / (z * cam.tanHalf * cam.aspect) * 0.5 + 0.5) * w),
           static_cast<float>((-dot(d, cam.up) / (z * cam.tanHalf) * 0.5 + 0.5) * h)};
    return std::fabs(out.x) < 1.0e5f && std::fabs(out.y) < 1.0e5f;
}

// Rayon apparent du disque d'un astre, en pixels (0 pour une étoile lointaine).
double discRadiusPx(const Sim& sim, const Camera& cam, int i, float h) {
    const Vec3 d = sim.position(i) - cam.pos;
    const double dist = std::max(std::sqrt(dot(d, d)), 1e-30);
    return (sim.bodies[static_cast<size_t>(i)].radiusKm / kLyInKm) / dist / (2.0 * cam.tanHalf / h);
}

// Orbites : la trajectoire réelle lue dans les éphémérides sur un tour centré sur la date courante.
struct OrbitCache {
    static constexpr int kPoints = 240;
    struct Track {
        double atYears = 1e300;
        bool valid = false;
        std::vector<Vec3> pts;      // positions relatives à l'astre parent (Soleil, ou Terre pour la Lune)
    };
    std::vector<Track> tracks;

    void update(const Sim& sim) {
        tracks.resize(sim.bodies.size());
        for (size_t i = 0; i < sim.bodies.size(); ++i) {
            const Body& b = sim.bodies[i];
            if (b.kind != Kind::Planet) continue;
            Track& t = tracks[i];
            if (std::fabs(sim.years - t.atYears) < b.periodYears / 240.0) continue;      // encore bon à l'écran
            t.atYears = sim.years;
            t.pts.resize(kPoints + 1);
            t.valid = true;
            for (int k = 0; k <= kPoints && t.valid; ++k) {
                const double at = sim.years + (static_cast<double>(k) / kPoints - 0.5) * b.periodYears;
                Vec3 p, parent{0, 0, 0};
                t.valid = sim.planetAt(b.naif, at, p) && (b.parent <= 0 || sim.planetAt(sim.bodies[static_cast<size_t>(b.parent)].naif, at, parent));
                t.pts[static_cast<size_t>(k)] = p - parent;
            }
        }
    }
};

struct UiState {
    char search[64] = "";
    ImFont* normal = nullptr;
    ImFont* big = nullptr;
    OrbitCache orbits;
};

// Dessine toute l'interface pour cette image. Rend le numéro de l'astre dont le nom a été cliqué, ou -1.
int drawInterface(Sim& sim, UiState& ui, const Camera& cam, float w, float h) {
    int clicked = -1;
    const ImGuiWindowFlags fixed = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoTitleBar |
                                   ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings;
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    const int count = static_cast<int>(sim.bodies.size());

    // Orbites des planètes et de la Lune.
    if (sim.ephemValid) {
        ui.orbits.update(sim);
        for (int i = 0; i < count; ++i) {
            const Body& b = sim.bodies[static_cast<size_t>(i)];
            if (b.kind != Kind::Planet || !ui.orbits.tracks[static_cast<size_t>(i)].valid) continue;
            const Vec3 parent = b.parent > 0 ? sim.position(b.parent) : Vec3{0, 0, 0};
            const auto& pts = ui.orbits.tracks[static_cast<size_t>(i)].pts;
            // Taille apparente de l'orbite : ni un point, ni un trait qui traverse tout l'écran.
            const Vec3 toParent = parent - cam.pos;
            const double size = std::sqrt(dot(pts[0], pts[0])) / std::max(std::sqrt(dot(toParent, toParent)), 1e-30) * h;
            if (size < 6 || size > 60.0 * h) continue;
            if (discRadiusPx(sim, cam, i, h) > 14) continue;      // l'astre est vu de près : son orbite ne lui passe pas sur le visage
            ImVec2 prev;
            bool hasPrev = false;
            for (const Vec3& rel : pts) {
                ImVec2 at;
                const bool ok = projectLoose(cam, {parent.x + rel.x, parent.y + rel.y, parent.z + rel.z}, w, h, at);
                if (ok && hasPrev) dl->AddLine(prev, at, i == sim.focus ? IM_COL32(255, 196, 110, 150) : kOrbit, 1.2f);
                prev = at;
                hasPrev = ok;
            }
        }
    }

    // Noms des astres, posés sur l'image ; un clic sur un nom le fait suivre.
    const ImVec2 mouse = ImGui::GetIO().MousePos;
    const ImVec2 drag = ImGui::GetMouseDragDelta(ImGuiMouseButton_Left, 4.0f);
    const bool click = ImGui::IsMouseReleased(ImGuiMouseButton_Left) && !ImGui::GetIO().WantCaptureMouse && drag.x == 0 && drag.y == 0;
    const double boostMag = 2.5 * std::log10(sim.brightnessBoost());
    std::vector<ImVec4> placed;      // rectangles des noms déjà posés : un nom ne recouvre jamais un autre
    for (int pass = -1; pass < count; ++pass) {      // l'astre suivi d'abord : il garde toujours son nom, les autres s'effacent devant lui
        const int i = pass < 0 ? sim.focus : pass;
        if (pass >= 0 && i == sim.focus) continue;
        if (!sim.visible(i)) continue;
        const Body& b = sim.bodies[static_cast<size_t>(i)];
        double px = 0, py = 0;
        if (!cam.project(sim.position(i), w, h, px, py)) continue;
        const bool isFocus = i == sim.focus;
        if (isFocus && discRadiusPx(sim, cam, i, h) > 14) continue;      // vu de près : la fiche porte déjà son nom
        if (!isFocus) {
            if (b.kind == Kind::Star && (sim.dist > 3000.0 || sim.apparentMag(i, cam.pos) - boostMag > 4.5)) continue;      // trop pâle d'ici, ou vue trop large
            if (b.kind == Kind::Planet && sim.dist > 0.05) continue;
            if (b.kind == Kind::Galaxy && (sim.dist < 2.0e4 || sim.dist > 3.0e9 || (b.priority > 1 && sim.dist < 1.5e6))) continue;
            if (b.kind == Kind::Planet) {      // un nom par planète seulement quand elle se détache de son astre parent
                double qx = 0, qy = 0;
                const bool parentOn = cam.project(sim.position(std::max(b.parent, 0)), w, h, qx, qy);
                if (parentOn && std::hypot(px - qx, py - qy) < 22) continue;
            }
        }
        const char* name = b.name.c_str();
        const ImVec2 size = ImGui::CalcTextSize(name);
        const ImVec2 at{static_cast<float>(px) + 10, static_cast<float>(py) - size.y * 0.5f};
        const ImVec4 box{at.x - 14, at.y - 3, at.x + size.x + 6, at.y + size.y + 3};
        if (!isFocus) {
            bool overlaps = false;
            for (const ImVec4& r : placed) overlaps |= box.x < r.z && box.z > r.x && box.y < r.w && box.w > r.y;
            if (overlaps) continue;
        }
        placed.push_back(box);
        const bool hover = mouse.x >= at.x - 14 && mouse.x <= at.x + size.x + 4 && mouse.y >= at.y - 4 && mouse.y <= at.y + size.y + 4;
        if (isFocus) dl->AddCircle({static_cast<float>(px), static_cast<float>(py)}, 9, kAccent, 32, 1.5f);
        dl->AddText({at.x + 1, at.y + 1}, IM_COL32(0, 0, 0, 200), name);
        dl->AddText(at, isFocus || hover ? kAccent : (b.kind == Kind::Star ? kInkSoft : IM_COL32(200, 214, 240, 255)), name);
        if (hover && click) clicked = i;
    }

    // En haut à gauche : chercher un astre.
    ImGui::SetNextWindowPos({16, 16});
    ImGui::Begin("chercher", nullptr, fixed);
    ImGui::SetNextItemWidth(260);
    ImGui::InputTextWithHint("##q", "Chercher un astre (ex. Jupiter)", ui.search, sizeof(ui.search));
    if (ui.search[0]) {
        int shown = 0;
        for (int i = 0; i < count && shown < 8; ++i) {
            if (!sim.visible(i) || !containsNoCase(sim.bodies[static_cast<size_t>(i)].name, ui.search)) continue;
            ++shown;
            if (ImGui::Selectable(sim.bodies[static_cast<size_t>(i)].name.c_str(), i == sim.focus, 0, {260, 0})) {
                clicked = i;
                ui.search[0] = 0;
            }
        }
        if (!shown) ImGui::TextDisabled("Aucun astre nommé ne correspond.");
    }
    ImGui::End();

    // En haut au centre : la date et le temps.
    ImGui::SetNextWindowPos({w * 0.5f, 16}, 0, {0.5f, 0});
    ImGui::Begin("temps", nullptr, fixed);
    ImGui::PushFont(ui.big);
    const std::string date = frDate(sim.years, kRates[sim.rate].yearsPerSecond < 0.02);
    ImGui::SetCursorPosX(std::max(14.0f, (ImGui::GetWindowSize().x - ImGui::CalcTextSize(date.c_str()).x) * 0.5f));
    ImGui::TextUnformatted(date.c_str());
    ImGui::PopFont();
    if (ImGui::Button(sim.paused ? "Reprendre" : "Pause")) sim.paused = !sim.paused;
    ImGui::SameLine();
    if (ImGui::Button(sim.backward ? "Le temps recule" : "Le temps avance")) sim.backward = !sim.backward;
    ImGui::SameLine();
    ImGui::SetNextItemWidth(230);
    if (ImGui::BeginCombo("##vitesse", kRates[sim.rate].label)) {
        for (int i = 0; i < kRateCount; ++i)
            if (ImGui::Selectable(kRates[i].label, i == sim.rate)) sim.rate = i;
        ImGui::EndCombo();
    }
    ImGui::SameLine();
    if (ImGui::Button("Aujourd'hui")) sim.years = kStartYears;
    if (!sim.spk) ImGui::TextDisabled("Planètes absentes : le fichier d'éphémérides de la NASA (de440.bsp) manque à côté du programme.");
    else if (!sim.ephemValid) ImGui::TextDisabled("Planètes masquées : les éphémérides de la NASA vont de 1550 à 2650. Au-delà : position inconnue pour l'instant.");
    if (std::fabs(sim.years - kStartYears) >= kLinearLimitYears * 0.999)
        ImGui::TextDisabled("Limite : au-delà de 3 millions d'années, les étoiles ne vont plus en ligne droite (à venir).");
    ImGui::End();

    // À droite : la fiche de l'astre suivi.
    const int f = sim.focus;
    const Body& fb = sim.bodies[static_cast<size_t>(f)];
    const Vec3 p = sim.position(f);
    const double dSun = std::sqrt(dot(p, p));
    const bool today = std::fabs(sim.years - kStartYears) < 1.0;
    ImGui::SetNextWindowPos({w - 16, 124}, 0, {1, 0});      // sous la barre du temps : les deux ne se recouvrent jamais
    ImGui::Begin("fiche", nullptr, fixed);
    ImGui::PushFont(ui.big);
    ImGui::TextUnformatted(fb.name.c_str());
    ImGui::PopFont();
    ImGui::Separator();
    row("Nature", fb.natureLabel(), "");
    if (fb.kind == Kind::Planet) {
        row("Distance au Soleil", frDistance(dSun), "éphémérides NASA");
        for (int i = 0; i < count; ++i)
            if (sim.bodies[static_cast<size_t>(i)].naif == eph::kEarth && i != f) {
                const Vec3 d = p - sim.position(i);
                row("Distance à la Terre", frDistance(std::sqrt(dot(d, d))), "éphémérides NASA");
            }
        row("Durée d'un tour", fb.periodYears >= 1 ? frNum(fb.periodYears) + " ans" : frNum(fb.periodYears * 365.25) + " jours", "mesuré");
        row("Rayon", frInt(fb.radiusKm) + " km", "mesuré");
    } else if (fb.kind == Kind::Star) {
        // Aujourd'hui la distance est une mesure ; à une autre date, c'est la mesure prolongée en ligne droite.
        row("Distance au Soleil", frDistance(dSun), today ? "mesuré" : "calculé : mouvement mesuré, prolongé en ligne droite");
        row("Éclat vu de la Terre", "magnitude " + frNum(sim.apparentMag(f, {0, 0, 0})), "calculé");
        row("Vitesse", frNum(sim.speedKms(f)) + " km/s par rapport au Soleil", "mesuré");
    } else if (fb.kind == Kind::Galaxy) {
        row("Distance au Soleil", frDistance(dSun), "mesuré");
        ImGui::TextDisabled("Sa forme et sa photo ne sont pas encore dessinées ici.");
    } else {
        row("Rayon", frInt(fb.radiusKm) + " km", "mesuré");
    }
    if (fb.kind == Kind::Sun || fb.kind == Kind::Star)
        row("Température", frInt(4600.0 * (1.0 / (0.92 * fb.bv + 1.7) + 1.0 / (0.92 * fb.bv + 0.62))) + " K en surface", "calculé d'après la couleur");
    if (fb.kind != Kind::Galaxy) row("Vue d'ici", "magnitude " + frNum(sim.apparentMag(f, cam.pos)), "calculé");
    ImGui::Separator();
    if (fb.kind == Kind::Planet) ImGui::TextDisabled("Position : éphémérides JPL DE440 de la NASA, lues telles quelles.");
    else if (fb.kind == Kind::Galaxy) ImGui::TextDisabled("Sources : Karachentsev et al. 2013 ; McConnachie 2012.");
    else ImGui::TextDisabled("Sources : catalogues Hipparcos (HYG) et Gaia DR3.");
    if (f != 0 && ImGui::Button("Revenir au Soleil")) clicked = 0;
    ImGui::End();

    // En bas à gauche : où l'on est, et comment s'en servir.
    ImGui::SetNextWindowPos({16, h - 16}, 0, {0, 1});
    ImGui::Begin("aide", nullptr, fixed);
    const std::string where = "Tu regardes « " + fb.name + " » depuis " + frDistance(sim.dist) + ".";
    ImGui::TextUnformatted(where.c_str());
    const double boost = sim.brightnessBoost();
    if (boost > 1.5 && sim.dist < 1.0e5) ImGui::TextDisabled("Éclat des étoiles multiplié par %s pour qu'elles restent visibles de si loin.", frNum(boost, 2).c_str());
    if (sim.asteroidCount && sim.asteroidGain(sim.asteroidEpochJd) > 0.01)
        ImGui::TextDisabled("Les petits points sont %s astéroïdes, chacun sur son orbite mesurée (JPL), grossis pour être visibles.", frInt(static_cast<double>(sim.asteroidCount)).c_str());
    if (sim.galaxyGain() > 0.005) {
        ImGui::TextDisabled("Chaque point lointain est une galaxie ou un quasar, placé d'après son décalage vers le rouge mesuré");
        ImGui::TextDisabled("(relevés 2MRS, 6dF, 2dF, SDSS, DESI). Son éclat n'est pas mesuré ici : le point a une taille fixe,");
        ImGui::TextDisabled("qui s'efface avec la distance pour garder l'image lisible (réglage d'affichage, pas une mesure).");
        ImGui::TextDisabled("La Voie lactée elle-même n'est pas encore dessinée : seules ses étoiles mesurées près du Soleil le sont.");
    }
    ImGui::TextDisabled("Molette : zoomer   •   Glisser : tourner autour   •   Clic sur un nom : le suivre   •   Espace : pause   •   Échap : quitter");
    ImGui::End();

    // En bas à droite, quand on regarde l'univers lointain : les réglages de l'expansion, recalculés en direct.
    if (sim.dist > 2.0e6) {
        cosmo::Params& c = sim.cosmology;
        float h0 = static_cast<float>(c.h0), om = static_cast<float>(c.om), ode = static_cast<float>(c.ode), w0 = static_cast<float>(c.w0), wa = static_cast<float>(c.wa);
        ImGui::SetNextWindowPos({w - 16, h - 16}, 0, {1, 1});
        ImGui::Begin("cosmologie", nullptr, fixed);
        ImGui::TextUnformatted("L'univers en expansion");
        ImGui::Separator();
        ImGui::PushItemWidth(240);
        bool changed = false;
        changed |= ImGui::SliderFloat("Vitesse d'expansion (km/s par Mpc)", &h0, 60.0f, 80.0f, "%.1f");
        changed |= ImGui::SliderFloat("Part de matière", &om, 0.05f, 0.60f, "%.3f");
        changed |= ImGui::SliderFloat("Part d'énergie noire", &ode, 0.30f, 0.95f, "%.3f");
        changed |= ImGui::SliderFloat("Énergie noire : w0", &w0, -1.6f, -0.4f, "%.2f");
        changed |= ImGui::SliderFloat("Énergie noire : wa", &wa, -2.0f, 1.0f, "%.2f");
        ImGui::PopItemWidth();
        if (ImGui::Button("Valeurs mesurées (Planck 2018)")) {
            c = cosmo::Params{};
            sim.cosmologyDirty = true;
        } else if (changed) {
            c.h0 = h0; c.om = om; c.ode = ode; c.w0 = w0; c.wa = wa;
            sim.cosmologyDirty = true;
        }
        const double ok = c.omegaK();
        ImGui::TextDisabled("Âge de l'univers : %s milliards d'années (calculé).", frNum(cosmo::ageGyr(c), 4).c_str());
        ImGui::TextDisabled("Forme de l'espace : %s (calculé).", std::fabs(ok) < 0.005 ? "plat" : ok > 0 ? "ouvert (courbure négative)" : "fermé (courbure positive)");
        ImGui::TextDisabled("Bouge un curseur : toutes les galaxies se replacent aussitôt.");
        ImGui::End();
    }
    return clicked;
}

}  // namespace
