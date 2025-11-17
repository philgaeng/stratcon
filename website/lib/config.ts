/**
 * Frontend configuration matching backend/services/config.py
 * Centralized configuration for fonts, colors, and other constants
 */

export const FontConfig = {
  HEADING_FONT_FAMILY: "Montserrat, Arial, sans-serif",
  BODY_FONT_FAMILY: "Inter, Arial, sans-serif",
} as const;

// Base color definitions
const baseColors = {
  // Primary Green (Client) - two shades
  STRATCON_DARK_GREEN: "#2E7D32", // Primary Green (Client) - darker shade
  STRATCON_PRIMARY_GREEN: "#4CAF50", // Primary Green (Client) - darkest shade
  STRATCON_BACKGROUND_GREEN: "#2F6B4A", // Background Green
  // Additional green shades
  STRATCON_MEDIUM_GREEN: "#388E3C",
  STRATCON_LIGHT_GREEN: "#8BC34A",
} as const;

export const ColorConfig = {
  // Primary Green (Client) - two shades
  STRATCON_DARK_GREEN: baseColors.STRATCON_DARK_GREEN,
  STRATCON_PRIMARY_GREEN: baseColors.STRATCON_PRIMARY_GREEN,

  // Additional green shades
  STRATCON_MEDIUM_GREEN: baseColors.STRATCON_MEDIUM_GREEN,
  STRATCON_LIGHT_GREEN: baseColors.STRATCON_LIGHT_GREEN,

  // UI Background Colors
  EXPLORER_BACKGROUND: baseColors.STRATCON_BACKGROUND_GREEN, // Explorer Background
  TOP_BAR: "#E3E3E3", // Top Bar
  BACKGROUND: "#EFEFEF", // Background (warm light grey)
  CARD_BACKGROUND: "#FFFFFF", // Card Background
  CARD_BORDER: "#DDDDDD", // Card Border (warm neutral border)
  FIELD_BACKGROUND: "#F6F6F6", // Field Background (soft warm grey input)
  HIGHLIGHT: "#F3F3F3", // Highlight

  // Text Colors
  TEXT_DARK: "#2C2C2C", // Text Dark
  TEXT_MEDIUM: "#6A6A6A", // Text Medium

  // Button Colors - inherit from base colors
  PRIMARY_BUTTON: baseColors.STRATCON_DARK_GREEN, // Primary Button
  SECONDARY_BUTTON: baseColors.STRATCON_PRIMARY_GREEN, // Secondary Button

  // Legacy colors (kept for backward compatibility)
  STRATCON_YELLOW: "#FFEB3B",
  STRATCON_BLACK: "#333",
  STRATCON_DARK_GREY: "#2c3e50",
  STRATCON_MEDIUM_GREY: "#475569",
  STRATCON_GREY: "#888",
  STRATCON_LIGHT_GREY: "#F6F6F6",
  STRATCON_VERY_LIGHT_GREY: "#EFEFEF",
} as const;
