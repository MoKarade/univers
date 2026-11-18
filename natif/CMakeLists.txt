# Appli PC « Univers » (docs/plan-natif.md). Se construit sans droits d'administrateur avec les outils portables
# de C:\dev\outils-natif (llvm-mingw, CMake, Ninja, glslang) : voir natif/README.md.
cmake_minimum_required(VERSION 3.24)
project(univers_natif LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
# En-têtes Vulkan officiels (Khronos) et volk (chargeur de fonctions Vulkan, Arseny Kapoulkine, licence MIT).
FetchContent_Declare(vulkan_headers GIT_REPOSITORY https://github.com/KhronosGroup/Vulkan-Headers.git GIT_TAG v1.4.309 GIT_SHALLOW ON)
FetchContent_Declare(volk GIT_REPOSITORY https://github.com/zeux/volk.git GIT_TAG 1.4.304 GIT_SHALLOW ON)
FetchContent_MakeAvailable(vulkan_headers)
# Dear ImGui (Omar Cornut, licence MIT) : interface. Version figée ; pas de CMake fourni, les sources sont listées ici.
FetchContent_Declare(imgui GIT_REPOSITORY https://github.com/ocornut/imgui.git GIT_TAG v1.91.9b GIT_SHALLOW ON)
# stb_image (Sean Barrett, domaine public) : lecture des cartes de surface en JPEG et PNG.
FetchContent_Declare(stb GIT_REPOSITORY https://github.com/nothings/stb.git GIT_TAG master GIT_SHALLOW ON)
FetchContent_GetProperties(stb)
if(NOT stb_POPULATED)
  FetchContent_Populate(stb)
endif()
FetchContent_GetProperties(imgui)
if(NOT imgui_POPULATED)
  FetchContent_Populate(imgui)
endif()
FetchContent_GetProperties(volk)
if(NOT volk_POPULATED)
  FetchContent_Populate(volk)
endif()

add_library(volk STATIC ${volk_SOURCE_DIR}/volk.c)
target_include_directories(volk PUBLIC ${volk_SOURCE_DIR})
target_link_libraries(volk PUBLIC Vulkan::Headers)
target_compile_definitions(volk PUBLIC VK_USE_PLATFORM_WIN32_KHR VK_NO_PROTOTYPES)

# Shaders GLSL -> SPIR-V par glslang (Khronos).
find_program(GLSLANG glslang REQUIRED)
set(SPV_DIR ${CMAKE_BINARY_DIR}/spv)
file(MAKE_DIRECTORY ${SPV_DIR})
set(SPV_FILES)
foreach(S essai.vert essai.frag etoiles.vert etoiles.frag ecran.vert ecran.frag sphere.frag galaxies.vert asteroides.vert gaia.vert gaia_reste.vert gaia_agrege.vert voie_lactee.frag etoiles_orbite.vert orbites_pas.comp ciel_bandes.frag fusion_nuage.vert ciel_sources.vert ciel_sources.frag gaia_ciel.vert galaxie_formes.vert)
  add_custom_command(OUTPUT ${SPV_DIR}/${S}.spv
    COMMAND ${GLSLANG} -V --quiet -I${CMAKE_SOURCE_DIR}/shaders ${CMAKE_SOURCE_DIR}/shaders/${S} -o ${SPV_DIR}/${S}.spv
    DEPENDS ${CMAKE_SOURCE_DIR}/shaders/${S} ${CMAKE_SOURCE_DIR}/shaders/orbite_galactique.glsl ${CMAKE_SOURCE_DIR}/shaders/gaia_acc.glsl ${CMAKE_SOURCE_DIR}/shaders/gaia_fiable.glsl VERBATIM)
  list(APPEND SPV_FILES ${SPV_DIR}/${S}.spv)
endforeach()
add_custom_target(shaders DEPENDS ${SPV_FILES})

add_executable(essai_vulkan src/essai_vulkan.cpp)
target_link_libraries(essai_vulkan PRIVATE volk)
target_compile_definitions(essai_vulkan PRIVATE SPV_DIR="${SPV_DIR}")
target_compile_options(essai_vulkan PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
target_link_options(essai_vulkan PRIVATE -static)
add_dependencies(essai_vulkan shaders)

add_library(imgui STATIC
  ${imgui_SOURCE_DIR}/imgui.cpp ${imgui_SOURCE_DIR}/imgui_draw.cpp ${imgui_SOURCE_DIR}/imgui_tables.cpp ${imgui_SOURCE_DIR}/imgui_widgets.cpp
  ${imgui_SOURCE_DIR}/backends/imgui_impl_win32.cpp ${imgui_SOURCE_DIR}/backends/imgui_impl_vulkan.cpp)
target_include_directories(imgui PUBLIC ${imgui_SOURCE_DIR} ${imgui_SOURCE_DIR}/backends)
target_compile_definitions(imgui PUBLIC IMGUI_IMPL_VULKAN_USE_VOLK IMGUI_IMPL_WIN32_DISABLE_GAMEPAD NOMINMAX WIN32_LEAN_AND_MEAN)
target_link_libraries(imgui PUBLIC volk dwmapi gdi32)

# univers : avec console (contrôles). UniversPC : le même programme sans console, lancé par le raccourci du Bureau.
foreach(T univers UniversPC)
  add_executable(${T} src/univers.cpp src/fenetre.cpp src/stb_impl.cpp)
  target_include_directories(${T} PRIVATE ${stb_SOURCE_DIR})
  target_link_libraries(${T} PRIVATE volk imgui univers_physique)
  target_compile_options(${T} PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
  add_dependencies(${T} shaders)
endforeach()
target_link_options(univers PRIVATE -static)
target_link_options(UniversPC PRIVATE -static -mwindows)

# Contrôle du lecteur d'éphémérides NASA contre JPL Horizons (aucune carte graphique nécessaire).
add_executable(essai_ephem src/essai_ephem.cpp)
target_compile_options(essai_ephem PRIVATE -Wall -Wextra)
target_link_options(essai_ephem PRIVATE -static)

# Contrôle de l'orientation des astres (Terre : Soleil au zénith ; Lune : face tournée vers la Terre).
add_executable(essai_orientation src/essai_orientation.cpp)
target_compile_options(essai_orientation PRIVATE -Wall -Wextra)
target_link_options(essai_orientation PRIVATE -static)

# Contrôle d'une éclipse de Soleil (éphémérides + orientation de la Terre) contre la NASA.
add_executable(essai_eclipse src/essai_eclipse.cpp)
target_compile_options(essai_eclipse PRIVATE -Wall -Wextra)
target_link_options(essai_eclipse PRIVATE -static)

# Contrôle des distances cosmologiques contre astropy.
add_executable(essai_cosmologie src/essai_cosmologie.cpp)
add_executable(essai_bac_a_sable src/essai_bac_a_sable.cpp)
target_compile_options(essai_bac_a_sable PRIVATE -Wall -Wextra)
target_link_options(essai_bac_a_sable PRIVATE -static)
target_compile_options(essai_cosmologie PRIVATE -Wall -Wextra)
target_link_options(essai_cosmologie PRIVATE -static)

# Contrôle des outils de texte de l'interface (recherche, dates tapées).
add_executable(essai_interface src/essai_interface.cpp)
target_compile_options(essai_interface PRIVATE -Wall -Wextra)
target_link_options(essai_interface PRIVATE -static)

# Contrôle de la complétude par échelle (completude.h) sur le vrai fichier d'étoiles.
add_executable(essai_completude src/essai_completude.cpp)
target_link_libraries(essai_completude PRIVATE volk imgui univers_physique)
target_compile_options(essai_completude PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(essai_completude PRIVATE -static)

add_subdirectory(physique)

# Contrôle des trajectoires des sondes contre JPL Horizons.
add_executable(essai_sondes src/essai_sondes.cpp)
target_compile_options(essai_sondes PRIVATE -Wall -Wextra)
target_link_options(essai_sondes PRIVATE -static)

# Contrôle sans fenêtre des étoiles Gaia DR3 (gaia.h) : image hors écran, cadence, étoiles dessinées.
add_executable(essai_gaia src/essai_gaia.cpp)
target_link_libraries(essai_gaia PRIVATE volk univers_physique)
target_compile_options(essai_gaia PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(essai_gaia PRIVATE -static)
add_dependencies(essai_gaia shaders)

# Contrôle du mouvement des étoiles autour de la Galaxie (orbite_galactique.h, shaders/orbite_galactique.glsl).
add_executable(essai_orbite src/essai_orbite.cpp)
target_link_libraries(essai_orbite PRIVATE volk univers_physique)
target_compile_options(essai_orbite PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(essai_orbite PRIVATE -static)

# Précision mesurée des épicycles contre l'intégration exacte, sur les étoiles d'etoiles.bin.
add_executable(essai_epicycles src/essai_epicycles.cpp)
target_link_libraries(essai_epicycles PRIVATE volk univers_physique)
target_compile_options(essai_epicycles PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(essai_epicycles PRIVATE -static)

# Contrôle sans fenêtre du ciel par bande (ciel_bandes.h) : carte mesurée d'une longueur d'onde, image hors écran.
add_executable(essai_ciel src/essai_ciel.cpp)
target_link_libraries(essai_ciel PRIVATE volk)
target_compile_options(essai_ciel PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(essai_ciel PRIVATE -static)
add_dependencies(essai_ciel shaders)

# Précalcul sur la carte graphique sans fenêtre, avec shaders/orbites_pas.comp (plan-precalcul.md § 1) : contrôle du shader
# contre la bibliothèque en double, et écart des clones d'incertitude de chaque étoile.
add_executable(precalcul_clones src/precalcul_clones.cpp)
target_link_libraries(precalcul_clones PRIVATE volk univers_physique)
target_compile_options(precalcul_clones PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(precalcul_clones PRIVATE -static)
add_dependencies(precalcul_clones shaders)

# Temps très rapide hors de la plage de la NASA : les planètes restent visibles (sans fenêtre).
add_executable(essai_temps_rapide src/essai_temps_rapide.cpp src/stb_impl.cpp)
target_include_directories(essai_temps_rapide PRIVATE ${stb_SOURCE_DIR})
target_link_libraries(essai_temps_rapide PRIVATE volk imgui univers_physique)
target_compile_options(essai_temps_rapide PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
target_link_options(essai_temps_rapide PRIVATE -static)

# Essai d'ensemble : continuité des astres nommés sur toute la plage de dates (sans fenêtre).
add_executable(essai_continuite src/essai_continuite.cpp src/stb_impl.cpp)
target_include_directories(essai_continuite PRIVATE ${stb_SOURCE_DIR})
target_link_libraries(essai_continuite PRIVATE volk imgui univers_physique)
target_compile_options(essai_continuite PRIVATE -Wall -Wextra -Wno-missing-field-initializers -Wno-unused-function)
