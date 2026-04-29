cmake_minimum_required(VERSION 3.20)
cmake_policy(SET CMP0135 NEW)

project(kinomata_tests
  LANGUAGES CXX
  VERSION 0.1
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# setup Debug flags
if(MSVC)
  add_compile_options("$<$<CONFIG:Debug>:/RTC1;/sdl>")
  add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
else()
  set(DEBUG_FLAGS "-fsanitize=address,undefined" "-fno-omit-frame-pointer")
  set(DEBUG_LINK_FLAGS "-fsanitize=address,undefined")
  add_compile_options("$<$<CONFIG:Debug>:${DEBUG_FLAGS}>")
  add_link_options("$<$<CONFIG:Debug>:${DEBUG_LINK_FLAGS}>")
endif()

add_executable(${PROJECT_NAME} 
  "${CMAKE_CURRENT_LIST_DIR}/main.cpp"
)

target_include_directories(${PROJECT_NAME} PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}/include"
)

set_property(TARGET ${PROJECT_NAME} PROPERTY INTERPROCEDURAL_OPTIMIZATION
  "$<CONFIG:Release,RelWithDebInfo,MinSizeRel>"
)

find_package(OpenCV REQUIRED)
target_link_libraries(kinomata_tests PUBLIC ${OpenCV_LIBS})
target_include_directories(kinomata_tests PUBLIC ${OpenCV_INCLUDE_DIRS})

get_filename_component(KINOMATA_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../kinomata"
    ABSOLUTE)
add_subdirectory("${KINOMATA_DIR}"
                 "${CMAKE_BINARY_DIR}/kinomata")

target_link_libraries(${PROJECT_NAME} PRIVATE
  kinomata
)

if(MSVC)
  copy_dlls(${PROJECT_NAME})
endif()
