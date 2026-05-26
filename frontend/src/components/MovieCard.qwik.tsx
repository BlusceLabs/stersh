import { component$ } from '@builder.io/qwik';

interface MovieCardProps {
  title: string;
  year: string;
  posterUrl: string;
}

export default component$(() => {
  return (
    <div class="group cursor-pointer">
      <div class="relative overflow-hidden rounded-lg bg-zinc-800 aspect-[2/3]">
        <img
          src="/placeholder-movie.jpg"
          alt="Movie poster"
          width={200}
          height={300}
          class="w-full h-full object-cover transition-transform group-hover:scale-105"
        />
      </div>
      <div class="mt-2">
        <h3 class="font-medium text-sm line-clamp-1">Movie Title</h3>
        <p class="text-xs text-gray-400">2024</p>
      </div>
    </div>
  );
});