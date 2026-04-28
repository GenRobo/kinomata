#include "zenoh_service.h"

#include <iostream>
#include "adaptors.hpp"

inline void log(std::string_view msg)
{
  std::cout << "[Info]: " << msg << "\n";
}

inline void log_warn(std::string_view msg)
{
  std::cout << "[Warning]: " << msg << "\n";
}

inline void log_err(std::string_view msg)
{
  std::cerr << "[Error]: " << msg << "\n";
}

zenoh::Session create_session()
{
  // init Zenoh
  zc_init_log_from_env_or("error");
  auto config = zenoh::Config::create_default();
  config.insert_json5("transport/shared_memory/enabled", "true");
  return zenoh::Session::open(std::move(config));
}

zenoh_service_t::zenoh_service_t(api_provider_t& api_provider) :
  session_{create_session()},
  api_provider_{api_provider}
{
  bind_queryables();
}

void zenoh_service_t::bind_queryables()
{
  static thread_local const std::string KeySim = "sim";

  bind_qr(KeySim, "spawn/object", sim_spawn_object);
  bind_qr(KeySim, "stream", sim_start_stream);

  bind_qr_0(KeySim, "stream/end", [this](){
    return api_provider_.get_world_sim_api().end_stream();
  });
}
