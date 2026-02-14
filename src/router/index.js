import { createRouter, createWebHistory } from "vue-router";
import Login from "../views/Login.vue";
import AdminDashboard from "../views/admin/Dashboard.vue";
import TeacherDashboard from "../views/teacher/Dashboard.vue";
import ChangePassword from "../views/ChangePassword.vue";
import { ElMessage } from "element-plus";

const routes = [
  { path: "/", name: "Login", component: Login },
  {
    path: "/change-password",
    name: "ChangePassword",
    component: ChangePassword,
    meta: { requiresAuth: true }, // 标记需要登录
  },
  {
    path: "/admin",
    component: AdminDashboard,
    redirect: "/admin/approval",
    meta: { requiresAuth: true, role: "admin" }, // 标记需要管理员权限
    children: [
      {
        path: "approval",
        component: () => import("../views/admin/UserApproval.vue"),
      },
      {
        path: "teachers",
        component: () => import("../views/admin/TeacherList.vue"),
      },
      {
        path: "classes",
        component: () => import("../views/admin/ClassMgmt.vue"),
      },
      {
        path: "students",
        component: () => import("../views/admin/StudentMgmt.vue"),
      },
      {
        path: "stats",
        component: () => import("../views/admin/ScoreStats.vue"),
      },
      {
        path: "assignments",
        component: () => import("../views/admin/CourseAssignment.vue"),
      },
      {
        path: "exams",
        component: () => import("../views/admin/ExamPublish.vue"),
      },
      {
        path: "class-stats", // 访问路径: /admin/class-stats
        component: () => import("../views/admin/ClassScoreStats.vue"),
      },
      {
        path: "teacher-stats",
        component: () => import("../views/admin/TeacherStats.vue"),
      },
      {
        path: "settings",
        component: () => import("../views/admin/SystemSettings.vue"),
      },
      {
        path: "score-entry",
        component: () => import("../views/admin/AdminScoreEntry.vue"),
      },
    ],
  },
  {
    path: "/teacher",
    component: TeacherDashboard,
    redirect: "/teacher/scores",
    meta: { requiresAuth: true, role: "teacher" }, // 标记需要老师权限
    children: [
      {
        path: "scores",
        component: () => import("../views/teacher/ScoreEntry.vue"),
      },
    ],
  },
  // 捕获所有未定义路由，重定向到登录
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

// --- 核心修复：全局路由守卫 ---
router.beforeEach((to, from, next) => {
  // 获取本地存储的用户信息
  const role = localStorage.getItem("user_role");
  const isAuthenticated = !!role; // 是否已登录
  // [修改点 3] 获取强制修改密码标记
  const mustChangePwd = localStorage.getItem("must_change_password") === "true";

  // 1. 如果要去的是 登录页
  if (to.path === "/") {
    if (isAuthenticated) {
      // [修改点 4] 登录页也需要判断是否需要改密码
      if (mustChangePwd) return next("/change-password");

      if (role === "admin") return next("/admin/approval");
      if (role === "teacher") return next("/teacher/scores");
    }
    return next();
  }

  // 2. 检查该路由是否需要登录
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);

  if (requiresAuth && !isAuthenticated) {
    ElMessage.warning("请先登录系统");
    return next("/");
  }

  // [修改点 5] 强制拦截：如果需要改密码，且当前不在改密码页，强制跳转
  if (isAuthenticated && mustChangePwd) {
    if (to.path !== "/change-password") {
      ElMessage.warning("为了账号安全，请先修改初始密码");
      return next("/change-password");
    }
  }

  // 3. 权限检查
  const requiredRole = to.matched.find((record) => record.meta.role)?.meta.role;

  if (requiredRole && requiredRole !== role) {
    ElMessage.error("无权访问该页面");
    return next("/");
  }

  // 4. 一切正常，放行
  next();
});
