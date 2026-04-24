#if defined _WIN32 || defined _WIN64
#define KINOMATALIBRARY_IMPORT __declspec(dllimport)
#elif defined __linux__
#define KINOMATALIBRARY_IMPORT __attribute__((visibility("default")))
#else
#define KINOMATALIBRARY_IMPORT
#endif

KINOMATALIBRARY_IMPORT void KinomataLibTestFunction();
