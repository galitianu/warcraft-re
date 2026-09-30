cmake_minimum_required(VERSION 3.20)
project(warcraft_re VERSION 0.0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
include(CTest)

# A fresh, dependency-free build. Consulted the archived sim/CMakeLists.txt for
# its standalone static-library boundary; no archived code or flags imported.
add_library(wc3world STATIC src/core/World.cpp)
target_include_directories(wc3world PUBLIC src)
target_compile_options(wc3world PUBLIC
  $<$<CXX_COMPILER_ID:AppleClang,Clang,GNU>:-Wall;-Wextra;-Wpedantic;-ffp-contract=off>)

add_library(movement_cases STATIC tools/wc3test/Cases.cpp)
target_include_directories(movement_cases PUBLIC tools/wc3test)
target_link_libraries(movement_cases PUBLIC wc3world)

execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
  OUTPUT_VARIABLE BUILD_GIT_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE)
execute_process(COMMAND git status --porcelain --untracked-files=normal
  WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
  OUTPUT_VARIABLE BUILD_GIT_STATUS OUTPUT_STRIP_TRAILING_WHITESPACE)
if(BUILD_GIT_STATUS STREQUAL "")
  set(BUILD_GIT_DIRTY false)
else()
  set(BUILD_GIT_DIRTY true)
endif()
# Exact source identity even for an uncommitted build. Hash only build/runner
# sources, not generated evidence (which would create a self-reference).
set(BUILD_SOURCE_INPUT "")
foreach(path CMakeLists.txt src/core/World.h src/core/World.cpp src/core/Random.h
    tools/wc3test/Cases.h tools/wc3test/Cases.cpp tools/wc3test/main.cpp
    tools/wc3test/BuildIdentity.h.in)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${path}")
  file(SHA256 "${CMAKE_SOURCE_DIR}/${path}" digest)
  string(APPEND BUILD_SOURCE_INPUT "${path}:${digest}\n")
endforeach()
string(SHA256 BUILD_SOURCE_SHA256 "${BUILD_SOURCE_INPUT}")
configure_file(tools/wc3test/BuildIdentity.h.in generated/BuildIdentity.h @ONLY)

add_executable(wc3test tools/wc3test/main.cpp)
target_include_directories(wc3test PRIVATE "${CMAKE_BINARY_DIR}/generated")
target_link_libraries(wc3test PRIVATE movement_cases)
if(BUILD_TESTING)
  add_executable(world_tests tests/world_tests.cpp)
  target_link_libraries(world_tests PRIVATE movement_cases)
  add_test(NAME world_invariants COMMAND world_tests)
endif()
