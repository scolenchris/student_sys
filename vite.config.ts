import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // 设置为 false 以禁用压缩混淆，代码将保持原样（包含空格、换行、变量名）
    minify: false,

    // 建议同时开启 sourcemap，方便在浏览器 DevTools 中直接定位源码位置
    sourcemap: true,
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
