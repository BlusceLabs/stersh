<script lang="ts">
  let { title, isActive = false, href = undefined } = $props();
</script>

{#if href}
  <a 
    href={href}
    class={`px-4 py-2 rounded-lg font-medium transition-all inline-block text-center ${
      isActive
        ? 'bg-primary text-white'
        : 'bg-surface-raised text-text hover:bg-surface border border-border/50'
    }`}
  >
    {title}
  </a>
{:else}
  <button
    class={`px-4 py-2 rounded-lg font-medium transition-all ${
      isActive
        ? 'bg-primary text-white'
        : 'bg-surface-raised text-text hover:bg-surface border border-border/50'
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