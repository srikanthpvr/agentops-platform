import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Map '@' to the src directory for clean imports like '@/components/...'
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      // Proxy all /api requests to the backend server during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
