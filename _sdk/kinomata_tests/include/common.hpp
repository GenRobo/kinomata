#pragma once

#include <mutex>

struct looper_t
{
  bool dead;
  std::function<void(void)> fun;
};

class looper_manager
{
  static inline std::vector<std::shared_ptr<looper_t>> loopers_ = {};
  static inline std::vector<std::shared_ptr<looper_t>> to_add_ = {};
  static inline std::mutex m_{};

  static inline bool clear_pending_ = false;

  static void update()
  {
    if(clear_pending_)
    {
      std::lock_guard lk(m_);
      std::erase_if(loopers_, [](const std::shared_ptr<looper_t> looper) { return looper->dead; });

      clear_pending_ = false;
    }

    if(!to_add_.empty())
    {
      std::lock_guard lk(m_);

      loopers_.insert(loopers_.end(), to_add_.begin(), to_add_.end());
      to_add_.clear();
    }

    for(auto& looper : loopers_)
    {
      looper->fun();
    }
  }

public:
  static void add(std::function<void(void)> in_function)
  {
    std::lock_guard lk(m_);

    to_add_.emplace_back(new looper_t{
      .dead = false,
      .fun = std::move(in_function)
    });
  }

  static void clear(size_t reserve_count = 1)
  {
    std::lock_guard lk(m_);
    for(auto& looper : loopers_)
    {
      looper->dead = true;
    }
    clear_pending_ = true;

    to_add_.clear();
    to_add_.reserve(reserve_count);
  }

  friend int main(int argc, char** argv);
};
