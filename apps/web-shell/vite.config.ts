import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import federation from "@originjs/vite-plugin-federation";

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: "shell",
      remotes: {
        analysis: "http://localhost:3001/assets/remoteEntry.js",
        // Add more remotes here as you build them:
        // workspace: 'http://localhost:3002/assets/remoteEntry.js',
        // billing: 'http://localhost:3003/assets/remoteEntry.js',
      },
      shared: ["react", "react-dom"],
    }),
  ],
  server: {
    port: 3000,
  },
  build: {
    modulePreload: false,
    target: "esnext",
    minify: false,
    cssCodeSplit: false,
  },
});
