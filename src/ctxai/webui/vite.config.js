import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  root: ".",
  base: "/",

  build: {
    outDir: "dist",
    emptyOutDir: true,
    manifest: true,

    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.js"),
        styles: resolve(__dirname, "css/vite-entry.css"),
      },

      output: {
        // Content-hashed filenames for cache busting
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },

      // Keep vendor libs external — they're already minified and loaded via <script>
      external: [
        // These are loaded as globals from vendor/ — don't bundle them
      ],
    },

    // Target modern browsers
    target: "es2022",

    // Source maps for debugging
    sourcemap: false,

    // CSS code splitting
    cssCodeSplit: true,

    // Minify
    minify: "esbuild",
  },

  // Dev server (for local dev without Python backend)
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the Python backend
      "/api": "http://localhost:50001",
      "/poll": "http://localhost:50001",
      "/socket.io": {
        target: "http://localhost:50001",
        ws: true,
      },
    },
  },

  // Resolve aliases for cleaner imports
  resolve: {
    alias: {
      "/js": resolve(__dirname, "js"),
      "/components": resolve(__dirname, "components"),
      "/css": resolve(__dirname, "css"),
    },
  },
});
