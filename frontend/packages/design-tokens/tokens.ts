export const tokens = {
  colors: {
    purple: {
      50: "#f5f3ff",
      100: "#ede9fe",
      200: "#ddd6fe",
      300: "#c4b5fd",
      400: "#a78bfa",
      500: "#8b5cf6",
      600: "#7c3aed",
      700: "#6d28d9",
      800: "#5b21b6",
      900: "#4c1d95",
    },
    cyan: {
      400: "#22d3ee",
      500: "#06b6d4",
    },
  },
  spacing: {
    1: "0.25rem",
    2: "0.5rem",
    3: "0.75rem",
    4: "1rem",
    5: "1.25rem",
    6: "1.5rem",
    8: "2rem",
    10: "2.5rem",
    12: "3rem",
    16: "4rem",
  },
} as const;

export type Tokens = typeof tokens;
export type TokenColors = Tokens['colors'];
export type TokenSpacing = Tokens['spacing'];
export type PurpleShades = TokenColors['purple'];
export type CyanShades = TokenColors['cyan'];
export type SpacingSteps = keyof TokenSpacing;

/**
 * Utility compile engine to output your explicit root stylesheet strings
 */
export function compileTokensToCSSVariables(): string {
  const lines: string[] = [];
  lines.push(':root {');

  // Parse Purple Matrix Scales
  Object.entries(tokens.colors.purple).forEach(([shade, hex]) => {
    lines.push(`  --color-purple-${shade}: ${hex};`);
  });

  // Parse Cyan Matrix Scales
  Object.entries(tokens.colors.cyan).forEach(([shade, hex]) => {
    lines.push(`  --color-cyan-${shade}: ${hex};`);
  });

  // Parse Spacing Layout Intervals
  Object.entries(tokens.spacing).forEach(([step, val]) => {
    lines.push(`  --spacing-step-${step}: ${val};`);
  });

  lines.push('}');
  return lines.join('\n');
}