include(FetchContent)

add_subdirectory(zenohc)
FetchContent_Declare(
  zenohcxx
  GIT_REPOSITORY https://github.com/eclipse-zenoh/zenoh-cpp.git
  GIT_TAG        1.9.0 # matches zenohc binaries release
)
set(ZENOHCXX_ZENOHC ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(zenohcxx)
# CMake will automatically create ${lowercaseName_SOURCE_DIR}
# We include the helper file here, so it'll be globally available to the parent project.
include(${zenohcxx_SOURCE_DIR}/cmake/helpers.cmake)

