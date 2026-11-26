# Bibliothèque de physique de l'appli PC (lot G : gravité mutuelle). Sans Vulkan ni windows.h.
# Se construit seule (cmake -S natif/physique, Linux ou Windows) ou incluse par natif/CMakeLists.txt.
cmake_minimum_required(VERSION 3.20)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(univers_physique LANGUAGES CXX)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
endif()
# Lien statique seulement sous Windows (MinGW) : les .exe partent sans DLL. Sous Linux, -static avec la glibc
# n'apporte rien et avertit (getpwnam, dlopen...).
if(WIN32)
  set(UNIVERS_LIEN_STATIQUE -static)
else()
  set(UNIVERS_LIEN_STATIQUE)
endif()
add_library(univers_physique STATIC systeme_solaire.cpp)
target_include_directories(univers_physique PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(univers_physique PRIVATE -Wall -Wextra)

# Essai : calcul à N corps parti des bornes de DE440, comparé à DE440 lui-même et à JPL Horizons.
add_executable(essai_systeme_solaire essais/essai_systeme_solaire.cpp)
target_include_directories(essai_systeme_solaire PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src)
target_link_libraries(essai_systeme_solaire PRIVATE univers_physique)
target_compile_options(essai_systeme_solaire PRIVATE -Wall -Wextra)
target_link_options(essai_systeme_solaire PRIVATE ${UNIVERS_LIEN_STATIQUE})

# Essai : la Lune de Meeus contre DE440.
add_executable(essai_lune essais/essai_lune.cpp)
target_include_directories(essai_lune PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src)
target_link_libraries(essai_lune PRIVATE univers_physique)
target_compile_options(essai_lune PRIVATE -Wall -Wextra)
target_link_options(essai_lune PRIVATE ${UNIVERS_LIEN_STATIQUE})
# Essai : orbites des étoiles dans la Voie lactée (barre comprise), comparées à la page.
add_executable(essai_galaxie essais/essai_galaxie.cpp)
target_link_libraries(essai_galaxie PRIVATE univers_physique)
target_compile_options(essai_galaxie PRIVATE -Wall -Wextra)
target_link_options(essai_galaxie PRIVATE ${UNIVERS_LIEN_STATIQUE})

# Essai : rejeu du calcul complet de la fusion (centres, traceurs, images des étoiles).
add_executable(essai_fusion essais/essai_fusion.cpp)
target_link_libraries(essai_fusion PRIVATE univers_physique)
target_compile_options(essai_fusion PRIVATE -Wall -Wextra)
target_link_options(essai_fusion PRIVATE ${UNIVERS_LIEN_STATIQUE})

# Horizon du chaos du système solaire (clones écartés de quelques mètres), outil de précalcul (plan-precalcul.md § 3).
add_executable(chaos_systeme_solaire essais/chaos_systeme_solaire.cpp)
target_link_libraries(chaos_systeme_solaire PRIVATE univers_physique)
target_compile_options(chaos_systeme_solaire PRIVATE -Wall -Wextra -O3 -march=native)
target_link_options(chaos_systeme_solaire PRIVATE ${UNIVERS_LIEN_STATIQUE})

# Champ de gravité en coefficients (plan B+, étape 8) : égalité avec pipeline/champ/champ_bfe.py
add_executable(essai_champ_bfe essais/essai_champ_bfe.cpp)
target_compile_options(essai_champ_bfe PRIVATE -Wall -Wextra)
target_link_options(essai_champ_bfe PRIVATE ${UNIVERS_LIEN_STATIQUE})

# Essai : lecteur du film version 2 du Groupe local (étoiles visibles emportées par le calcul unique).
add_executable(essai_film essais/essai_film.cpp)
target_link_libraries(essai_film PRIVATE univers_physique)
target_compile_options(essai_film PRIVATE -Wall -Wextra)
target_link_options(essai_film PRIVATE ${UNIVERS_LIEN_STATIQUE})

# Essai : lecteur du film version 3 (pipeline/fusion/film_v3.py), contre le lecteur Python sur un petit film d'essai.
add_executable(essai_film_v3 essais/essai_film_v3.cpp)
target_include_directories(essai_film_v3 PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(essai_film_v3 PRIVATE -Wall -Wextra)
target_link_options(essai_film_v3 PRIVATE ${UNIVERS_LIEN_STATIQUE})
