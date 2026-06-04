import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import tailwind from '@astrojs/tailwind';
import node from '@astrojs/node';
import { loadEnv } from 'vite';

const env = loadEnv(process.env.NODE_ENV || 'development', process.cwd(), '');
const BACKEND_URL = env.BACKEND_URL || 'http://localhost:8000';

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),

  integrations: [
    svelte(),
    tailwind({
      applyBaseStyles: true,
    })
  ],

  prefetch: {
    prefetchAll: false,
    defaultStrategy: 'hover'
  },

  server: {
    host: true,
    port: 4321,
  },

  vite: {
    server: {
      proxy: {
        '/api': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        },
        '/continue-watching': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        },
        '/user': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        },
        '/ads': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        },
        '/analytics': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      cssCodeSplit: true,
      minify: 'esbuild',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('svelte')) return 'vendor-svelte';
              if (id.includes('hls.js')) return 'vendor-hls';
              return 'vendor-core';
            }
          }
        }
      }
    }
  }
});