#pragma once

#include <cassert>
#include <concepts>
#include <format>
#include <functional>
#include <iostream>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>
#include "zenoh/api/session.hxx"
#include "api_provider.h"
#include "packet.hpp"

template <typename T>
concept ReqRspResponse =
  std::same_as<std::remove_cvref_t<T>, void> ||
  requires(T&& value)
  {
    { serialize<std::remove_cvref_t<T>>(std::forward<T>(value)) } -> std::same_as<zenoh::Bytes>;
  };

template <typename Fun>
concept ReqRspHandler0 =
  requires(Fun& fun)
  {
    { std::invoke(fun) } -> ReqRspResponse;
  };

template <typename Fun>
concept ReqRspHandler =
  requires(Fun& fun, std::string_view key_expr,
    const zenoh::Bytes& payload, const zenoh::Session& session,
    api_provider_t& api_provider)
  {
    { std::invoke(fun, key_expr, payload, session, api_provider) } -> ReqRspResponse;
  };

class zenoh_service_t
{
  zenoh::Session session_;
  api_provider_t& api_provider_;
  std::vector<zenoh::Queryable<void>> queryables_;

  static std::optional<zenoh_service_t> instance_;

  void bind_queryables();

  // Query-Reply binding for functions with no args
  void bind_qr_0(std::string_view key_expr, ReqRspHandler0 auto&& fun);

  // Query-Reply binding for functions with one or more args
  void bind_qr(std::string_view key_expr, ReqRspHandler auto&& fun);

public:
  explicit zenoh_service_t(api_provider_t& api_provider);
  zenoh_service_t(const zenoh_service_t&) = delete;
  zenoh_service_t& operator=(const zenoh_service_t&) = delete;

  static inline void init(api_provider_t& api_provider)
  {
    instance_.emplace(api_provider);
  }

  static inline zenoh_service_t& get()
  {
    assert(instance_.has_value() && "zenoh_service_t not initialized");
    return *instance_;
  }

  inline zenoh::Publisher add_pub(std::string_view key_expr)
  {
    return session_.declare_publisher(key_expr);
  }

  inline void remove_pub(zenoh::Publisher& pub_ref)
  {
    std::move(pub_ref).undeclare();
  }
};

void zenoh_service_t::bind_qr_0(std::string_view key_expr, ReqRspHandler0 auto&& fun)
{
  using Fun = decltype(fun);
  using Ret = std::remove_cvref_t<std::invoke_result_t<Fun&>>;

  static auto empty_payload = zenoh::Bytes();

  auto q = session_.declare_queryable(key_expr, [f = std::forward<Fun>(fun)](const zenoh::Query& query) mutable {
    if constexpr (std::is_void_v<Ret>)
    {
      std::invoke(f);
      query.reply(query.get_keyexpr(), empty_payload.clone());
    }
    else
    {
      decltype(auto) result = std::invoke(f);
      query.reply(query.get_keyexpr(), serialize<Ret>(result));
    }
  },
  [](){std::cerr << "Queryable destroyed, REQ handler unregistered." << std::endl;}
  );

  queryables_.push_back(std::move(q));
}

void zenoh_service_t::bind_qr(std::string_view key_expr, ReqRspHandler auto&& fun)
{
  using Fun = decltype(fun);
  using Ret = std::remove_cvref_t<std::invoke_result_t<Fun&, std::string_view,
    const zenoh::Bytes&, const zenoh::Session&, api_provider_t&>>;

  static auto empty_payload = zenoh::Bytes();

  auto q = session_.declare_queryable(key_expr, [this, key_expr, f = std::forward<Fun>(fun)](const zenoh::Query& query) mutable {
    auto payload_opt = query.get_payload();
    const zenoh::Bytes& payload = payload_opt.has_value() ? payload_opt->get() : empty_payload;

    if constexpr (std::is_void_v<Ret>)
    {
      std::invoke(f, key_expr, payload, session_, api_provider_);
      query.reply(query.get_keyexpr(), empty_payload.clone());
    }
    else
    {
      decltype(auto) result = std::invoke(f, key_expr, payload, session_, api_provider_);
      query.reply(query.get_keyexpr(), serialize<Ret>(result));
    }
  },
  [](){std::cerr << "Queryable destroyed, REQ handler unregistered." << std::endl;}
  );

  queryables_.push_back(std::move(q));
}
