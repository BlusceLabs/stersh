<script lang="ts">
  export let title: string;
  export let isActive: boolean = false;
</script>

<button
  class={`px-4 py-2 rounded-lg font-medium transition-all ${
    isActive
      ? 'bg-yellow-500 text-black'
      : 'bg-zinc-800 text-white hover:bg-zinc-700'
  }`}
>
  {title}
</button>

<style>
  button {
    font-family: inherit;
  }
</style>