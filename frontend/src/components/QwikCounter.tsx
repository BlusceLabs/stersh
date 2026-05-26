import { component$, useStore } from '@builder.io/qwik';

export default component$(() => {
  const state = useStore({
    count: 0,
  });

  return (
    <div class="p-4 bg-zinc-800 rounded-lg">
      <p class="text-white mb-2">Count: {state.count}</p>
      <button 
        onClick$={() => state.count++}
        class="px-4 py-2 bg-yellow-500 text-black rounded hover:bg-yellow-400 transition"
      >
        Increment
      </button>
    </div>
  );
});