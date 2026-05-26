import { component$ } from '@builder.io/qwik';

export default component$(() => {
  return (
    <div class="p-4 bg-zinc-800 rounded-lg">
      <h2 class="text-white font-semibold mb-2">Qwik Counter</h2>
      <p class="text-gray-400">Qwik components work with Astro!</p>
    </div>
  );
});