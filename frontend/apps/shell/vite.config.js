import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/graphql": process.env.API_PROXY_TARGET || "http://127.0.0.1:8080",
      "/mfe/signup": "http://localhost:5174",
      "/mfe/orders": "http://localhost:5175",
      "/mfe/checkout": "http://localhost:5176",
    },
  },
});
