import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Proxy keeps the browser same-origin, so the httpOnly session cookie works without CORS.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } }
});
