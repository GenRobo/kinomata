// Copyright (c) General Robotics Technology, Inc. All rights reserved.

using System.IO;
using UnrealBuildTool;

public class KinomataLibrary : ModuleRules
{
	public KinomataLibrary(ReadOnlyTargetRules Target) : base(Target)
	{
		Type = ModuleType.External;
		PublicSystemIncludePaths.Add("$(ModuleDir)/Public");

		string ConfigurationString = (Target.Configuration == UnrealTargetConfiguration.Debug) ? "Debug" : "Release";

		if (Target.Platform == UnrealTargetPlatform.Win64)
		{
			// Add the import library
			PublicAdditionalLibraries.Add(Path.Combine(ModuleDirectory, "win-x64", ConfigurationString, "kinomata.lib"));

			// Delay-load the DLL, so we can load it from the right place first
			PublicDelayLoadDLLs.Add("kinomata.dll");

			// Ensure that the DLL is staged along with the executable
			RuntimeDependencies.Add("$(PluginDir)/Binaries/FirstParty/KinomataLibrary/win-x64/${ConfigurationString}/kinomata.dll");
		}
		else if (Target.Platform == UnrealTargetPlatform.Mac)
		{
			PublicDelayLoadDLLs.Add(Path.Combine(ModuleDirectory, "macos-arm64", ConfigurationString, "libkinomata.dylib"));
			RuntimeDependencies.Add("$(PluginDir)/Source/FirstParty/KinomataLibrary/macos-arm64/${ConfigurationString}/libkinomata.dylib");
		}
		else if (Target.Platform == UnrealTargetPlatform.Linux)
		{
			string KinomataSoPath = Path.Combine("$(PluginDir)", "Binaries", "FirstParty", "KinomataLibrary", "linux-debian-x64", ConfigurationString, "libkinomata.so");
			PublicAdditionalLibraries.Add(KinomataSoPath);
			PublicDelayLoadDLLs.Add(KinomataSoPath);
			RuntimeDependencies.Add(KinomataSoPath);
		}
	}
}
