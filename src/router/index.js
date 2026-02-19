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
    meta: { requiresAuth: true },
  },
  {
    path: "/admin",
    component: AdminDashboard,
    redirect: "/admin/approval",
    meta: { requiresAuth: true, role: "admin" },
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
        path: "score-trend",
        component: () => import("../views/admin/ScoreTrendComparison.vue"),
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
        path: "class-stats",
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
        path: "import-history",
        component: () => import("../views/admin/ImportHistory.vue"),
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
    meta: { requiresAuth: true, role: "teacher" },
    children: [
      {
        path: "scores",
        component: () => import("../views/teacher/ScoreEntry.vue"),
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 全局守卫：登录态校验、强制改密与角色权限控制。
router.beforeEach((to, from, next) => {
  let role = localStorage.getItem("user_role");
  let token = localStorage.getItem("access_token");

  if ((role && !token) || (!role && token)) {
    localStorage.clear();
    role = null;
    token = null;
  }

  const isAuthenticated = !!role && !!token;
  const mustChangePwd = localStorage.getItem("must_change_password") === "true";

  if (to.path === "/") {
    if (isAuthenticated) {
      if (mustChangePwd) return next("/change-password");

      if (role === "admin") return next("/admin/approval");
      if (role === "teacher") return next("/teacher/scores");
    }
    return next();
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);

  if (requiresAuth && !isAuthenticated) {
    ElMessage.warning("请先登录系统");
    return next("/");
  }

  // 强制修改密码期间仅允许访问改密页。
  if (isAuthenticated && mustChangePwd) {
    if (to.path !== "/change-password") {
      ElMessage.warning("为了账号安全，请先修改初始密码");
      return next("/change-password");
    }
  }

  const requiredRole = to.matched.find((record) => record.meta.role)?.meta.role;

  if (requiredRole && requiredRole !== role) {
    ElMessage.error("无权访问该页面");
    return next("/");
  }

  next();
});
