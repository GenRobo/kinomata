// Copyright (c) General Robotics Technology, Inc. All rights reserved.

#include "Kinomata.h"

#include "KinomataLibrary.h"
#include "Misc/MessageDialog.h"
#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "HAL/PlatformProcess.h"

#define LOCTEXT_NAMESPACE "FKinomataModule"

void FKinomataModule::StartupModule()
{
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module

	// Temp code for testing
	// Get the base directory of this plugin
	const FString BaseDir = IPluginManager::Get().FindPlugin("Kinomata")->GetBaseDir();

	// Add on the relative location of kinomata dll and load it
	FString LibraryPath;
#if PLATFORM_WINDOWS
	LibraryPath = FPaths::Combine(*BaseDir, TEXT("Binaries/FirstParty/KinomataLibrary/win-x64/Release/kinomata.dll"));
#elif PLATFORM_MAC
    LibraryPath = FPaths::Combine(*BaseDir, TEXT("Source/FirstParty/KinomataLibrary/macos-arm64/Release/libkinomata.dylib"));
#elif PLATFORM_LINUX
	LibraryPath = FPaths::Combine(*BaseDir, TEXT("Binaries/FirstParty/KinomataLibrary/linux-debian-x64/Release/libkinomata.so"));
#endif // PLATFORM_WINDOWS

	KinomataLibraryHandle = !LibraryPath.IsEmpty() ? FPlatformProcess::GetDllHandle(*LibraryPath) : nullptr;

	if (KinomataLibraryHandle)
	{
		// Call the test function in the kinomata library that opens a message box
		KinomataLibTestFunction();
	}
	else
	{
		FMessageDialog::Open(EAppMsgType::Ok, LOCTEXT("ExternalLibraryError", "Failed to load kinomata external library"));
	}
}

void FKinomataModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.

	// Free the dll handle
	FPlatformProcess::FreeDllHandle(KinomataLibraryHandle);
	KinomataLibraryHandle = nullptr;
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FKinomataModule, Kinomata)
