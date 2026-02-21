<template>
  <div class="login-page">
    <div class="shape shape-a"></div>
    <div class="shape shape-b"></div>
    <div class="shape shape-c"></div>

    <div class="login-shell">
      <section class="hero-panel">
        <p class="hero-tag">Campus Ops</p>
        <h1>学生成绩管理系统</h1>
        <p class="hero-desc">
          聚合审核、档案、成绩、统计与回退流程，统一管理教学数据。
        </p>
        <ul class="hero-list">
          <li>教师与账号状态联动管理</li>
          <li>成绩导入校验与批次回退</li>
          <li>班级与教师教学统计分析</li>
        </ul>
      </section>

      <el-card class="login-card">
        <template #header>
          <div class="card-header">
            <h2>{{ isRegister ? "新用户注册申请" : "欢迎登录" }}</h2>
            <p>{{ isRegister ? "提交后等待管理员审核" : "请输入账号密码进入系统" }}</p>
          </div>
        </template>

        <el-form :model="form" label-width="88px">
          <div v-if="isRegister">
            <el-form-item label="真实姓名">
              <el-input v-model="form.name" placeholder="将用于建立教师档案" />
            </el-form-item>
            <el-form-item label="申请身份">
              <el-radio-group v-model="form.role">
                <el-radio label="teacher">任课教师</el-radio>
                <el-radio label="admin">管理员</el-radio>
              </el-radio-group>
            </el-form-item>
          </div>

          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="请输入工号/用户名" />
          </el-form-item>

          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入登录密码"
            />
          </el-form-item>

          <div class="btn-group">
            <el-button
              class="submit-btn"
              type="primary"
              @click="handleSubmit"
              :loading="loading"
            >
              {{ isRegister ? "提交申请" : "立即登录" }}
            </el-button>

            <div class="helper-line">
              <template v-if="!isRegister">
                <el-link
                  v-if="allowRegister"
                  type="primary"
                  @click="isRegister = true"
                >
                  没有账号？去注册申请
                </el-link>
                <span
                  v-else
                  class="disabled-tip"
                  title="管理员已关闭注册"
                >
                  当前系统已关闭注册
                </span>
              </template>
              <el-link v-else @click="isRegister = false">返回登录</el-link>
            </div>
          </div>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { loginApi, registerApi, getRegisterConfig } from "../api/auth";
import { ElMessage } from "element-plus";

const router = useRouter();
const isRegister = ref(false);
const loading = ref(false);
const allowRegister = ref(true);

const form = reactive({
  username: "",
  password: "",
  name: "",
  role: "teacher",
});

// 初始化注册开关状态。请求失败时默认保持可注册，避免页面闪烁。
onMounted(async () => {
  try {
    const res = await getRegisterConfig();
    allowRegister.value = res.data.allow_register;
  } catch (e) {
    console.error("无法获取系统配置", e);
  }
});

const handleSubmit = async () => {
  if (!form.username || !form.password)
    return ElMessage.warning("请填写完整信息");
  if (isRegister.value && !form.name)
    return ElMessage.warning("请填写真实姓名");

  loading.value = true;
  try {
    if (isRegister.value) {
      const res = await registerApi(form);
      ElMessage.success(res.data.msg);
      isRegister.value = false;
    } else {
      const res = await loginApi({
        username: form.username,
        password: form.password,
      });

      if (!res.data.access_token) {
        return ElMessage.error("登录凭证缺失，请联系管理员检查服务端配置");
      }

      localStorage.setItem("access_token", res.data.access_token);
      localStorage.setItem("user_id", res.data.user_id);
      localStorage.setItem("user_role", res.data.role);
      localStorage.setItem("username", res.data.username);

      // 记录强制改密标记，路由守卫会据此拦截跳转。
      if (res.data.must_change_password) {
        localStorage.setItem("must_change_password", "true");
      } else {
        localStorage.removeItem("must_change_password");
      }

      ElMessage.success("登录成功");

      setTimeout(() => {
        if (res.data.must_change_password) {
          router.push("/change-password");
        } else {
          if (res.data.role === "admin") router.push("/admin/overview");
          else router.push("/teacher/scores");
        }
      }, 100);
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || "操作失败");
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(140deg, #f3f9ff 0%, #e7f1fb 45%, #f9fbff 100%);
  padding: 20px;
}

.shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
}

.shape-a {
  width: 320px;
  height: 320px;
  left: -80px;
  top: -80px;
  background: rgba(63, 156, 255, 0.22);
}

.shape-b {
  width: 260px;
  height: 260px;
  right: 10%;
  top: 8%;
  background: rgba(76, 211, 184, 0.22);
}

.shape-c {
  width: 360px;
  height: 360px;
  right: -120px;
  bottom: -120px;
  background: rgba(255, 169, 114, 0.22);
}

.login-shell {
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 20px;
  z-index: 1;
}

.hero-panel {
  background: linear-gradient(160deg, #0f4f84 0%, #1473a6 55%, #1790a9 100%);
  border-radius: 18px;
  padding: 30px;
  color: #f8fbff;
  box-shadow: 0 16px 30px rgba(21, 67, 103, 0.22);
}

.hero-tag {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 1px;
  margin: 0;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
}

.hero-panel h1 {
  margin: 14px 0 10px;
  font-size: 34px;
  line-height: 1.2;
}

.hero-desc {
  margin: 0;
  color: rgba(245, 249, 255, 0.9);
  line-height: 1.7;
}

.hero-list {
  margin: 18px 0 0;
  padding-left: 18px;
  line-height: 1.9;
  color: #f0f8ff;
}

.login-card {
  border-radius: 18px;
}

.card-header h2 {
  margin: 0;
  color: #0f3f69;
}

.card-header p {
  margin: 8px 0 0;
  color: #6b849f;
  font-size: 13px;
}

.btn-group {
  margin-top: 4px;
}

.submit-btn {
  width: 100%;
  height: 42px;
  border: none;
  background: linear-gradient(90deg, #1678cf, #1ba3bf);
}

.helper-line {
  margin-top: 14px;
  font-size: 14px;
  text-align: center;
}

.disabled-tip {
  color: #9cb0c6;
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    display: none;
  }
}
</style>
