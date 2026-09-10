import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/mfe/signup": "http://localhost:5174",
      "/mfe/orders": "http://localhost:5175",
      "/mfe/checkout": "http://localhost:5176",
    },
  },
});
