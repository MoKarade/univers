// Chronomètre par image et par étape (mesure de la cadence, 20/11/2026). Éteint par défaut : rien n'est mesuré ni écrit.
//
// UNIVERS_CHRONO=<fichier.csv> l'allume : chaque image écrit une ligne par étape (« cpu » : temps du processeur entre deux
// repères ; « gpu » : temps de la carte graphique entre deux horodatages posés dans les commandes de l'image). À la fin,
// un résumé par étape (moyenne, médiane, 95e centile, maximum) est imprimé. Les horodatages de la carte sont lus une
// image plus tard, sans attente (la barrière de l'image est déjà passée à ce moment).
#pragma once
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <map>
#include <string>
#include <vector>

#include "commun.h"

namespace univers {

struct Chrono {
    static constexpr uint32_t kMaxMarks = 64;
    bool on = false;

    void init(const Gpu& g) {
        const char* path = std::getenv("UNIVERS_CHRONO");
        if (!path || !*path) return;
        out_ = std::fopen(path, "w");
        if (!out_) return;
        std::fprintf(out_, "image,genre,etape,ms,distance_al,annee\n");
        VkPhysicalDeviceProperties props;
        vkGetPhysicalDeviceProperties(g.pd, &props);
        period_ = props.limits.timestampPeriod;      // nanosecondes par tic
        VkQueryPoolCreateInfo qi{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};
        qi.queryType = VK_QUERY_TYPE_TIMESTAMP;
        qi.queryCount = kMaxMarks;
        check(vkCreateQueryPool(g.dev, &qi, nullptr, &pool_), "horodatages");
        on = true;
        cpuT_ = std::chrono::steady_clock::now();
    }
    void release(const Gpu& g) {
        if (pool_) vkDestroyQueryPool(g.dev, pool_, nullptr);
        pool_ = VK_NULL_HANDLE;
        if (out_) std::fclose(out_);
        out_ = nullptr;
    }

    // Processeur : temps écoulé depuis le repère précédent, rangé sous ce nom (cumulé si le nom revient dans l'image).
    void cpu(const char* name) {
        if (!on) return;
        const auto t = std::chrono::steady_clock::now();
        cpuRows_.emplace_back(name, std::chrono::duration<double, std::milli>(t - cpuT_).count());
        cpuT_ = t;
    }

    // Carte : début des commandes de l'image (remet les horodatages à zéro), puis un repère après chaque étape.
    void gpuBegin(VkCommandBuffer cmd) {
        if (!on) return;
        vkCmdResetQueryPool(cmd, pool_, 0, kMaxMarks);
        names_.clear();
        cpu("enreg. debut");
        vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, pool_, 0);
        names_.push_back("debut");
    }
    void gpu(VkCommandBuffer cmd, const char* name) {
        if (!on || names_.empty() || names_.size() >= kMaxMarks) return;
        cpu(("enreg. " + std::string(name)).c_str());      // part du processeur pour préparer cette étape
        vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, pool_, static_cast<uint32_t>(names_.size()));
        names_.push_back(name);
    }
    // Après l'envoi : ces repères seront lus à l'image suivante.
    void gpuSubmitted() { submittedNames_ = names_; }

    // Après la barrière de l'image précédente : lit ses horodatages (déjà prêts).
    void gpuCollect(const Gpu& g) {
        if (!on || submittedNames_.size() < 2) return;
        std::vector<uint64_t> ts(submittedNames_.size());
        const VkResult r = vkGetQueryPoolResults(g.dev, pool_, 0, static_cast<uint32_t>(ts.size()), ts.size() * sizeof(uint64_t), ts.data(), sizeof(uint64_t),
                                                 VK_QUERY_RESULT_64_BIT);
        if (r != VK_SUCCESS) return;
        for (size_t k = 1; k < ts.size(); ++k) gpuRows_.emplace_back(submittedNames_[k], static_cast<double>(ts[k] - ts[k - 1]) * period_ * 1.0e-6);
        gpuRows_.emplace_back("total", static_cast<double>(ts.back() - ts.front()) * period_ * 1.0e-6);
        submittedNames_.clear();
    }

    // Fin de l'image : écrit ses lignes. wallMs : durée réelle de l'image (horloge, d'un tour de boucle au suivant).
    void endFrame(double wallMs, double distLy, double years) {
        if (!on) return;
        double cpuTotal = 0;
        for (const auto& [n, ms] : cpuRows_) cpuTotal += ms;
        cpuRows_.emplace_back("total", cpuTotal);
        auto write = [&](const char* kind, const std::vector<std::pair<std::string, double>>& rows) {
            std::map<std::string, double> merged;
            for (const auto& [n, ms] : rows) merged[n] += ms;
            for (const auto& [n, ms] : merged) {
                std::fprintf(out_, "%ld,%s,\"%s\",%.4f,%.6g,%.6g\n", frame_, kind, n.c_str(), ms, distLy, years);      /* nom entre guillemets : il peut contenir des virgules */
                stats_[std::string(kind) + " " + n].push_back(ms);
            }
        };
        write("cpu", cpuRows_);
        write("gpu", gpuRows_);
        std::fprintf(out_, "%ld,image,image,%.4f,%.6g,%.6g\n", frame_, wallMs, distLy, years);
        stats_["image"].push_back(wallMs);
        cpuRows_.clear();
        gpuRows_.clear();
        ++frame_;
    }

    void summary() const {
        if (!on) return;
        std::printf("chrono : %ld images (ms : moyenne, mediane, 95e centile, max)\n", frame_);
        for (const auto& [n, v] : stats_) {
            std::vector<double> s = v;
            std::sort(s.begin(), s.end());
            double m = 0;
            for (double x : s) m += x;
            m /= static_cast<double>(s.size());
            auto q = [&](double p) { return s[std::min(s.size() - 1, static_cast<size_t>(p * static_cast<double>(s.size())))]; };
            std::printf("  %-34s %8.3f %8.3f %8.3f %8.3f\n", n.c_str(), m, q(0.5), q(0.95), s.back());
        }
    }

private:
    FILE* out_ = nullptr;
    VkQueryPool pool_ = VK_NULL_HANDLE;
    float period_ = 1.0f;
    long frame_ = 0;
    std::chrono::steady_clock::time_point cpuT_;
    std::vector<std::pair<std::string, double>> cpuRows_, gpuRows_;
    std::vector<std::string> names_, submittedNames_;
    std::map<std::string, std::vector<double>> stats_;
};

}  // namespace univers
