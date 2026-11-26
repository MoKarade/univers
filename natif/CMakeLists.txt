# Appli PC « Univers » (docs/plan-natif.md). Se construit sans droits d'administrateur avec les outils portables
# de C:\dev\outils-natif (llvm-mingw, CMake, Ninja, glslang) : voir natif/README.md.
# Sur Linux/macOS, configure et construit automatiquement la bibliothèque physique et les 7 essais CPU portables.
cmake_minimum_required(VERSION 3.24)
project(univers_natif LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(CTest)

if(MSVC)
  set(UNIVERS_WARNINGS /W4)
else()
  set(UNIVERS_WARNINGS -Wall -Wextra -Wpedantic -Wshadow)
endif()

# Bibliothèque physique portable et ses 3 essais (essai_systeme_solaire, essai_galaxie, essai_fusion).
add_subdirectory(physique)

# Essais CPU portables (aucune carte graphique ni dépendance externe requise).
foreach(T essai_ephem essai_orientation essai_cosmologie essai_interface)
  add_executable(${T} src/${T}.cpp)
  target_compile_options(${T} PRIVATE ${UNIVERS_WARNINGS})
  if(MINGW)
    target_link_options(${T} PRIVATE -static)
  endif()
endforeach()

if(BUILD_TESTING)
  add_test(NAME essai_cosmologie COMMAND essai_cosmologie)
  add_test(NAME essai_interface COMMAND essai_interface)
endif()

if(WIN32)
  include(FetchContent)
  # En-têtes Vulkan officiels (Khronos) et volk (chargeur de fonctions Vulkan, Arseny Kapoulkine, licence MIT).
  FetchContent_Declare(vulkan_headers
    GIT_REPOSITORY https://github.com/KhronosGroup/Vulkan-Headers.git
    GIT_TAG v1.4.309
    GIT_SHALLOW ON)
  FetchContent_Declare(volk
    GIT_REPOSITORY https://github.com/zeux/volk.git
    GIT_TAG 1.4.304
    GIT_SHALLOW ON)
  # Dear ImGui (Omar Cornut, licence MIT) : interface. Version figée ; pas de CMake fourni, les sources sont listées ici.
  FetchContent_Declare(imgui
    GIT_REPOSITORY https://github.com/ocornut/imgui.git
    GIT_TAG v1.91.9b
    GIT_SHALLOW ON)
  # stb_image (Sean Barrett, domaine public) : commit épinglé (sans GIT_SHALLOW, interdit par CMake avec un hash).
  FetchContent_Declare(stb
    GIT_REPOSITORY https://github.com/nothings/stb.git
    GIT_TAG 6b5799bae8a1fe3792691ef4b72ae26434c3e799)

  set(VOLK_PULL_IN_VULKAN OFF CACHE BOOL "" FORCE)
  set(VOLK_STATIC_DEFINES "VK_USE_PLATFORM_WIN32_KHR;VK_NO_PROTOTYPES" CACHE STRING "" FORCE)
  FetchContent_MakeAvailable(vulkan_headers volk imgui stb)
  target_link_libraries(volk PUBLIC Vulkan::Headers)

  # Shaders GLSL -> SPIR-V par glslang (Khronos).
  find_program(GLSLANG glslang REQUIRED)
  set(SPV_DIR ${CMAKE_CURRENT_BINARY_DIR}/spv)
  file(MAKE_DIRECTORY ${SPV_DIR})
  set(SPV_FILES)
  foreach(S essai.vert essai.frag etoiles.vert etoiles.frag ecran.vert ecran.frag sphere.frag galaxies.vert asteroides.vert)
    add_custom_command(OUTPUT ${SPV_DIR}/${S}.spv
      COMMAND ${GLSLANG} -V --quiet ${CMAKE_CURRENT_SOURCE_DIR}/shaders/${S} -o ${SPV_DIR}/${S}.spv
      DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/${S} VERBATIM)
    list(APPEND SPV_FILES ${SPV_DIR}/${S}.spv)
  endforeach()
  add_custom_target(shaders DEPENDS ${SPV_FILES})

  add_executable(essai_vulkan src/essai_vulkan.cpp)
  target_link_libraries(essai_vulkan PRIVATE volk)
  target_compile_definitions(essai_vulkan PRIVATE SPV_DIR="${SPV_DIR}")
  target_compile_options(essai_vulkan PRIVATE ${UNIVERS_WARNINGS} $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wno-missing-field-initializers>)
  if(MINGW)
    target_link_options(essai_vulkan PRIVATE -static)
  endif()
  add_dependencies(essai_vulkan shaders)

  add_library(imgui STATIC
    ${imgui_SOURCE_DIR}/imgui.cpp ${imgui_SOURCE_DIR}/imgui_draw.cpp ${imgui_SOURCE_DIR}/imgui_tables.cpp ${imgui_SOURCE_DIR}/imgui_widgets.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_win32.cpp ${imgui_SOURCE_DIR}/backends/imgui_impl_vulkan.cpp)
  target_include_directories(imgui SYSTEM PUBLIC ${imgui_SOURCE_DIR} ${imgui_SOURCE_DIR}/backends)
  target_compile_definitions(imgui PUBLIC IMGUI_IMPL_VULKAN_USE_VOLK IMGUI_IMPL_WIN32_DISABLE_GAMEPAD NOMINMAX WIN32_LEAN_AND_MEAN)
  target_link_libraries(imgui PUBLIC volk dwmapi gdi32)

  # Compilation unique partagée entre univers (console) et UniversPC (sans console, raccourci Bureau).
  add_library(univers_app_obj OBJECT src/univers.cpp src/fenetre.cpp src/stb_impl.cpp)
  target_include_directories(univers_app_obj SYSTEM PRIVATE ${stb_SOURCE_DIR})
  target_link_libraries(univers_app_obj PRIVATE volk imgui univers_physique)
  target_compile_options(univers_app_obj PRIVATE ${UNIVERS_WARNINGS} $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wno-missing-field-initializers>)
  add_dependencies(univers_app_obj shaders)

  add_executable(univers $<TARGET_OBJECTS:univers_app_obj>)
  target_link_libraries(univers PRIVATE volk imgui univers_physique)
  add_dependencies(univers shaders)

  add_executable(UniversPC $<TARGET_OBJECTS:univers_app_obj>)
  target_link_libraries(UniversPC PRIVATE volk imgui univers_physique)
  add_dependencies(UniversPC shaders)

  if(MINGW)
    target_link_options(univers PRIVATE -static)
    target_link_options(UniversPC PRIVATE -static -mwindows)
  elseif(MSVC)
    set_target_properties(UniversPC PROPERTIES WIN32_EXECUTABLE TRUE)
    target_link_options(UniversPC PRIVATE /ENTRY:mainCRTStartup)
  endif()
endif()
