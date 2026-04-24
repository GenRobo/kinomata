#if defined _WIN32 || defined _WIN64
    #include <Windows.h>

    #define KINOMATALIBRARY_EXPORT __declspec(dllexport)
#else
    #include <stdio.h>
#endif

#ifndef KINOMATALIBRARY_EXPORT
    #define KINOMATALIBRARY_EXPORT
#endif

KINOMATALIBRARY_EXPORT void KinomataLibTestFunction()
{
#if defined _WIN32 || defined _WIN64
	MessageBox(NULL, TEXT("Loaded KinomataLibrary.dll from the external First Party Plugin."), TEXT("First Party Plugin"), MB_OK);
#else
    printf("Loaded KinomataLibrary from the external First Party Plugin");
#endif
}