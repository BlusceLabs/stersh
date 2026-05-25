import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isDev = mode === "development";
  const isProd = mode === "production";

  return {
 plugins: [
        react(),
      ],

     base: env["VITE_BASE_URL"] ?? "/",

     server: {
       port: Number(env["VITE_PORT"]) || 3000,
       strictPort: true,
       open: true,
       cors: true,
 proxy: {
          "/api": {
            target: env["VITE_API_URL"] || "http://127.0.0.1:8000",
            changeOrigin: true,
            secure: false,
          },
        },
     },

     build: {
       outDir: "../dist",
       emptyOutDir: true,
       sourcemap: isDev ? "inline" : false,
       minify: isProd ? "esbuild" : false,
       target: "esnext",
       chunkSizeWarningLimit: 1000,
rollupOptions: {
          input: path.resolve(__dirname, "./index.html"),
          output: {
            // Split vendor chunks for better long-term caching
            manualChunks: {
              react: ["react", "react-dom"],
              router: ["@tanstack/react-router"],
            },
            chunkFileNames: "assets/js/[name]-[hash].js",
            entryFileNames: "assets/js/[name]-[hash].js",
            assetFileNames: "assets/[ext]/[name]-[hash].[ext]",
          },
        },
     },

 resolve: {
        alias: {
          "@": path.resolve(__dirname, "./src"),
          "@components": path.resolve(__dirname, "./src/components"),
          "@app": path.resolve(__dirname, "./src/app"),
          "@store": path.resolve(__dirname, "./src/store"),
          "@stores": path.resolve(__dirname, "./src/store"),
          "@utils": path.resolve(__dirname, "./src/utils"),
          "@hooks": path.resolve(__dirname, "./src/hooks"),
          "@assets": path.resolve(__dirname, "./src/assets"),
          "@types": path.resolve(__dirname, "./src/types"),
        },
      },

     optimizeDeps: {
       include: ["react", "react-dom"],
     },

     preview: {
       port: Number(env["VITE_PREVIEW_PORT"]) || 4173,
       strictPort: true,
     },

     css: {
       devSourcemap: isDev,
       modules: {
         localsConvention: "camelCaseOnly",
       },
     },

     esbuild: {
       // Strip console/debugger in production
       drop: isProd ? ["console", "debugger"] : [],
     },
   };
});