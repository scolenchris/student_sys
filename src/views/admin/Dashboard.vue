<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <el-menu
        :router="true"
        default-active="/admin/approval"
        class="el-menu-vertical"
      >
        <div class="logo">管理后台</div>
        <el-menu-item index="/admin/approval">用户审核</el-menu-item>
        <el-menu-item index="/admin/settings">系统设置</el-menu-item>
        <el-menu-item index="/admin/import-history">导入记录与回退</el-menu-item>
        <el-menu-item index="/admin/teachers">教师管理</el-menu-item>
        <el-menu-item index="/admin/classes">班级管理</el-menu-item>
        <el-menu-item index="/admin/students">学籍管理</el-menu-item>
        <el-menu-item index="/admin/stats">成绩管理与成绩排名统计</el-menu-item>
        <el-menu-item index="/admin/score-trend">成绩与排名变化比较</el-menu-item>
        <el-menu-item index="/admin/score-entry">手动成绩录入</el-menu-item>
        <el-menu-item index="/admin/assignments">任课分配</el-menu-item>
        <el-menu-item index="/admin/exams">考试发布管理</el-menu-item>
        <el-menu-item index="/admin/class-stats">班级成绩统计</el-menu-item>
        <el-menu-item index="/admin/teacher-stats">教师教学统计</el-menu-item>
        <el-menu-item @click="logout">退出登录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main> <router-view /> </el-main>
  </el-container>
</template>

<script setup>
import { useRouter } from "vue-router";
const router = useRouter();
const logout = () => {
  localStorage.clear();
  router.push("/");
};
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.el-aside {
  background-color: #304156;
  color: #fff;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-weight: bold;
  font-size: 18px;
  border-bottom: 1px solid #1f2d3d;
  color: black;
}
.el-menu {
  border-right: none;
}
</style>
