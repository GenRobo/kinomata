#pragma once

#include <iostream>
#include <format>
#include <algorithm>
#include <vector>
#include <memory>
#include <mutex>
#include <format>

#include "open_cv_pub.hpp"
#include "common.hpp"

class world_sim_api_t : public world_sim_api_interface
{
public:
  virtual void start_stream(std::string_view topic_main, const zenoh::Session& session,
    const uint16_t width, const uint16_t height, const uint16_t count,
    const float font_scale, const uint16_t font_thickness) override
  {
    looper_manager::clear(count);
    for(uint16_t i = 0; i < count; ++i)
    {
      auto pub_ptr = std::make_shared<open_cv_pub>(session, i+1,
        std::format("{}/{}", topic_main, i+1),
        width,
        height,
        font_scale,
        font_thickness);

      looper_manager::add([pub_ptr]() { pub_ptr->update(); });
    }

    std::cout << "Added " << count << " new " << width << "x" << height << " streamers...\n";
  }

  virtual void end_stream() override
  {
    std::cout << "Removed all streamers...\n";

    looper_manager::clear();
  }

  virtual bool spawn_object(std::string_view name, 
   std::vector<std::string_view> tags,
   const pose_t& pose, const vec3_t& scale) override
 {
   const std::string msg = std::format("Spawning object named {} at ({},{},{}) rotated at ({},{},{},{}) scaled to ({},{},{}), with tags:",
     name, pose.pos.x, pose.pos.y, pose.pos.z, pose.rot.x, pose.rot.y, pose.rot.z, pose.rot.w, scale.x, scale.y, scale.z);

   std::cout << msg << "\n";
   for(auto& tag : tags) std:: cout << tag << ",";
   std::cout << std::endl;

   return true;
 }
};
