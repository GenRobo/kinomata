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
    string PlatformString = "none";

		if (Target.Platform == UnrealTargetPlatform.Win64)
		{
      PlatformString = "win-x64";

			PublicAdditionalLibraries.Add(Path.Combine(ModuleDirectory, PlatformString, "lib", ConfigurationString, "kinomata.lib"));
		}
		else if (Target.Platform == UnrealTargetPlatform.Mac)
		{
      PlatformString = "macos-arm64";

			PublicAdditionalLibraries.Add(Path.Combine(ModuleDirectory, PlatformString, "lib", ConfigurationString, "libkinomata.a"));
		}
		else if (Target.Platform == UnrealTargetPlatform.Linux)
		{
      PlatformString = "linux-debian-x64";

			PublicAdditionalLibraries.Add(Path.Combine(ModuleDirectory, PlatformString, "lib", ConfigurationString, "libkinomata.a"));
		}

    PublicIncludePaths.Add(Path.Combine(ModuleDirectory, PlatformString, "include"));
	}
}
