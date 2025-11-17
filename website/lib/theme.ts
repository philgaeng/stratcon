/**
 * Stratcon Theme Configuration
 * Matches backend/services/config.py
 */

export const theme = {
  colors: {
    // Energy colors
    consumption: '#f5b041',  // orange
    production: '#76b7b2',    // teal/light green
    import: '#4e79a7',        // blue
    export: '#333333',        // dark gray/black
    
    // Stratcon brand colors
    darkGreen: '#2E7D32',
    mediumGreen: '#388E3C',
    primaryGreen: '#4CAF50',
    lightGreen: '#8BC34A',
    yellow: '#FFEB3B',
    
    // Grey shades
    black: '#333',
    darkGrey: '#2c3e50',
    mediumGrey: '#666',
    grey: '#888',
    lightGrey: '#7f8c8d',
    veryLightGrey: '#bdc3c7',
  },
  
  fonts: {
    heading: 'Montserrat, Arial, sans-serif',
    body: 'Inter, sans-serif',
  },
  
  fontSize: {
    base: '14px',
    h1: '24px',
    h2: '20px',
    h3: '18px',
  },
} as const;

