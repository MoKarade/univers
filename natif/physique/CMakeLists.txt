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

# Essai : orbites des étoiles dans la Voie lactée (barre comprise), comparées à la page.
add_executable(essai_galaxie essais/essai_galaxie.cpp)
target_link_libraries(essai_galaxie PRIVATE univers_physique)
target_compile_options(essai_galaxie PRIVATE -Wall -Wextra)
target_link_options(essai_galaxie PRIVATE -static)
