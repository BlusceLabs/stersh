import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import svelte from '@astrojs/svelte';
import qwik from '@qwikdev/astro';
import tailwind from '@astrojs/tailwind';
import node from '@astrojs/node';
import { loadEnv } from 'vite';

// Load environment variables across server runtime context wrappers
const env = loadEnv(process.env.NODE_ENV || 'development', process.cwd(), '');
const BACKEND_URL = env.BACKEND_URL || 'http://localhost:8000';

export default defineConfig({
  // Enable full Server-Side Rendering (SSR) mode
  output: 'server',
  
  // Standalone production-ready Node deployment configuration
  adapter: node({ 
    mode: 'standalone' 
  }),
  
  // Integrated Multi-Framework UI Engines + Design Ecosystem
  integrations: [
    svelte(), 
    qwik(),
    react(), 
    tailwind({
      applyBaseStyles: true,
    })
  ],

  // Global Routing & Link Speed Enhancements
  prefetch: {
    prefetchAll: true,
    defaultStrategy: 'hover' // Prefetches dynamic links instantly on user interaction
  },
  
  // Development Infrastructure Reverse Proxy Filters
  server: {
    host: true,
    port: 4321,
  },
  
  // High-End Vite Bundle Compilation Pipes
  vite: {
    server: {
      proxy: {
        '/api': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      cssCodeSplit: true, // Generates atomic CSS layers on demand
      minify: 'esbuild',
      sourcemap: false, // Disables maps in production to shed weight
      rollupOptions: {
        output: {
          // Intelligently splits vendor runtimes (Svelte/Qwik/Tailwind) into long-term cached assets
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('svelte')) return 'vendor-svelte';
              if (id.includes('qwik')) return 'vendor-qwik';
              return 'vendor-core';
            }
          }
        }
      }
    }
  }
});