#pragma once

#include <algorithm>
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>
#include "zenoh/api/bytes.hxx"

constexpr uint16_t MAX_NAME_LEN = 32;
constexpr uint16_t MAX_TAG_LEN = 16;
constexpr uint16_t MAX_TAG_COUNT = 8;

namespace pkt
{
  namespace detail
  {
    static_assert(std::endian::native == std::endian::little,
      "Kinomata packet wire format is currently little-endian only");

    inline void append_bytes(std::vector<uint8_t>& out, const void* data, size_t size)
    {
      if(size == 0) return;
      const auto* bytes = static_cast<const uint8_t*>(data);
      out.insert(out.end(), bytes, bytes + size);
    }

    inline bool read_bytes(const std::vector<uint8_t>& bytes, size_t& offset, void* dst, size_t size)
    {
      if(offset > bytes.size() || size > bytes.size() - offset) return false;
      std::memcpy(dst, bytes.data() + offset, size);
      offset += size;
      return true;
    }

    inline std::string decode_fixed_str(const char* data, size_t size)
    {
      return std::string(data, strnlen(data, size));
    }

    template <size_t I = 0, typename SpecsTuple, typename ValuesTuple>
    bool decode_all(const SpecsTuple& specs, const std::vector<uint8_t>& bytes,
      size_t& offset, ValuesTuple& values)
    {
      if constexpr (I == std::tuple_size_v<SpecsTuple>)
      {
        return true;
      }
      else
      {
        auto value = std::get<I>(specs).decode(bytes, offset);
        if(!value) return false;

        std::get<I>(values) = std::move(*value);
        return decode_all<I + 1>(specs, bytes, offset, values);
      }
    }

    template <typename Schema, typename ValuesTuple, size_t... I>
    void encode_all(const Schema& schema, std::vector<uint8_t>& out, ValuesTuple&& values,
      std::index_sequence<I...>)
    {
      (std::get<I>(schema.specs).encode(out, std::get<I>(std::forward<ValuesTuple>(values))), ...);
    }
  }

  template <typename T>
  struct primitive_spec
  {
    using value_type = T;

    static_assert(std::is_arithmetic_v<T>, "primitive packet specs require arithmetic types");

    void encode(std::vector<uint8_t>& out, T value) const
    {
      if constexpr (std::is_same_v<T, bool>)
      {
        uint8_t byte = value ? 1 : 0;
        detail::append_bytes(out, &byte, sizeof(byte));
      }
      else
      {
        detail::append_bytes(out, &value, sizeof(T));
      }
    }

    std::optional<T> decode(const std::vector<uint8_t>& bytes, size_t& offset) const
    {
      if constexpr (std::is_same_v<T, bool>)
      {
        uint8_t byte = 0;
        if(!detail::read_bytes(bytes, offset, &byte, sizeof(byte))) return std::nullopt;
        return byte != 0;
      }
      else
      {
        T value{};
        if(!detail::read_bytes(bytes, offset, &value, sizeof(T))) return std::nullopt;
        return value;
      }
    }
  };

  inline constexpr primitive_spec<uint8_t> u8{};
  inline constexpr primitive_spec<uint16_t> u16{};
  inline constexpr primitive_spec<uint32_t> u32{};
  inline constexpr primitive_spec<uint64_t> u64{};

  inline constexpr primitive_spec<int8_t> i8{};
  inline constexpr primitive_spec<int16_t> i16{};
  inline constexpr primitive_spec<int32_t> i32{};
  inline constexpr primitive_spec<int64_t> i64{};

  inline constexpr primitive_spec<float> f32{};
  inline constexpr primitive_spec<double> f64{};
  inline constexpr primitive_spec<bool> boolean{};

  template <size_t Size>
  struct fixed_str
  {
    using value_type = std::string;

    static_assert(Size > 0, "fixed_str size must be at least 1");

    void encode(std::vector<uint8_t>& out, std::string_view value) const
    {
      std::array<char, Size> buf{};
      const size_t copy_size = std::min(value.size(), Size - 1);
      std::memcpy(buf.data(), value.data(), copy_size);
      detail::append_bytes(out, buf.data(), buf.size());
    }

    std::optional<std::string> decode(const std::vector<uint8_t>& bytes, size_t& offset) const
    {
      std::array<char, Size> buf{};
      if(!detail::read_bytes(bytes, offset, buf.data(), buf.size())) return std::nullopt;
      return detail::decode_fixed_str(buf.data(), buf.size());
    }
  };

  template <size_t MaxCount, size_t ElemSize>
  struct fixed_str_array
  {
    using value_type = std::vector<std::string>;

    static_assert(ElemSize > 0, "fixed_str_array element size must be at least 1");
    static_assert(MaxCount <= std::numeric_limits<uint32_t>::max(),
      "fixed_str_array max count must fit in uint32_t");

    template <typename Range>
    void encode(std::vector<uint8_t>& out, const Range& values) const
    {
      std::array<std::array<char, ElemSize>, MaxCount> buf{};
      uint32_t count = 0;

      for(const auto& value : values)
      {
        if(count == MaxCount) break;

        std::string_view str(value);
        const size_t copy_size = std::min(str.size(), ElemSize - 1);
        std::memcpy(buf[count].data(), str.data(), copy_size);
        ++count;
      }

      u32.encode(out, count);
      detail::append_bytes(out, buf.data(), MaxCount * ElemSize);
    }

    std::optional<std::vector<std::string>> decode(const std::vector<uint8_t>& bytes, size_t& offset) const
    {
      auto count = u32.decode(bytes, offset);
      if(!count || *count > MaxCount) return std::nullopt;

      std::array<std::array<char, ElemSize>, MaxCount> buf{};
      if(!detail::read_bytes(bytes, offset, buf.data(), MaxCount * ElemSize)) return std::nullopt;

      std::vector<std::string> values;
      values.reserve(*count);
      for(uint32_t i = 0; i < *count; ++i)
      {
        values.push_back(detail::decode_fixed_str(buf[i].data(), ElemSize));
      }

      return values;
    }
  };

