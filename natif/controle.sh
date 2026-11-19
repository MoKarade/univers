#!/usr/bin/env bash
# Un seul geste : fabrique l'appli PC et lance tous ses essais sans fenêtre, sur les vraies données installées.
# Les essais natifs ne tournent pas sur GitHub (Windows, données de plusieurs Go, minutes comptées) : ce script est le
# contrôle à lancer avant toute fusion dans appli-pc. Il ne touche ni à l'appli installée ni aux calculs en cours ; seuls
# essai_vulkan et la capture finale utilisent la carte graphique, quelques secondes.
#
# Usage : bash natif/controle.sh [dossier de fabrication] [dossier des données]
#   défauts : /c/tmp/natif/build-controle et /c/dev/Univers-PC
# Rend 0 si tout passe. La dernière ligne dit PASSE ou ECHEC.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
B="${1:-/c/tmp/natif/build-controle}"
D="${2:-/c/dev/Univers-PC}"
T=/c/dev/outils-natif
export PATH="$T/llvm-mingw-20261104-ucrt-x86_64/bin:$T/cmake-4.4.5-windows-x86_64/bin:$T:$T/glslang/bin:$PATH"
# Cassures de continuité connues (docs/revue-detaillee.md). Ce nombre ne doit que baisser : le remettre à jour à la baisse
# à chaque cassure réparée, jamais à la hausse.
CASSURES_MAX=29

if [ ! -f "$B/build.ninja" ]; then
  DEPS=/c/tmp/natif/build/_deps      # sources déjà téléchargées par la fabrication principale, si elle existe
  EXTRA=""
  if [ -d "$DEPS/imgui-src" ]; then
    EXTRA="-DFETCHCONTENT_SOURCE_DIR_VULKAN_HEADERS=$DEPS/vulkan_headers-src -DFETCHCONTENT_SOURCE_DIR_VOLK=$DEPS/volk-src -DFETCHCONTENT_SOURCE_DIR_IMGUI=$DEPS/imgui-src -DFETCHCONTENT_SOURCE_DIR_STB=$DEPS/stb-src"
  fi
  cmake -S "$ICI" -B "$B" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ $EXTRA > "$B.configure.log" 2>&1 || { echo "ECHEC : préparation (voir $B.configure.log)"; exit 1; }
fi
cmake --build "$B" > "$B.build.log" 2>&1 || { tail -20 "$B.build.log"; echo "ECHEC : fabrication"; exit 1; }
echo "fabrication : faite"

R="$ICI/../pipeline/natif"
echecs=0
essai() {  # nom, puis la commande
  local nom=$1; shift
  local t0=$SECONDS
  if "$@" > "$B/$nom.log" 2>&1 && ! grep -q "ECHEC" "$B/$nom.log"; then
    printf '  PASSE  %-26s %3d s\n' "$nom" $((SECONDS - t0))
  else
    printf '  ECHEC  %-26s %3d s   (%s)\n' "$nom" $((SECONDS - t0)) "$B/$nom.log"
    echecs=$((echecs + 1))
  fi
}
P="$B/physique"
[ -x "$P/essai_lune.exe" ] || P="$B"
essai vulkan            "$B/essai_vulkan.exe"
REF_EPHEM="$R/ref_ephem.txt"; [ -f "$REF_EPHEM" ] || REF_EPHEM=/c/tmp/natif/ref_ephem.txt      # valeurs de Horizons écrites par pipeline/natif/ref_ephem.py
essai ephemerides       "$B/essai_ephem.exe" "$D/de440.bsp" "$REF_EPHEM"
essai orientation       "$B/essai_orientation.exe" "$D/de440.bsp"
essai eclipses          "$B/essai_eclipse.exe" "$D/de440.bsp"
essai cosmologie        "$B/essai_cosmologie.exe"
essai bac_a_sable       "$B/essai_bac_a_sable.exe" "$D"
essai interface         "$B/essai_interface.exe"
essai completude        "$B/essai_completude.exe" "$D"
essai structures        "$B/essai_structures.exe" "$D"
essai sondes            "$B/essai_sondes.exe" "$D/sondes.bin" "$R/ref_sondes.txt"
essai orbite_constantes "$B/essai_orbite.exe" "$ICI/shaders/orbite_galactique.glsl"
essai temps_rapide      "$B/essai_temps_rapide.exe" "$D/etoiles.bin"
essai lune              "$P/essai_lune.exe" "$D/de440.bsp"
essai systeme_solaire   "$P/essai_systeme_solaire.exe" "$D/de440.bsp" "$D/orbites_planetes.bin"
essai galaxie_orbites   "$P/essai_galaxie.exe"
# Film du Groupe local : seulement s'il est là (dossier écrit dans film_dossier.txt, à côté des données).
FILM="$(head -1 "$D/film_dossier.txt" 2>/dev/null | tr -d '
')"
[ -n "$FILM" ] && [ -f "$FILM/film_index.bin" ] && essai film "$P/essai_film.exe" "$FILM"
essai continuite        "$B/essai_continuite.exe" "$D/etoiles.bin" --max "$CASSURES_MAX"
grep -E "cassures de continuité|Référence" "$B/continuite.log" | sed 's/^/         /'

if [ "$echecs" -eq 0 ]; then echo "PASSE"; else echo "ECHEC : $echecs essai(s)"; fi
exit "$echecs"
