#include <iostream>

#include "zenoh_service.h"
#include "world_sim_api.hpp"
#include "common.hpp"
#include "packet_tests.hpp"

int main(int argc, char** argv)
{
  std::cout << "Launched App\n";
  run_packet_self_checks();

  api_provider_t api_provider(std::make_unique<world_sim_api_t>());
  zenoh_service_t::init(api_provider);

  std::cout << "Ready!" << std::endl;
  std::cout << "Press Ctrl+C to stop." << std::endl;
  while(true)
  {
    looper_manager::update();

    cv::waitKey(1);
  }

  std::cout << "Exiting App\n";
}
