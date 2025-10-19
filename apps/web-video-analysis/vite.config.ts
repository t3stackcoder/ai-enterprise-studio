import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import federation from "@originjs/vite-plugin-federation";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const port = parseInt(env.VITE_WEB_VIDEO_ANALYSIS_PORT || '3002');
  
  return {
    plugins: [
      react(),
      federation({
        name: "videoAnalysis",
        filename: "remoteEntry.js",
        exposes: {
          "./VideoAnalysisApp": "./src/App.tsx",
          "./VideoAnalysisRoutes": "./src/routes.tsx",
        },
        shared: ["react", "react-dom"],
      }),
    ],
    server: {
      port,
      cors: true,
    },
    preview: {
      port,
    },
    build: {
      modulePreload: false,
      target: "esnext",
      minify: false,
      cssCodeSplit: false,
    },
  };
});
