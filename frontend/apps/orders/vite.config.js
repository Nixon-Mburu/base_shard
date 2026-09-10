import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "/mfe/orders/",
  server: {
    port: 5175,
    cors: true,
    proxy: { "/api": process.env.API_PROXY_TARGET || "http://127.0.0.1:8080" },
  },
  build: {
    cssCodeSplit: false,
    rollupOptions: {
      input: { index: "index.html", remote: "src/remote.jsx" },
      preserveEntrySignatures: "strict",
      output: {
        entryFileNames: "assets/[name].js",
        assetFileNames: (asset) =>
          asset.names?.some((n) => n.endsWith(".css"))
            ? "assets/style.css"
            : "assets/[name]-[hash][extname]",
      },
    },
  },
});
