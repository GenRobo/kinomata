#include <iostream>
#include <sstream>
#include <vector>
#include <memory>
#include <mutex>

#include <opencv2/opencv.hpp>
#include "zenoh.hxx"

void show_img_window(const cv::Mat& image)
{
  // open cv window
  cv::imshow("No-Input Test", image);

  std::cout << "Press any key in the image window to exit..." << std::endl;
  cv::waitKey(0);
}

// OpenCV PUB/SUB test
class open_cv_pub
{
  static inline cv::RNG rng{12345};

  zenoh::Publisher pub_;
  uint16_t width_;
  uint16_t height_;
  uint16_t index_;
  cv::Mat frame_;
  cv::Point pos_;

public:
  open_cv_pub(const zenoh::Session& session, const uint16_t index,
    const std::string_view key, const uint16_t width, const uint16_t height) :
    pub_{session.declare_publisher(key)},
    width_{width}, height_{height},
    pos_{0, height/2},
    frame_{cv::Mat::zeros(height, width, CV_8UC3)},
    index_{index}
    {}

  void update()
  {
    cv::Scalar color(rng.next() & 255, rng.next() & 255, rng.next() & 255);
    frame_.setTo(color); // clear
    // cv::putText (InputOutputArray img, const String &text, Point org, int fontFace, double fontScale, Scalar color, int thickness=1, int lineType=LINE_8, bool bottomLeftOrigin=false)
    cv::putText(frame_, std::to_string(index_), pos_, 
      cv::FONT_HERSHEY_SIMPLEX, 1, cv::Scalar(0, 255, 0), 2);

    // cv::Mat is an Open CV smart pointer.
    // cv::Mat::data is a uint16_t* pointer to pixel data array.

    // Wrap the cv::Mat in a lambda deleter
    // to ensure the reference count is held until Zenoh releases the bytes.
    auto deleter = [keep_alive = frame_](uint8_t*) mutable {
        // The capture 'keep_alive' is destroyed here,
        // decrementing the cv::Mat ref count.
    };

    // map raw data into Zenoh bytes without copying
    auto payload = zenoh::Bytes(frame_.data, frame_.total() * frame_.elemSize(), deleter);
    pub_.put(std::move(payload));
  }
};

static std::vector<std::shared_ptr<open_cv_pub>> Publishers;
static std::vector<std::shared_ptr<open_cv_pub>> PubsToAdd;
std::mutex PubMutex;

void update_stream(zenoh::Session& session,
  const uint16_t width, const uint16_t height, const uint16_t count)
{
  PubsToAdd.clear();
  PubsToAdd.reserve(count);
  for(uint16_t i = 0; i < count; ++i)
  {
    PubsToAdd.push_back(std::make_shared<open_cv_pub>(session, i+1,
      std::format("sim/stream/{}", i+1),
      width,
      height));
  }

  std::cout << "Streaming at " << width << "x" << height << "...\n";
  std::cout << "Press Ctrl+C to stop." << std::endl;
}

int main(int argc, char** argv)
{
  std::cout << "Launched App\n";

  // init Zenoh
  zenoh::init_log_from_env_or("error");
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
      if (payload.size() == 6) // 6 bytes for 3 uint16_t
      {
        uint16_t params[3];
        auto reader = payload.reader();
        reader.read(reinterpret_cast<uint8_t*>(params), 6);

        uint16_t w = params[0];
        uint16_t h = params[1];
        uint16_t count = params[2];

        std::cout << "Received Req for " << count
          << " images of size [" << w << "x" << h << "]" << std::endl;

        {
          std::lock_guard lk(PubMutex);
          // will be invoked as part of this zenoh callback thread (not the main thread)
          update_stream(session, w, h, count);
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

  // Pub stream test
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

