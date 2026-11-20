// Travail d'une image partagé entre les cœurs du processeur (mesure du 20/11/2026 : le choix des feuilles Gaia prenait
// jusqu'à 15 ms par image sur un seul cœur, deux fois : Gaia et Gaia B). Fils créés une seule fois, réveillés à chaque appel.
//
// parallele::pour(n, f) appelle f(debut, fin, morceau) sur kMorceaux tranches contiguës de [0, n), dans l'ordre des
// morceaux, chacune sur un fil, et rend la main quand toutes sont finies. Les résultats rangés par morceau puis remis
// bout à bout dans l'ordre donnent exactement ce qu'aurait donné la boucle sur un seul cœur.
#pragma once
#include <algorithm>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

namespace parallele {

class Reserve {
public:
    static Reserve& une() {
        static Reserve r;
        return r;
    }
    unsigned fils() const { return static_cast<unsigned>(fils_.size()) + 1; }

    // f(morceau) pour morceau = 0..m-1 ; le fil appelant en fait sa part.
    void lance(unsigned m, const std::function<void(unsigned)>& f) {
        if (m <= 1 || fils_.empty()) {
            for (unsigned k = 0; k < m; ++k) f(k);
            return;
        }
        std::lock_guard<std::mutex> seul(appel_);      // un seul appel à la fois (Gaia et Gaia B se suivent)
        {
            std::lock_guard<std::mutex> l(m_);
            tache_ = &f;
            total_ = m;
            prochain_ = 0;
            restants_ = m;
            ++tour_;
        }
        cv_.notify_all();
        travaille();
        std::unique_lock<std::mutex> l(m_);
        fini_.wait(l, [this] { return restants_ == 0; });
        tache_ = nullptr;
    }

    ~Reserve() {
        {
            std::lock_guard<std::mutex> l(m_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& t : fils_) t.join();
    }

private:
    Reserve() {
        const unsigned n = std::clamp(std::thread::hardware_concurrency() / 2, 1u, 16u);      // cœurs physiques, sans les jumeaux
        for (unsigned i = 1; i < n; ++i) fils_.emplace_back([this] { boucle(); });
    }
    void travaille() {
        for (;;) {
            unsigned k;
            const std::function<void(unsigned)>* f;
            {
                std::lock_guard<std::mutex> l(m_);
                if (!tache_ || prochain_ >= total_) return;
                k = prochain_++;
                f = tache_;
            }
            (*f)(k);
            std::lock_guard<std::mutex> l(m_);
            if (--restants_ == 0) fini_.notify_all();
        }
    }
    void boucle() {
        uint64_t vu = 0;
        for (;;) {
            {
                std::unique_lock<std::mutex> l(m_);
                cv_.wait(l, [&] { return stop_ || tour_ != vu; });
                if (stop_) return;
                vu = tour_;
            }
            travaille();
        }
    }
    std::vector<std::thread> fils_;
    std::mutex m_, appel_;
    std::condition_variable cv_, fini_;
    const std::function<void(unsigned)>* tache_ = nullptr;
    unsigned total_ = 0, prochain_ = 0, restants_ = 0;
    uint64_t tour_ = 0;
    bool stop_ = false;
};

// Tranches contiguës de [0, n) : f(debut, fin, morceau). seuil : en dessous de ce nombre d'éléments, un seul morceau (travail
// trop court pour réveiller les fils) ; à baisser quand chaque élément coûte cher (étoiles du cycle de vie : 1).
inline unsigned morceaux(uint64_t n, uint64_t seuil = 4096) { return n < seuil ? 1u : static_cast<unsigned>(std::min<uint64_t>(n, Reserve::une().fils() * 2)); }
inline void pour(uint64_t n, const std::function<void(uint64_t, uint64_t, unsigned)>& f, uint64_t seuil = 4096) {
    const unsigned m = morceaux(n, seuil);
    Reserve::une().lance(m, [&](unsigned k) { f(n * k / m, n * (k + 1) / m, k); });
}

}  // namespace parallele
