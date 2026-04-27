#pragma once

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
