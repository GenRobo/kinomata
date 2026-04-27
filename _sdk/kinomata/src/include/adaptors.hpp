#include "types.h"
#include "packet.hpp"

bool spawn_object(const std::string_view key_expr,
  const zenoh::Bytes& payload, const zenoh::Session& session,
  api_provider_t& api)
{
  PKT_BEGIN(data_t)
    uint32_t version;
    char name[MAX_NAME_LEN];
    uint32_t tag_count;
    char tags[MAX_TAG_COUNT][MAX_TAG_LEN];
    pose_t pose;
    vec3_t scale;
  PKT_END

  auto data = pkt_as<data_t>(payload);
  if(!data) return false;
  
  if(data->version != 1) return false;

  std::string_view name = pkt_name_str(data->name);

  std::vector<std::string_view> tags;
  tags.reserve(data->tag_count);
  for(uint16_t i = 0; i < data->tag_count; ++i)
  {
    tags.emplace_back(pkt_tag_str(data->tags[i]));
  }

  const pose_t& pose = data->pose;
  const vec3_t& scale = data->scale;

  return api.get_world_sim_api().sim_spawn_object(name, tags, pose, scale);
}

void start_stream(const std::string_view key_expr,
  const zenoh::Bytes& payload, const zenoh::Session& session,
  api_provider_t& api)
{
  PKT_BEGIN(data_t)
    uint16_t width;
    uint16_t height;
    uint16_t count;
    float font_scale;
    uint16_t font_thickness;
  PKT_END

  auto data = pkt_as<data_t>(payload);
  if(!data) return;

  api.get_world_sim_api().start_stream(key_expr, session,
    data->width, data->height, data->count, data->font_scale, data->font_thickness);
}
