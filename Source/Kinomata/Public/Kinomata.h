// Copyright (c) General Robotics Technology, Inc. All rights reserved.

#pragma once

#include "Modules/ModuleManager.h"

class FKinomataModule : public IModuleInterface
{
public:

	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	/** Handle to the test dll we will load */
	void*	KinomataLibraryHandle = nullptr;
};
