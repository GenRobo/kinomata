#include <iostream>
#include <sstream>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <string_view>
#include <vector>
#include <opencv2/opencv.hpp>

#include "zenoh_service.h"
#include "world_sim_api.hpp"
#include "common.hpp"

void run_packet_self_checks()
{
  if(serialize<bool>(true).as_vector() != std::vector<uint8_t>{1})
  {
    throw std::runtime_error("serialize<bool>(true) did not produce a one-byte true payload");
  }

  if(serialize<bool>(false).as_vector() != std::vector<uint8_t>{0})
  {
    throw std::runtime_error("serialize<bool>(false) did not produce a one-byte false payload");
  }

  PKT_BEGIN(spawn_payload_t)
    uint32_t version;
    char name[MAX_NAME_LEN];
    uint32_t tag_count;
    char tags[MAX_TAG_COUNT][MAX_TAG_LEN];
    pose_t pose;
    vec3_t scale;
  PKT_END

  pose_t pose{{1.15f, 450.0f, 2000.567f}, {0.25f, 0.1f, 0.2f, 1.0f}};
  vec3_t scale{1.0f, 500.0f, 1.0f};
  std::vector<std::string_view> tags{"dynamic", "visible"};

  spawn_payload_t expected{};
  expected.version = 1;
  std::strncpy(expected.name, "cube", MAX_NAME_LEN - 1);
  expected.tag_count = static_cast<uint32_t>(tags.size());
  for(size_t i = 0; i < tags.size(); ++i)
  {
    std::strncpy(expected.tags[i], tags[i].data(), MAX_TAG_LEN - 1);
  }
  expected.pose = pose;
  expected.scale = scale;

  const auto schema_payload = pkt::pack(
    pkt::schema(
      pkt::u32,
      pkt::fixed_str<MAX_NAME_LEN>{},
      pkt::fixed_str_array<MAX_TAG_COUNT, MAX_TAG_LEN>{},
      pkt::pod<pose_t>{},
      pkt::pod<vec3_t>{}
    ),
    1u,
    std::string_view("cube"),
    tags,
    pose,
    scale
  );

  if(schema_payload.as_vector() != serialize(expected).as_vector())
  {
    throw std::runtime_error("C++ packet schema output did not match the spawn-object wire layout");
  }
}

int main(int argc, char** argv)
{
  std::cout << "Launched App\n";
  run_packet_self_checks();

  api_provider_t api_provider(std::make_unique<world_sim_api_t>());
  zenoh_service_t zenoh_service(api_provider);

  std::cout << "Ready!" << std::endl;
  std::cout << "Press Ctrl+C to stop." << std::endl;
  while(true)
  {
    looper_manager::update();

    cv::waitKey(1);
  }

  std::cout << "Exiting App\n";
}
