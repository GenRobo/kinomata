#include <iostream>
#include <sstream>

#include "zenoh.hxx"
using namespace zenoh;

int main(int argc, char** argv)
{
  std::cout << "Launched App\n";

  init_log_from_env_or("error");

  Config config = Config::create_default();

  // enable SHM
  config.insert_json5("transport/shared_memory/enabled", "true");

  auto session = Session::open(std::move(config));

  std::ostringstream oss;
  for(int i = 1; i < argc; ++i)
  {
    oss << " " << argv[i];
  }

  const std::string msg = std::format("Hello Zenoh:{}", oss.str());
  session.put("demo/example/simple", std::move(msg));

  std::cout << "Exiting App\n";
}

