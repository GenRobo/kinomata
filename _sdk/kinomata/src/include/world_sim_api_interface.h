#pragma once

#include <string_view>
#include "zenoh/api/session.hxx"
#include "types.h"

class world_sim_api_interface
{
public:
  world_sim_api_interface() = default;
  virtual ~world_sim_api_interface() = default;

  virtual bool start_stream(std::string_view topic_main, const zenoh::Session& session,
    const uint16_t width, const uint16_t height, const uint16_t count,
    const float font_scale, const uint16_t font_thickness) = 0;

  virtual bool end_stream() = 0;

  virtual bool spawn_object(std::string_view name, 
   std::vector<std::string_view> tags,
   const pose_t& pose, const vec3_t& scale) = 0;
};
