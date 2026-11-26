# Univers

Simulation 3D de l'univers, du système solaire ($10^{-20}\text{ m}$ côté Terre) à l'horizon cosmique ($10^{26,95}\text{ m}$) et du Big Bang à $+100\text{ Ga}$, sur données réelles et sourcées.

Toute donnée affichée garde sa provenance et son statut : **mesuré**, **calculé**, **supposé** ou **inconnu** (règle de vérité : [CLAUDE.md](CLAUDE.md)).

## Architecture du dépôt

- **`app/`** — Application web autonome (WebGL2 / Three.js `0.149.0`) assemblée par `python3 app/build.py` → `dist/index.html`, avec 26 tests de calcul Node.js et des tests d'écran Playwright (`app/test/`).
- **`natif/`** — Application PC native (C++20, Vulkan 1.4, Dear ImGui) et bibliothèque physique portable `natif/physique/` compilable sous Linux et Windows.
- **`pipeline/`** — Scripts Python/JS de préparation des catalogues, simulations N-corps de la fusion Voie lactée–Andromède et calculs quantiques (`pipeline/pyproject.toml`).
- **`infra/`** — Modèles de configuration Firebase Hosting / Storage privé (Mission 1).
- **`docs/`** — Plans, audits de précision, audit qualité & gouvernance GitHub ([docs/audit-qualite-github.md](docs/audit-qualite-github.md)).

## Construire et tester

```bash
# 1. Application web + 26 tests de calcul (en parallèle)
python3 app/build.py
printf '%s\n' app/test/*.test.js | xargs -P 4 -n 1 node

# 2. Bibliothèque physique C++20 et essais portables (Linux)
cmake -S natif -B build-linux -DCMAKE_BUILD_TYPE=Release
cmake --build build-linux -j
ctest --test-dir build-linux --output-on-failure

# 3. Tests autonomes du pipeline Python (stdlib uniquement)
python3 pipeline/test_pipeline_stdlib.py
python3 pipeline/sources/test_build_gw.py
```

## Pour commencer

- Règles du dépôt : [CLAUDE.md](CLAUDE.md)
- État et architecture détaillée : [HANDOVER.md](HANDOVER.md)
- Crédits et licences des données : [CREDITS.md](CREDITS.md)
- Mission web en cours (Firebase + tuiles spatiales) : [docs/mission-lot1.md](docs/mission-lot1.md)
