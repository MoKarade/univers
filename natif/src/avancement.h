// Appli PC « Univers » : où en sont les calculs de fond du PC (demande de Marc, 12 novembre 2026 : « je veux un
// indicateur qui montre où ça en est »).
// Chaque tâche de fond (téléchargement, calcul long) écrit un petit fichier texte dans le dossier « avancement » à côté
// des données de l'appli : NOM.txt, lignes clé=valeur (nom, fait, total, unite, debut, maj, etat, detail ; dates en heure
// locale, 2026-11-12T15:31:20). L'appli relit le dossier toutes les 2 secondes et en tire le pourcentage et le temps
// restant (durée écoulée x reste / fait). Rien n'est inventé : sans avancement mesuré, la durée est dite inconnue.
#pragma once
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

struct TaskProgress {
    std::string name, unit, state, detail;
    double done = 0, total = 0;
    double percent = 0;                // 0 à 100
    double remainingSeconds = -1;      // -1 : inconnu
    bool stale = false;                // « en cours » mais sans nouvelles depuis plus de 3 minutes
    bool finished = false;
};

inline std::time_t parseLocalTime(const std::string& s) {
    std::tm tm{};
    if (std::sscanf(s.c_str(), "%d-%d-%dT%d:%d:%d", &tm.tm_year, &tm.tm_mon, &tm.tm_mday, &tm.tm_hour, &tm.tm_min, &tm.tm_sec) < 5) return 0;
    tm.tm_year -= 1900;
    tm.tm_mon -= 1;
    tm.tm_isdst = -1;
    return std::mktime(&tm);
}

// Lit toutes les tâches du dossier. Une tâche terminée depuis plus de 10 minutes n'est plus rendue.
inline std::vector<TaskProgress> readTasks(const std::string& dir) {
    std::vector<TaskProgress> out;
    std::error_code ec;
    const std::time_t now = std::time(nullptr);
    for (const auto& e : std::filesystem::directory_iterator(dir, ec)) {
        if (e.path().extension() != ".txt") continue;
        std::ifstream f(e.path());
        TaskProgress t;
        std::time_t start = 0, update = 0;
        for (std::string line; std::getline(f, line);) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            const size_t eq = line.find('=');
            if (eq == std::string::npos) continue;
            const std::string k = line.substr(0, eq), v = line.substr(eq + 1);
            if (k == "nom") t.name = v;
            else if (k == "unite") t.unit = v;
            else if (k == "etat") t.state = v;
            else if (k == "detail") t.detail = v;
            else if (k == "fait") t.done = std::atof(v.c_str());
            else if (k == "total") t.total = std::atof(v.c_str());
            else if (k == "debut") start = parseLocalTime(v);
            else if (k == "maj") update = parseLocalTime(v);
        }
        if (t.name.empty()) continue;
        t.finished = t.state.rfind("termin", 0) == 0;
        if (t.finished && update && now - update > 600) continue;
        t.percent = t.total > 0 ? std::min(100.0, std::max(0.0, 100.0 * t.done / t.total)) : 0;
        if (t.finished) t.percent = 100;
        const bool running = t.state == "en cours";
        t.stale = running && update && now - update > 180;
        if (running && !t.stale && t.done > 0 && t.total > t.done && start && update > start)
            t.remainingSeconds = static_cast<double>(update - start) * (t.total - t.done) / t.done - static_cast<double>(now - update);
        if (t.remainingSeconds < 0 && t.remainingSeconds != -1) t.remainingSeconds = 0;
        out.push_back(t);
    }
    return out;
}
