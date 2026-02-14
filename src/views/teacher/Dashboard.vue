<template>
  <el-container class="layout-container">
    <el-aside width="200px" style="background-color: #2c3e50;">
      <el-menu :router="true" default-active="/teacher/scores" theme="dark">
        <div class="logo">教师工作台</div>
        <el-menu-item index="/teacher/scores">成绩录入</el-menu-item>
        <el-menu-item @click="logout">退出登录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const logout = () => {
  localStorage.clear()
  router.push('/')
}
</script>