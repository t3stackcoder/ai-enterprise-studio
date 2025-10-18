import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import federation from "@originjs/vite-plugin-federation";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [
      react(),
      federation({
        name: "shell",
        remotes: {
          analysis: env.VITE_WEB_ANALYSIS_REMOTE || "http://localhost:3001/assets/remoteEntry.js",
          // Add more remotes here as you build them:
          // workspace: 'http://localhost:3002/assets/remoteEntry.js',
          // billing: 'http://localhost:3003/assets/remoteEntry.js',
        },
        shared: ["react", "react-dom"],
      }),
    ],
    server: {
      port: parseInt(env.VITE_WEB_SHELL_PORT || '3000'),
    },
    build: {
      modulePreload: false,
      target: "esnext",
      minify: false,
      cssCodeSplit: false,
    },
  };
});
