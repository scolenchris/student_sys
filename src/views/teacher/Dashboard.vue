<template>
  <el-container class="teacher-shell">
    <el-aside :width="asideWidth" class="teacher-aside">
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
        <el-menu-item index="/teacher/class-rank-trend">
          <el-icon><DataLine /></el-icon>
          <span>班级级排趋势</span>
        </el-menu-item>
        <el-menu-item index="/teacher/history-scores">
          <el-icon><Reading /></el-icon>
          <span>历史成绩查询</span>
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
          <LayoutSizeSwitcher />
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
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  DataLine,
  EditPen,
  Expand,
  Fold,
  Lock,
  Reading,
  SwitchButton,
} from "@element-plus/icons-vue";
import LayoutSizeSwitcher from "../../components/LayoutSizeSwitcher.vue";
import { clearAuthStorageKeepLayoutSize } from "../../composables/useLayoutSize";

const router = useRouter();
const route = useRoute();
const isCollapse = ref(false);
const asideWidth = computed(() =>
  isCollapse.value
    ? "var(--app-aside-collapsed-width)"
    : "var(--app-teacher-aside-width)",
);

const logout = () => {
  clearAuthStorageKeepLayoutSize();
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
  height: var(--app-brand-height);
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
  height: var(--app-menu-item-height);
  line-height: var(--app-menu-item-height);
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
  height: var(--app-header-height);
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
  flex-wrap: wrap;
}

.teacher-main {
  height: calc(100vh - var(--app-header-height));
  overflow: auto;
  padding: var(--app-main-padding);
}
</style>
