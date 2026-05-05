import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In Container Apps the frontend nginx sidecar reverse-proxies /api/* to the
// backend on localhost:8000. During local `vite dev`, do the same with a
// dev-server proxy so the React code can always call /api/* uniformly.
export default defineConfig({
  plugins: [react()],
  // When served at /commercial in production, all asset paths must be rooted
  // there. Vite dev server still proxies /api to localhost:8000 for local work.
  base: '/commercial/',
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
