<script lang="ts">
  let { title, isActive = false, href = undefined } = $props();
  
  // Shared structural and interactive design tokens
  const baseStyles = "inline-flex items-center justify-center px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300 transform select-none focus:outline-none focus:ring-2 focus:ring-red-500/40 focus:ring-offset-2 focus:ring-offset-[#09090b]";
  
  const activeStyles = "bg-gradient-to-r from-red-600 to-pink-600 text-white shadow-lg shadow-red-600/20 hover:brightness-110 active:scale-[0.98]";
  
  const inactiveStyles = "bg-zinc-900/60 text-zinc-300 hover:text-white border border-zinc-800/80 hover:bg-zinc-800/80 hover:border-zinc-700/80 backdrop-blur-md active:scale-[0.98]";
  
  const elementStyles = `${baseStyles} ${isActive ? activeStyles : inactiveStyles}`;
</script>

{#if href}
  <a href={href} class={elementStyles}>
    {title}
  </a>
{:else}
  <button type="button" class={elementStyles}>
    {title}
  </button>
{/if}