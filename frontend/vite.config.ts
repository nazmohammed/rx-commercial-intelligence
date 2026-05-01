import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In Container Apps the frontend nginx sidecar reverse-proxies /api/* to the
// backend on localhost:8000. During local `vite dev`, do the same with a
// dev-server proxy so the React code can always call /api/* uniformly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
