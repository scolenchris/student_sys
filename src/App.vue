<template>
  <router-view />
</template>

<script setup>
// 这里暂时不需要逻辑
</script>

<style>
/* 全局样式重置，确保老旧电脑浏览器显示正常 */
body {
  margin: 0;
  padding: 0;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}

#app {
  height: 100vh;
}

/* 针对 Element Plus 的一些全局微调 */
.el-card {
  margin-bottom: 20px;
}
</style>