#pragma once

#include "zenoh/api/bytes.hxx"

enum class e_color_space : uint16_t
{
  UNKNOWN = 0,
  GRAY = 1,
  RGB = 2,
  BGR = 3,
  RGBA = 4,
  BGRA = 5
};

enum class e_data_type : uint16_t
{
  UNKNOWN = 0,
  UINT8 = 1,
  UINT16 = 2,
  UINT32 = 3,
  UINT64 = 4,
  INT8 = 5,
  INT16 = 6,
  INT32 = 7,
  INT64 = 8,
  FLOAT16 = 9,
  FLOAT32 = 10,
  FLOAT64 = 11,
  BOOL = 12
};

struct vec3_t
{
  float x, y, z;
};

struct quat_t
{
  float x, y, z, w;
};

struct pose_t
{
  vec3_t pos;
  quat_t rot;
};

struct image_metadata_t
{
  uint16_t width;
  uint16_t height;
  uint16_t channel_count;
  e_color_space color_space;
  e_data_type data_type;
};
