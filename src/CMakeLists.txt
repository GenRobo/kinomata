file(GLOB_RECURSE KINOMATA_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp"
)
add_executable(kinomata ${KINOMATA_SOURCES})

set_property(TARGET kinomata PROPERTY INTERPROCEDURAL_OPTIMIZATION
  "$<CONFIG:Release,RelWithDebInfo,MinSizeRel>"
)

# Debug -> 3, RelWithDebInfo -> 2, else -> 1
target_compile_definitions(kinomata PRIVATE
  LOG_LEVEL=$<IF:$<CONFIG:Debug>,3,$<IF:$<CONFIG:RelWithDebInfo>,2,1>>
)

find_package(OpenCV REQUIRED)
target_link_libraries(kinomata PRIVATE ${OpenCV_LIBS})
target_include_directories(kinomata PRIVATE ${OpenCV_INCLUDE_DIRS})

target_link_libraries(kinomata PRIVATE zenohcxx::zenohc)
copy_dlls(kinomata)
