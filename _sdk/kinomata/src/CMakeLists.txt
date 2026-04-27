file(GLOB_RECURSE KINOMATA_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_LIST_DIR}/internal/*.cpp"
)
add_library(kinomata ${KINOMATA_SOURCES})

target_include_directories(kinomata PUBLIC
  "${CMAKE_CURRENT_LIST_DIR}/include"
)

set_property(TARGET kinomata PROPERTY INTERPROCEDURAL_OPTIMIZATION
  "$<CONFIG:Release,RelWithDebInfo,MinSizeRel>"
)

# Debug -> 3, RelWithDebInfo -> 2, else -> 1
target_compile_definitions(kinomata PRIVATE
  LOG_LEVEL=$<IF:$<CONFIG:Debug>,3,$<IF:$<CONFIG:RelWithDebInfo>,2,1>>
)

target_link_libraries(kinomata PUBLIC zenohcxx::zenohc)
#copy_dlls(kinomata)

install(TARGETS kinomata
  EXPORT kinomata_targets
  ARCHIVE DESTINATION lib/$<CONFIG>
  LIBRARY DESTINATION lib/$<CONFIG>
  RUNTIME DESTINATION bin/$<CONFIG>
  COMPONENT KinomataRuntime
)

install(DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/include/"
  DESTINATION include/
  COMPONENT KinomataDevelopment
)
