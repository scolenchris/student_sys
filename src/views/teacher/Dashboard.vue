<template>
  <el-container class="teacher-shell">
    <el-aside :width="isCollapse ? '82px' : '240px'" class="teacher-aside">
      <div class="teacher-logo">
        <div class="logo-mark">T</div>
        <span v-show="!isCollapse">教师工作台</span>
      </div>
      <el-menu
        :router="true"
        :collapse="isCollapse"
        :default-active="route.path"
        class="teacher-menu"
      >
        <el-menu-item index="/teacher/scores">
          <el-icon><EditPen /></el-icon>
          <span>成绩录入</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="teacher-header">
        <div class="left">
          <el-button text @click="isCollapse = !isCollapse">
            <el-icon><component :is="isCollapse ? Expand : Fold" /></el-icon>
          </el-button>
          <strong>教师端</strong>
        </div>
        <div class="right">
          <el-button text @click="router.push('/change-password')">
            <el-icon><Lock /></el-icon>
            修改密码
          </el-button>
          <el-button type="danger" plain @click="logout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="teacher-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { EditPen, Expand, Fold, Lock, SwitchButton } from "@element-plus/icons-vue";

const router = useRouter();
const route = useRoute();
const isCollapse = ref(false);

const logout = () => {
  localStorage.clear();
  router.push("/");
};
</script>

<style scoped>
.teacher-shell {
  height: 100vh;
  background: linear-gradient(180deg, #f8fbff 0%, #eef3fb 100%);
}

.teacher-aside {
  background: linear-gradient(180deg, #0f2945 0%, #15406a 100%);
  transition: width 0.2s ease;
}

.teacher-logo {
  height: 70px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  color: #ffffff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
  font-weight: 700;
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffd572, #ff9d5d);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3d301c;
}

.teacher-menu {
  border-right: none;
  background: transparent;
}

.teacher-menu :deep(.el-menu-item) {
  color: #d4e3f8;
  margin: 8px 10px;
  border-radius: 10px;
}

.teacher-menu :deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

.teacher-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #2ea0ff, #1f78cf);
  color: #ffffff;
}

.teacher-header {
  height: 68px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e7edf7;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.teacher-main {
  height: calc(100vh - 68px);
  overflow: auto;
  padding: 20px;
}
</style>
