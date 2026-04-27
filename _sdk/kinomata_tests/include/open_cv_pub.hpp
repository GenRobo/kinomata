#pragma once

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
    label_pos_{cv::Point(8, std::max(8, static_cast<int>(height_ / 2)))},
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