  struct raw_bytes_spec
  {
    using value_type = std::vector<uint8_t>;

    void encode(std::vector<uint8_t>& out, const std::vector<uint8_t>& value) const
    {
      if(value.size() > std::numeric_limits<uint32_t>::max())
      {
        throw std::length_error("raw_bytes payload is too large");
      }
      u32.encode(out, static_cast<uint32_t>(value.size()));
      detail::append_bytes(out, value.data(), value.size());
    }

    void encode(std::vector<uint8_t>& out, std::string_view value) const
    {
      if(value.size() > std::numeric_limits<uint32_t>::max())
      {
        throw std::length_error("raw_bytes payload is too large");
      }
      u32.encode(out, static_cast<uint32_t>(value.size()));
      detail::append_bytes(out, value.data(), value.size());
    }

    std::optional<std::vector<uint8_t>> decode(const std::vector<uint8_t>& bytes, size_t& offset) const
    {
      auto size = u32.decode(bytes, offset);
      if(!size || *size > bytes.size() - offset) return std::nullopt;

      std::vector<uint8_t> value(*size);
      if(!detail::read_bytes(bytes, offset, value.data(), value.size())) return std::nullopt;
      return value;
    }
  };

  inline constexpr raw_bytes_spec raw_bytes{};

  template <typename T>
  struct pod
  {
    using value_type = T;

    static_assert(std::is_trivially_copyable_v<T>, "pod<T> requires T to be trivially copyable");

    void encode(std::vector<uint8_t>& out, const T& value) const
    {
      detail::append_bytes(out, &value, sizeof(T));
    }

    std::optional<T> decode(const std::vector<uint8_t>& bytes, size_t& offset) const
    {
      T value{};
      if(!detail::read_bytes(bytes, offset, &value, sizeof(T))) return std::nullopt;
      return value;
    }
  };

  template <typename... Specs>
  struct schema_t
  {
    std::tuple<Specs...> specs;
  };

  template <typename... Specs>
  constexpr schema_t<std::remove_cvref_t<Specs>...> schema(Specs&&... specs)
  {
    return {std::tuple<std::remove_cvref_t<Specs>...>(std::forward<Specs>(specs)...)};
  }

  template <typename... Specs, typename... Values>
  zenoh::Bytes pack(const schema_t<Specs...>& schema, Values&&... values)
  {
    static_assert(sizeof...(Specs) == sizeof...(Values),
      "packet schema and value count must match");

    std::vector<uint8_t> bytes;
    auto values_tuple = std::forward_as_tuple(std::forward<Values>(values)...);
    detail::encode_all(schema, bytes, values_tuple, std::index_sequence_for<Specs...>{});
#ifdef _MSC_VER
    // MSVC has a bug with std::forward on lambdas in zenoh's Bytes(vector&&).
    // Use the copy constructor to avoid triggering the buggy move constructor.
    return zenoh::Bytes(bytes);
#else
    return zenoh::Bytes(std::move(bytes));
#endif
  }

  template <typename... Specs>
  std::optional<std::tuple<typename Specs::value_type...>> unpack(const schema_t<Specs...>& schema,
    const zenoh::Bytes& payload)
  {
    auto bytes = payload.as_vector();
    size_t offset = 0;
    std::tuple<typename Specs::value_type...> values{};

    if(!detail::decode_all(schema.specs, bytes, offset, values)) return std::nullopt;
    if(offset != bytes.size()) return std::nullopt;

    return values;
  }
}

template <typename T>
inline zenoh::Bytes serialize(const T& value)
{
  using value_t = std::remove_cvref_t<T>;

  if constexpr (std::is_same_v<value_t, bool>)
  {
    return pkt::pack(pkt::schema(pkt::boolean), value);
  }
  else if constexpr (std::is_same_v<value_t, zenoh::Bytes>)
  {
    return value.clone();
  }
  else if constexpr (std::is_same_v<value_t, std::vector<uint8_t>>)
  {
    return zenoh::Bytes(value);
  }
  else if constexpr (std::is_same_v<value_t, std::string> ||
    std::is_same_v<value_t, std::string_view> ||
    std::is_convertible_v<const T&, std::string_view>)
  {
    return zenoh::Bytes(std::string_view(value));
  }
  else if constexpr (std::is_trivially_copyable_v<value_t>)
  {
    return pkt::pack(pkt::schema(pkt::pod<value_t>{}), value);
  }
  else
  {
    static_assert(std::is_trivially_copyable_v<value_t>,
      "serialize<T> requires T to be trivially copyable, zenoh::Bytes, std::vector<uint8_t>, or string-like");
  }
}

// --- cast payload → struct (safe size check)
template <typename T>
inline std::optional<T> deserialize(const zenoh::Bytes& payload)
{
  static_assert(std::is_trivially_copyable_v<T>, "pkt_as<T> requires T to be trivially copyable");

  if(payload.size() == sizeof(T))
  {
    if constexpr (std::is_same_v<T, bool>)
    {
      uint8_t data = 0;
      auto reader = payload.reader();
      const size_t bytes_read = reader.read(&data, sizeof(data));
      if(bytes_read != sizeof(data)) return std::nullopt;

      return data != 0;
    }

    T data;
    auto reader = payload.reader();
    const size_t bytes_read = reader.read(reinterpret_cast<uint8_t*>(&data), payload.size());
    if(bytes_read != sizeof(T)) return std::nullopt;

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
