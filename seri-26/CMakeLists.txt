cmake_minimum_required(VERSION 3.26)
project(seri26 VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 26)
set(CMAKE_CXX_STANDARD_REQUIRED OFF)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(seri26 INTERFACE)
target_include_directories(seri26 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

if (CMAKE_CXX_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    target_compile_options(seri26 INTERFACE -std=c++2b)
endif()

enable_testing()

add_executable(seri26_tests tests/serializer_tests.cpp)
target_link_libraries(seri26_tests PRIVATE seri26)

add_test(NAME seri26.tests COMMAND seri26_tests)
