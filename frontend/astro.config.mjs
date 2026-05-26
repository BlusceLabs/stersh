import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import svelte from '@astrojs/svelte';
import qwik from '@qwikdev/astro';

export default defineConfig({
  integrations: [react(), svelte(), qwik()],
});