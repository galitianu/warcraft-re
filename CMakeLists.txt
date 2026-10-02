cmake_minimum_required(VERSION 3.20)
project(warcraft_re VERSION 0.0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
include(CTest)

# A fresh, dependency-free build. Consulted the archived sim/CMakeLists.txt for
# its standalone static-library boundary; no archived code or flags imported.
add_library(wc3world STATIC src/core/World.cpp src/core/SoftFloat.cpp)
target_include_directories(wc3world PUBLIC src)
target_compile_options(wc3world PUBLIC
  $<$<CXX_COMPILER_ID:AppleClang,Clang,GNU>:-Wall;-Wextra;-Wpedantic;-fno-fast-math;-ffp-contract=off>
  $<$<CXX_COMPILER_ID:MSVC>:/W4;/fp:strict>)
# Lets identity report contraction from the flags actually applied.
target_compile_definitions(wc3world PUBLIC
  $<$<CXX_COMPILER_ID:AppleClang,Clang,GNU,MSVC>:WC3_FP_CONTRACT_OFF>)

add_library(movement_cases STATIC tools/wc3test/Cases.cpp tools/wc3test/Canonical.cpp
  tools/wc3test/Scenario.cpp)
target_include_directories(movement_cases PUBLIC tools/wc3test)
target_link_libraries(movement_cases PUBLIC wc3world)

# Without a readable checkout, revision and dirty state are unknown, not clean.
execute_process(COMMAND git rev-parse --verify HEAD WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
  RESULT_VARIABLE git_commit_result ERROR_QUIET
  OUTPUT_VARIABLE BUILD_GIT_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE)
execute_process(COMMAND git status --porcelain --untracked-files=normal
  WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}" RESULT_VARIABLE git_status_result ERROR_QUIET
  OUTPUT_VARIABLE BUILD_GIT_STATUS OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT git_commit_result EQUAL 0 OR NOT git_status_result EQUAL 0
    OR NOT BUILD_GIT_COMMIT MATCHES "^[0-9a-f]+$")
  message(WARNING "git revision unavailable; identity records it as null")
  set(BUILD_GIT_COMMIT_JSON null)
  set(BUILD_GIT_DIRTY null)
else()
  set(BUILD_GIT_COMMIT_JSON "\"${BUILD_GIT_COMMIT}\"")
  if(BUILD_GIT_STATUS STREQUAL "")
    set(BUILD_GIT_DIRTY false)
  else()
    set(BUILD_GIT_DIRTY true)
  endif()
endif()
# Exact source identity even for an uncommitted build. Hash only build/runner
# sources, not generated evidence (which would create a self-reference).
set(BUILD_SOURCE_INPUT "")
foreach(path CMakeLists.txt src/core/World.h src/core/World.cpp src/core/Random.h
    src/core/SoftFloat.h src/core/SoftFloat.cpp
    tools/wc3test/Cases.h tools/wc3test/Cases.cpp tools/wc3test/main.cpp
    tools/wc3test/Canonical.h tools/wc3test/Canonical.cpp
    tools/wc3test/Scenario.h tools/wc3test/Scenario.cpp
    tools/wc3test/BuildIdentity.h.in tools/wc3states/main.cpp tools/math_scope.cpp)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${path}")
  file(SHA256 "${CMAKE_SOURCE_DIR}/${path}" digest)
  string(APPEND BUILD_SOURCE_INPUT "${path}:${digest}\n")
endforeach()
string(SHA256 BUILD_SOURCE_SHA256 "${BUILD_SOURCE_INPUT}")
configure_file(tools/wc3test/BuildIdentity.h.in generated/BuildIdentity.h @ONLY)

add_executable(wc3test tools/wc3test/main.cpp)
target_include_directories(wc3test PRIVATE "${CMAKE_BINARY_DIR}/generated")
target_link_libraries(wc3test PRIVATE movement_cases)
add_executable(wc3states tools/wc3states/main.cpp)
target_link_libraries(wc3states PRIVATE wc3world)
add_executable(math_scope tools/math_scope.cpp)
target_link_libraries(math_scope PRIVATE wc3world)
if(BUILD_TESTING)
  add_executable(world_tests tests/world_tests.cpp)
  target_link_libraries(world_tests PRIVATE movement_cases)
  add_test(NAME world_invariants COMMAND world_tests)
  add_executable(scenario_tests tests/scenario_tests.cpp)
  target_link_libraries(scenario_tests PRIVATE movement_cases)
  add_test(NAME scenario_v1 COMMAND scenario_tests "${CMAKE_SOURCE_DIR}/scenarios")
  # Bit-exact footman-v4 gate against the committed WC3 fixtures and captures.
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(NAME footman_v4_wc3 COMMAND Python3::Interpreter
    "${CMAKE_SOURCE_DIR}/tools/run_footman_v4.py" --runner $<TARGET_FILE:wc3test>
    --states $<TARGET_FILE:wc3states> --out "${CMAKE_BINARY_DIR}/footman-v4-test"
    --reports "${CMAKE_BINARY_DIR}/footman-v4-test/reports")
  set_tests_properties(world_invariants scenario_v1 footman_v4_wc3 PROPERTIES TIMEOUT 180)
endif()
