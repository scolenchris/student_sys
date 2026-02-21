<template>
  <el-container class="admin-shell">
    <el-aside :width="asideWidth" class="admin-aside">
      <div class="brand" @click="router.push('/admin/overview')">
        <div class="brand-mark">SM</div>
        <div v-show="!isCollapse" class="brand-text">
          <p class="brand-cn">成绩管理系统</p>
          <p class="brand-en">Admin Console</p>
        </div>
      </div>

      <el-scrollbar class="menu-scroll">
        <el-menu
          :router="true"
          :collapse="isCollapse"
          :collapse-transition="false"
          :default-active="activePath"
          :default-openeds="openedGroups"
          :unique-opened="true"
          class="admin-menu"
        >
          <el-sub-menu
            v-for="group in menuGroups"
            :key="group.key"
            :index="group.key"
          >
            <template #title>
              <el-icon>
                <component :is="group.icon" />
              </el-icon>
              <span>{{ group.title }}</span>
            </template>
            <el-menu-item
              v-for="item in group.items"
              :key="item.index"
              :index="item.index"
            >
              {{ item.label }}
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="admin-content">
      <el-header class="admin-header">
        <div class="header-left">
          <el-button text class="collapse-btn" @click="toggleMenu">
            <el-icon>
              <component :is="isCollapse ? Expand : Fold" />
            </el-icon>
          </el-button>
          <h3 class="page-title">{{ currentPageTitle }}</h3>
        </div>
        <div class="header-right">
          <span class="welcome">你好，{{ username }}</span>
          <el-button text @click="goChangePassword">
            <el-icon><Lock /></el-icon>
            修改密码
          </el-button>
          <el-button type="danger" plain @click="logout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="admin-main">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import {
  DataAnalysis,
  EditPen,
  Expand,
  Fold,
  Histogram,
  Lock,
  School,
  SwitchButton,
} from "@element-plus/icons-vue";

const router = useRouter();
const route = useRoute();

const MENU_COLLAPSE_KEY = "admin_menu_collapsed";
const isCollapse = ref(localStorage.getItem(MENU_COLLAPSE_KEY) === "1");

const menuGroups = [
  {
    key: "system",
    title: "系统运营",
    icon: DataAnalysis,
    items: [
      { index: "/admin/overview", label: "数据可视化大屏" },
      { index: "/admin/approval", label: "用户审核" },
      { index: "/admin/settings", label: "系统设置" },
      { index: "/admin/import-history", label: "导入记录与回退" },
      { index: "/admin/audit-logs", label: "敏感操作审计日志" },
    ],
  },
  {
    key: "base",
    title: "组织与档案",
    icon: School,
    items: [
      { index: "/admin/teachers", label: "教师管理" },
      { index: "/admin/classes", label: "班级管理" },
      { index: "/admin/students", label: "学籍管理" },
      { index: "/admin/assignments", label: "任课分配" },
    ],
  },
  {
    key: "score",
    title: "成绩业务",
    icon: EditPen,
    items: [
      { index: "/admin/stats", label: "综合成绩统计" },
      { index: "/admin/score-trend", label: "成绩变化比较" },
      { index: "/admin/score-entry", label: "手动成绩录入" },
      { index: "/admin/exams", label: "考试发布管理" },
    ],
  },
  {
    key: "analysis",
    title: "教学分析",
    icon: Histogram,
    items: [
      { index: "/admin/class-stats", label: "班级成绩统计" },
      { index: "/admin/teacher-stats", label: "教师教学统计" },
    ],
  },
];

const pageTitleMap = menuGroups
  .flatMap((g) => g.items)
  .reduce((map, item) => {
    map[item.index] = item.label;
    return map;
  }, {});

const asideWidth = computed(() => (isCollapse.value ? "82px" : "270px"));
const activePath = computed(() => route.path);
const openedGroups = computed(() =>
  isCollapse.value ? [] : menuGroups.map((group) => group.key),
);
const currentPageTitle = computed(
  () => pageTitleMap[route.path] || "管理后台",
);
const username = computed(() => localStorage.getItem("username") || "管理员");

const toggleMenu = () => {
  isCollapse.value = !isCollapse.value;
  localStorage.setItem(MENU_COLLAPSE_KEY, isCollapse.value ? "1" : "0");
};

const goChangePassword = () => router.push("/change-password");

const logout = async () => {
  try {
    await ElMessageBox.confirm("确认退出当前账号吗？", "提示", {
      type: "warning",
      confirmButtonText: "退出",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }

  localStorage.clear();
  router.push("/");
};
</script>

<style scoped>
.admin-shell {
  height: 100vh;
  background: linear-gradient(180deg, #f8fbff 0%, #eef3fb 100%);
}

.admin-aside {
  background: linear-gradient(180deg, #0f2945 0%, #15406a 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  transition: width 0.2s ease;
}

.brand {
  height: 72px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ffd36f, #ff9c58);
  color: #3b2f1f;
  font-weight: 700;
  letter-spacing: 1px;
}

.brand-text {
  line-height: 1.2;
}

.brand-cn {
  color: #f8fbff;
  margin: 0;
  font-weight: 700;
}

.brand-en {
  color: #96b8dc;
  margin: 0;
  font-size: 12px;
}

.menu-scroll {
  height: calc(100vh - 72px);
}

.admin-menu {
  border-right: none;
  background: transparent;
}

.admin-menu :deep(.el-menu) {
  border-right: none;
  background: transparent;
}

.admin-menu :deep(.el-sub-menu__title),
.admin-menu :deep(.el-menu-item) {
  margin: 6px 10px;
  border-radius: 10px;
  color: #d4e3f8;
  height: 44px;
  line-height: 44px;
}

.admin-menu :deep(.el-sub-menu__title:hover),
.admin-menu :deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #2ea0ff, #1f78cf);
  color: #ffffff;
}

.admin-content {
  overflow: hidden;
}

.admin-header {
  height: 68px;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #e7edf7;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  font-size: 20px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: #10385d;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.welcome {
  color: #4c6684;
  font-size: 14px;
}

.admin-main {
  height: calc(100vh - 68px);
  overflow: auto;
  padding: 20px;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
