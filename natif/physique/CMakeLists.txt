# Bibliothèque de physique de l'appli PC (lot G : gravité mutuelle). Sans Vulkan ni windows.h.
add_library(univers_physique STATIC systeme_solaire.cpp)
target_include_directories(univers_physique PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(univers_physique PRIVATE -Wall -Wextra)

# Essai : calcul à N corps parti des bornes de DE440, comparé à DE440 lui-même et à JPL Horizons.
add_executable(essai_systeme_solaire essais/essai_systeme_solaire.cpp)
target_include_directories(essai_systeme_solaire PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src)
target_link_libraries(essai_systeme_solaire PRIVATE univers_physique)
target_compile_options(essai_systeme_solaire PRIVATE -Wall -Wextra)
target_link_options(essai_systeme_solaire PRIVATE -static)

# Essai : la Lune de Meeus contre DE440.
add_executable(essai_lune essais/essai_lune.cpp)
target_include_directories(essai_lune PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src)
target_link_libraries(essai_lune PRIVATE univers_physique)
target_compile_options(essai_lune PRIVATE -Wall -Wextra)
target_link_options(essai_lune PRIVATE -static)
# Essai : orbites des étoiles dans la Voie lactée (barre comprise), comparées à la page.
add_executable(essai_galaxie essais/essai_galaxie.cpp)
target_link_libraries(essai_galaxie PRIVATE univers_physique)
target_compile_options(essai_galaxie PRIVATE -Wall -Wextra)
target_link_options(essai_galaxie PRIVATE -static)

# Essai : rejeu du calcul complet de la fusion (centres, traceurs, images des étoiles).
add_executable(essai_fusion essais/essai_fusion.cpp)
target_link_libraries(essai_fusion PRIVATE univers_physique)
target_compile_options(essai_fusion PRIVATE -Wall -Wextra)
target_link_options(essai_fusion PRIVATE -static)

# Horizon du chaos du système solaire (clones écartés de quelques mètres), outil de précalcul (plan-precalcul.md § 3).
add_executable(chaos_systeme_solaire essais/chaos_systeme_solaire.cpp)
target_link_libraries(chaos_systeme_solaire PRIVATE univers_physique)
target_compile_options(chaos_systeme_solaire PRIVATE -Wall -Wextra -O3 -march=native)
target_link_options(chaos_systeme_solaire PRIVATE -static)

# Champ de gravité en coefficients (plan B+, étape 8) : égalité avec pipeline/champ/champ_bfe.py
add_executable(essai_champ_bfe essais/essai_champ_bfe.cpp)
target_compile_options(essai_champ_bfe PRIVATE -Wall -Wextra)
target_link_options(essai_champ_bfe PRIVATE -static)
