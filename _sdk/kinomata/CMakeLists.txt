cmake_minimum_required(VERSION 3.20)
cmake_policy(SET CMP0135 NEW)

project(kinomata_app
  LANGUAGES CXX
  VERSION 0.1
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# setup Debug flags
if(MSVC)
  add_compile_options("$<$<CONFIG:Debug>:/RTC1;/sdl>")
else()
  set(DEBUG_FLAGS "-fsanitize=address,undefined" "-fno-omit-frame-pointer")
  set(DEBUG_LINK_FLAGS "-fsanitize=address,undefined")
  add_compile_options("$<$<CONFIG:Debug>:${DEBUG_FLAGS}>")
  add_link_options("$<$<CONFIG:Debug>:${DEBUG_LINK_FLAGS}>")
endif()

add_subdirectory(deps)
add_subdirectory(src)
