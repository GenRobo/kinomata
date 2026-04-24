#if defined(_MSC_VER) && defined(_DEBUG)

#include <crtdbg.h>

namespace {
struct debug_heap_initializer {
  debug_heap_initializer()
  {
    int flags = _CrtSetDbgFlag(_CRTDBG_REPORT_FLAG);
    flags |= _CRTDBG_ALLOC_MEM_DF;
    flags |= _CRTDBG_LEAK_CHECK_DF;
    _CrtSetDbgFlag(flags);
  }
};

debug_heap_initializer g_debug_heap_initializer;
} // namespace

#endif
