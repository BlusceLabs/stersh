import { component$, useStore } from '@builder.io/qwik';

export default component$(() => {
  const state = useStore({
    query: '',
    results: [] as { id: number; title: string; year: string }[],
  });

  return (
    <div class="w-full max-w-2xl">
      <div class="relative">
        <input
          type="text"
          placeholder="Search movies, TV shows..."
          bind:value={state.query}
          onInput$={() => {
            if (state.query.length > 2) {
              state.results = [
                { id: 1, title: 'Inception', year: '2010' },
                { id: 2, title: 'The Matrix', year: '1999' },
              ];
            } else {
              state.results = [];
            }
          }}
          class="w-full px-6 py-4 bg-zinc-800 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500"
        />
      </div>
      
      {state.results.length > 0 && (
        <div class="mt-2 bg-zinc-800 rounded-lg overflow-hidden">
          {state.results.map(result => (
            <a key={result.id} href={`/movie/${result.id}`} class="block p-3 hover:bg-zinc-700 transition">
              <p class="text-white font-medium">{result.title}</p>
              <p class="text-gray-400 text-sm">{result.year}</p>
            </a>
          ))}
        </div>
      )}
    </div>
  );
});