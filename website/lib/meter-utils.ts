/**
 * Utility functions for meter logging
 */

/**
 * Format meter identifier to show only last 6 digits with * prefix
 * Example: "MTR-NEO3-1801" -> "*01801" or "1234567890" -> "*7890"
 */
export function formatMeterId(meterId: string): string {
  if (!meterId) return "*";

  // Extract last 6 digits
  const digits = meterId.replace(/\D/g, ""); // Remove all non-digits
  const last6 = digits.slice(-6);

  // Pad with zeros if less than 6 digits
  const padded = last6.padStart(6, "0");

  return `*${padded}`;
}

/**
 * Generate a session ID based on building ID and timestamp
 */
export function generateSessionId(buildingId: number): string {
  const timestamp = Date.now();
  return `building-${buildingId}-${timestamp}`;
}
