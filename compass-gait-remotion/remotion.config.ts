import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(2);

// Enable keyboard shortcuts in Remotion Studio
Config.setStudioPort(3000);

// Performance optimizations
Config.setChromiumOpenGlRenderer('angle');
Config.setChromiumHeadlessMode(true);
