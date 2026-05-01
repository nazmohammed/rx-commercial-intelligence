/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        rx: {
          // RX brand palette
          purple: '#5B2C8B',
          purpleDark: '#3F1F61',
          purpleLight: '#8A5DB8',
          cream: '#F4EDE2',
          ink: '#1A1A1A',
          subtle: '#6B6B6B',
        },
      },
      fontFamily: {
        sans: ['Segoe UI', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(26,26,26,0.06), 0 4px 12px rgba(26,26,26,0.06)',
      },
    },
  },
  plugins: [],
};
