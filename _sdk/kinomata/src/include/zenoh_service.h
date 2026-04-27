#pragma once

#include <concepts>
#include <type_traits>
#include <functional>
#include "zenoh/api/session.hxx"
#include "api_provider.h"

template <typename Fun, typename Ret>
concept ReqRspHandler0 =
  std::invocable<Fun&> &&
  (
    std::is_void_v<Ret> ||
    std::same_as<std::invoke_result_t<Fun&>, Ret>
  );

template <typename Fun, typename Ret>
concept ReqRspHandler =
  std::invocable<Fun&,
    const std::string_view,
    const zenoh::Bytes&, const zenoh::Session&,
    api_provider_t&> &&
  (
    std::is_void_v<Ret> ||
    std::same_as<
      std::invoke_result_t<Fun&,
        const std::string_view,
        const zenoh::Bytes&, const zenoh::Session&,
        api_provider_t&>,
      Ret>
  );

class zenoh_service_t
{
  zenoh::Session session_;
  api_provider_t& api_provider_;
  std::vector<zenoh::Queryable<void>> queryables_;

  void bind_queryables();

  // Query-Reply binding for functions with no args
  template <typename Ret, typename Fun>
  requires ReqRspHandler0<Fun, Ret>
  void bind_qr_0(std::string_view base_name, std::string_view method_name, Fun&& fun);

  // Query-Reply binding for functions with one or more args
  template <typename Ret, typename Fun>
  requires ReqRspHandler<Fun, Ret>
  void bind_qr(std::string_view base_name, std::string_view method_name, Fun&& fun);

public:
  zenoh_service_t(api_provider_t& api_provider);
};

template <typename Ret, typename Fun>
requires ReqRspHandler0<Fun, Ret>
void zenoh_service_t::bind_qr_0(std::string_view base_name, std::string_view method_name, Fun&& fun)
{
  static auto empty_payload = zenoh::Bytes();

  std::string key = std::format("{}/{}", base_name, method_name);

  auto q = session_.declare_queryable(key, [this, f = std::forward<Fun>(fun)](const zenoh::Query& query) {
    if constexpr (std::is_void_v<Ret>)
    {
      f();
      query.reply(query.get_keyexpr(), empty_payload.clone());
    }
    else if constexpr (std::is_same_v<Ret, bool>)
    {
      bool result = f(); 
      if(result) query.reply(query.get_keyexpr(), empty_payload.clone());
      else query.reply_err(empty_payload.clone());
    }
    else
    {
      Ret result = f(); 
      query.reply(query.get_keyexpr(), serialize<Ret>(result));
    }
  },
  [](){std::cerr << "Queryable destroyed, REQ handler unregistered." << std::endl;}
  );

  queryables_.push_back(std::move(q));
}

template <typename Ret, typename Fun>
requires ReqRspHandler<Fun, Ret>
void zenoh_service_t::bind_qr(std::string_view base_name, std::string_view method_name,
  Fun&& fun)
{
  static auto empty_payload = zenoh::Bytes();

  std::string key = std::format("{}/{}", base_name, method_name);

  auto q = session_.declare_queryable(key, [this, key, f = std::forward<Fun>(fun)](const zenoh::Query& query) {
    auto payload_opt = query.get_payload();
    const zenoh::Bytes& payload = payload_opt.has_value() ? payload_opt->get() : empty_payload;

    if constexpr (std::is_void_v<Ret>)
    {
      std::invoke(f, key, payload, session_, api_provider_);
      query.reply(query.get_keyexpr(), empty_payload.clone());
    }
    else if constexpr (std::is_same_v<Ret, bool>)
    {
      bool result = std::invoke(f, key, payload, session_, api_provider_);
      if(result) query.reply(query.get_keyexpr(), empty_payload.clone());
      else query.reply_err(empty_payload.clone());
    }
    else
    {
      Ret result = std::invoke(f, key, payload, session_, api_provider_);
      query.reply(query.get_keyexpr(), serialize<Ret>(result));
    }
  },
  [](){std::cerr << "Queryable destroyed, REQ handler unregistered." << std::endl;}
  );

  queryables_.push_back(std::move(q));
}
