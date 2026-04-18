include(FetchContent)

# release 1.9.0
# Platform Detection & Resource Mapping
if(APPLE) # macOS ARM64
  set(ZENOHC_URL "https://github.com/eclipse-zenoh/zenoh-c/releases/download/1.9.0/zenoh-c-1.9.0-aarch64-apple-darwin-standalone.zip")
  set(ZENOHC_HASH "SHA256=9cc79fa926f86e7d9757666c9afaf73007e4e0799aa59f7bdf77226f40dd2ff3")
  set(LIB_REL_PATH "lib/libzenohc.a")
  set(INCLUDE_REL_PATH "include")
elseif(WIN32) # Win x64
  set(ZENOHC_URL "https://github.com/eclipse-zenoh/zenoh-c/releases/download/1.9.0/zenoh-c-1.9.0-x86_64-pc-windows-msvc-standalone.zip")
  set(ZENOHC_HASH "SHA256=ebaa3c1ed303cf42c5af666b750da761c16d158f698cf17e5e8e0b4bd5524442")
  set(LIB_REL_PATH "lib/zenohc.lib")
  set(INCLUDE_REL_PATH "include")
elseif(UNIX AND NOT APPLE) # Debian x64
  set(ZENOHC_URL "https://github.com/eclipse-zenoh/zenoh-c/releases/download/1.9.0/libzenohc-1.9.0-x86_64-unknown-linux-gnu-debian.zip")
  set(ZENOHC_HASH "SHA256=afa6bfd2c6867ee0301d8d578be4a6a9f34dab3c132cbefc1c4cb4140ff92f1b")
  set(LIB_REL_PATH "usr/lib/x86_64-linux-gnu/libzenohc.a")
  set(INCLUDE_REL_PATH "usr/include")
endif()

# Download and Extract
FetchContent_Declare(
  zenohc_bin
  URL      ${ZENOHC_URL}
  URL_HASH ${ZENOHC_HASH}
)
FetchContent_MakeAvailable(zenohc_bin)

# Create the Static Target
add_library(zenohc_static STATIC IMPORTED GLOBAL)
set_target_properties(zenohc_static PROPERTIES
  IMPORTED_LOCATION "${zenohc_bin_SOURCE_DIR}/${LIB_REL_PATH}"
  INTERFACE_INCLUDE_DIRECTORIES "${zenohc_bin_SOURCE_DIR}/${INCLUDE_REL_PATH}"
)

# Zenoh-C static libs need system math/network libs to link properly
if(APPLE)
  target_link_libraries(zenohc_static INTERFACE "-framework Foundation" "-framework Security")
elseif(WIN32)
  target_link_libraries(zenohc_static INTERFACE "ws2_32" "crypt32" "bcrypt" "userenv" "ntdll" "iphlpapi")
elseif(UNIX)
  target_link_libraries(zenohc_static INTERFACE "rt" "pthread" "m" "dl")
endif()

# zenoh-cpp looks for zenohc::lib, so we provide it
add_library(zenohc::lib ALIAS zenohc_static)
add_library(zenohc::static ALIAS zenohc_static)

