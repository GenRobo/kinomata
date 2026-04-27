#pragma once

#include <cstdint>
#include <cstring>
#include <string_view>
#include "zenoh/api/bytes.hxx"

constexpr uint16_t MAX_NAME_LEN = 32;
constexpr uint16_t MAX_TAG_LEN = 16;
constexpr uint16_t MAX_TAG_COUNT = 8;

template <typename T>
zenoh::Bytes serialize(const T& value);

// --- cast payload → struct (safe size check)
template <typename T>
inline std::optional<T> pkt_as(const zenoh::Bytes& payload)
{
  if(payload.size() == sizeof(T))
  {
    T data;
    auto reader = payload.reader();
    reader.read(reinterpret_cast<uint8_t*>(&data), payload.size()); // uint8_t = byte

    return data;
  }

  return std::nullopt;
}

// --- fixed-size string → string_view
inline std::string_view pkt_str(const char* buf, size_t max)
{
  return std::string_view(buf, strnlen(buf, max));
}

inline std::string_view pkt_name_str(const char* buf)
{
  return pkt_str(buf, MAX_NAME_LEN);
}

inline std::string_view pkt_tag_str(const char* buf)
{
  return pkt_str(buf, MAX_TAG_LEN);
}

// --- packing macros for "schema structs"

#define PKT_BEGIN(name) \
  _Pragma("pack(push, 1)") \
  struct name \
  {

#define PKT_END \
  }; \
  _Pragma("pack(pop)")
