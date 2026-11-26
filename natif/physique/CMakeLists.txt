# Bibliothèque de physique de l'appli PC (lot G : gravité mutuelle). Sans Vulkan ni windows.h.
cmake_minimum_required(VERSION 3.24)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(univers_physique LANGUAGES CXX)
  set(CMAKE_CXX_EXTENSIONS OFF)
  include(CTest)
endif()

find_package(Threads REQUIRED)

if(MSVC)
  set(UNIVERS_PHYSIQUE_WARNINGS /W4)
else()
  set(UNIVERS_PHYSIQUE_WARNINGS -Wall -Wextra -Wpedantic -Wshadow)
endif()

add_library(univers_physique STATIC systeme_solaire.cpp)
target_compile_features(univers_physique PUBLIC cxx_std_20)
set_target_properties(univers_physique PROPERTIES CXX_EXTENSIONS OFF)
target_include_directories(univers_physique PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(univers_physique PUBLIC Threads::Threads)
target_compile_options(univers_physique PRIVATE ${UNIVERS_PHYSIQUE_WARNINGS})

# Essai : calcul à N corps parti des bornes de DE440, comparé à DE440 lui-même et à JPL Horizons.
add_executable(essai_systeme_solaire essais/essai_systeme_solaire.cpp)
set_target_properties(essai_systeme_solaire PROPERTIES CXX_EXTENSIONS OFF)
target_include_directories(essai_systeme_solaire PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src)
target_link_libraries(essai_systeme_solaire PRIVATE univers_physique)
target_compile_options(essai_systeme_solaire PRIVATE ${UNIVERS_PHYSIQUE_WARNINGS})

# Essai : orbites des étoiles dans la Voie lactée (barre comprise), comparées à la page.
add_executable(essai_galaxie essais/essai_galaxie.cpp)
set_target_properties(essai_galaxie PROPERTIES CXX_EXTENSIONS OFF)
target_link_libraries(essai_galaxie PRIVATE univers_physique)
target_compile_options(essai_galaxie PRIVATE ${UNIVERS_PHYSIQUE_WARNINGS})

# Essai : rejeu du calcul complet de la fusion (centres, traceurs, images des étoiles).
add_executable(essai_fusion essais/essai_fusion.cpp)
set_target_properties(essai_fusion PROPERTIES CXX_EXTENSIONS OFF)
target_link_libraries(essai_fusion PRIVATE univers_physique)
target_compile_options(essai_fusion PRIVATE ${UNIVERS_PHYSIQUE_WARNINGS})

# Essai autonome : entrées hostiles ou limites (dates non finies, fichiers de synthèse corrompus, bornes à 1 ULP).
add_executable(essai_robustesse essais/essai_robustesse.cpp)
set_target_properties(essai_robustesse PROPERTIES CXX_EXTENSIONS OFF)
target_link_libraries(essai_robustesse PRIVATE univers_physique)
target_compile_options(essai_robustesse PRIVATE ${UNIVERS_PHYSIQUE_WARNINGS})

if(MINGW)
  target_link_options(essai_systeme_solaire PRIVATE -static)
  target_link_options(essai_galaxie PRIVATE -static)
  target_link_options(essai_fusion PRIVATE -static)
  target_link_options(essai_robustesse PRIVATE -static)
endif()

if(BUILD_TESTING)
  add_test(NAME essai_galaxie COMMAND essai_galaxie)
  add_test(NAME essai_systeme_solaire_noyau COMMAND essai_systeme_solaire --noyau)
  add_test(NAME essai_robustesse COMMAND essai_robustesse)
endif()
