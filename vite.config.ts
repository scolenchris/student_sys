import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

const debugBuild = process.env.DEBUG_BUILD === "1";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // 默认生产构建开启压缩；如需排查线上问题，可用 DEBUG_BUILD=1 生成可读包
    minify: debugBuild ? false : "esbuild",
    sourcemap: debugBuild,
    rollupOptions: {
      output: {
        manualChunks: {
          "vue-vendor": ["vue", "vue-router", "pinia"],
          "ui-vendor": ["element-plus", "@element-plus/icons-vue"],
          "http-vendor": ["axios"],
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000", // 后端 Flask 地址
        changeOrigin: true,
        // 如果后端接口没有 /api 前缀，可以开启重写
        // rewrite: (path) => path.replace(/^\/api/, '')
      },
    },
  },
});
