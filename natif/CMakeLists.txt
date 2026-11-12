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
foreach(S essai.vert essai.frag)
  add_custom_command(OUTPUT ${SPV_DIR}/${S}.spv
    COMMAND ${GLSLANG} -V --quiet ${CMAKE_SOURCE_DIR}/shaders/${S} -o ${SPV_DIR}/${S}.spv
    DEPENDS ${CMAKE_SOURCE_DIR}/shaders/${S} VERBATIM)
  list(APPEND SPV_FILES ${SPV_DIR}/${S}.spv)
endforeach()
add_custom_target(shaders DEPENDS ${SPV_FILES})

add_executable(essai_vulkan src/essai_vulkan.cpp)
target_link_libraries(essai_vulkan PRIVATE volk)
target_compile_definitions(essai_vulkan PRIVATE SPV_DIR="${SPV_DIR}")
target_compile_options(essai_vulkan PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
target_link_options(essai_vulkan PRIVATE -static)
add_dependencies(essai_vulkan shaders)
