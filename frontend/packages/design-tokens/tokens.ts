/**
 * Watchfy Atomic Design Token Architecture
 * Cast with 'as const' to freeze structural values into literal types.
 */
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

/* Extract compile-time type unions directly from token definitions */

export type TokenColors = typeof tokens.colors;
export type TokenSpacing = typeof tokens.spacing;

// Generates an explicit type union: 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900
export type PurpleShades = keyof TokenColors['purple'];

// Generates an explicit type union: 400 | 500
export type CyanShades = keyof TokenColors['cyan'];

// Generates an explicit type union of spacing step keys: 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 | 16
export type SpacingSteps = keyof TokenSpacing;