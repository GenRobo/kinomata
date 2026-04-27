#pragma once

#include <memory>
#include "world_sim_api_interface.h"

class api_provider_t
{
  std::unique_ptr<world_sim_api_interface> world_sim_api_owned_;
  world_sim_api_interface* world_sim_api_;

public:
  api_provider_t(std::unique_ptr<world_sim_api_interface> world_sim_api) :
    world_sim_api_owned_(std::move(world_sim_api)),
    world_sim_api_(world_sim_api_owned_.get())
  {}

  api_provider_t(world_sim_api_interface* world_sim_api) :
    world_sim_api_(world_sim_api) // non-owning
  {}

  inline const world_sim_api_interface& get_world_sim_api() const { return *world_sim_api_; }
  inline world_sim_api_interface& get_world_sim_api() { return *world_sim_api_; }
};
