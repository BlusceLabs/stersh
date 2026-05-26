<script lang="ts">
  export let title: string;
  export let isActive: boolean = false;
  export let href: string | undefined = undefined;
</script>

{#if href}
  <a 
    href={href}
    class={`px-4 py-2 rounded-lg font-medium transition-all inline-block text-center ${
      isActive
        ? 'bg-yellow-500 text-black'
        : 'bg-zinc-800 text-white hover:bg-zinc-700'
    }`}
  >
    {title}
  </a>
{:else}
  <button
    class={`px-4 py-2 rounded-lg font-medium transition-all ${
      isActive
        ? 'bg-yellow-500 text-black'
        : 'bg-zinc-800 text-white hover:bg-zinc-700'
    }`}
  >
    {title}
  </button>
{/if}

<style>
  button, a {
    font-family: inherit;
  }
</style>