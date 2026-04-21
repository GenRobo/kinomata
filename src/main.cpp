#include <algorithm>
#include <iostream>
#include <sstream>
#include <format>
#include <vector>
#include <memory>
#include <mutex>

#include <opencv2/opencv.hpp>
#include "zenoh/api/session.hxx"

// Open CV publisher class that generates random color frames with a label and publishes them to Zenoh.
// CV_8UC3 format is used for the image data, each pixel is represented by 3 unsigned char values (BGR format).
class open_cv_pub
{
  static inline cv::RNG rng{12345};

  zenoh::Publisher pub_;
  uint16_t width_;
  uint16_t height_;
  size_t payload_size_;
  std::vector<uint8_t> payload_bytes_;
  cv::Mat frame_;
  uint16_t index_;
  double font_scale_;
  int font_thickness_;
  cv::Point label_pos_;
  std::string label_;

public:
  open_cv_pub(const zenoh::Session& session, const uint16_t index,
    const std::string_view key, const uint16_t width, const uint16_t height,
    const double font_scale, const uint16_t font_thickness) :
    pub_{session.declare_publisher(key)},
    width_{width}, height_{height},
    payload_size_{static_cast<size_t>(width * height) * CV_ELEM_SIZE(CV_8UC3)},
    payload_bytes_(payload_size_),
    frame_(height_, width_, CV_8UC3, payload_bytes_.data()), // wrap the payload bytes as OpenCV Mat (zero-copy)
    index_{index},
    font_scale_{font_scale},
    font_thickness_{font_thickness},
    label_pos_{cv::Point(8, std::min(8, static_cast<int>(height_ / 2)))},
    label_{std::to_string(index_)}
    {}

  void update()
  { 
    // clear frame with random color
    cv::Scalar color(rng.next() & 255, rng.next() & 255, rng.next() & 255);
    frame_.setTo(color);

    cv::putText(frame_, label_, label_pos_,
      cv::FONT_HERSHEY_SIMPLEX, font_scale_, cv::Scalar(0, 255, 0), font_thickness_);

    pub_.put(zenoh::Bytes(payload_bytes_)); // publish the frame as bytes (zero-copy)
  }
};

static std::vector<std::shared_ptr<open_cv_pub>> Publishers;
static std::vector<std::shared_ptr<open_cv_pub>> PubsToAdd;
std::mutex PubMutex;

void update_stream(zenoh::Session& session,
  const uint16_t width, const uint16_t height, const uint16_t count,
  const double font_scale, const uint16_t font_thickness)
{
  PubsToAdd.clear();
  PubsToAdd.reserve(count);
  for(uint16_t i = 0; i < count; ++i)
  {
    PubsToAdd.push_back(std::make_shared<open_cv_pub>(session, i+1,
      std::format("sim/stream/{}", i+1),
      width,
      height,
      font_scale,
      font_thickness));
  }

  std::cout << "Streaming at " << width << "x" << height << "...\n";
  std::cout << "Press Ctrl+C to stop." << std::endl;
}

int main(int argc, char** argv)
{
  std::cout << "Launched App\n";

  // init Zenoh
  zc_init_log_from_env_or("error");
  auto config = zenoh::Config::create_default();
  config.insert_json5("transport/shared_memory/enabled", "true");
  auto session = zenoh::Session::open(std::move(config));

  // simple msg test
  std::ostringstream oss;
  for(int i = 1; i < argc; ++i) oss << " " << argv[i];
  const std::string msg = std::format("Hello Zenoh:{}", oss.str());
  session.put("example/simple", std::move(msg));

  // REQ/RSP example
  // Register a queryable 
  auto queryable = session.declare_queryable("sim/stream", [&](const zenoh::Query& query) {
    auto payload_opt = query.get_payload();
    if (payload_opt.has_value()) // parse payload
    {
      const zenoh::Bytes& payload = payload_opt->get();
      if (payload.size() == 10) // 10 bytes for 5 uint16_t
      {
        uint16_t params[5];
        auto reader = payload.reader();
        reader.read(reinterpret_cast<uint8_t*>(params), 10);

        uint16_t w = params[0];
        uint16_t h = params[1];
        uint16_t count = params[2];
        double font_scale = params[3] / 100.0; // convert percentage to scale factor
        uint16_t font_thickness = params[4];

        std::cout << "Received Req for " << count
          << " images of size [" << w << "x" << h << "]" << std::endl;

        {
          std::lock_guard lk(PubMutex);
          // will be invoked as part of this zenoh callback thread (not the main thread)
          update_stream(session, w, h, count, font_scale, font_thickness);
        }

        // Send an "OK" confirmation back to requester
        query.reply("sim/stream", "OK");
        return;
      }

      std::cerr << "Received incompatible config payload of size: " 
        << payload.size()
        << std::endl;
    }
  },
  [](){std::cerr << "Failed query" << std::endl;}
  );

  // OpenCV PUB/SUB test
  std::cout << "Ready to stream!" << std::endl;
  while(true)
  {
    for(auto& pub : Publishers)
      pub->update();

    if(PubsToAdd.size() > 0)
    {
      Publishers.clear();

      {
        std::lock_guard lk(PubMutex);
        Publishers.append_range(PubsToAdd);
        PubsToAdd.clear();
      }

      std::cout << "Updated stream pubs" << std::endl;
    }

    cv::waitKey(16); // wait for 16 ms to simulate 60 fps
  }

  std::cout << "Exiting App\n";
}
