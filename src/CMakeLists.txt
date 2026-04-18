add_executable(kinomata main.cpp)

set_property(TARGET kinomata PROPERTY INTERPROCEDURAL_OPTIMIZATION
  "$<CONFIG:Release,RelWithDebInfo,MinSizeRel>"
)

# Debug -> 3, RelWithDebInfo -> 2, else -> 1
target_compile_definitions(kinomata PRIVATE
  LOG_LEVEL=$<IF:$<CONFIG:Debug>,3,$<IF:$<CONFIG:RelWithDebInfo>,2,1>>
)

target_link_libraries(kinomata PRIVATE zenohcxx::zenohc)
copy_dlls(kinomata)

