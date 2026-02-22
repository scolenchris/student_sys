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
            <p class="browser-meta">
              当前浏览器：{{ browserInfo.name }} {{ browserInfo.version }}
            </p>
            <div class="browser-recommend">
              <p>推荐使用最新版 Microsoft Edge 或 Mozilla Firefox</p>
              <p>
                Edge 下载地址：
                <el-link
                  :href="edgeDownloadUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  type="primary"
                >
                  {{ edgeDownloadUrl }}
                </el-link>
              </p>
              <p>
                Firefox 下载地址：
                <el-link
                  :href="firefoxDownloadUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  type="primary"
                >
                  {{ firefoxDownloadUrl }}
                </el-link>
              </p>
            </div>
          </div>
        </template>

        <el-alert
          v-if="!browserInfo.supported"
          class="browser-alert"
          type="error"
          show-icon
          :closable="false"
          :title="browserInfo.message"
        />

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
              :disabled="!browserInfo.supported"
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
const edgeDownloadUrl = "https://www.microsoft.com/zh-cn/edge/download";
const firefoxDownloadUrl = "https://www.mozilla.org/zh-CN/firefox/new/";
const browserInfo = ref({
  name: "检测中",
  version: "-",
  supported: true,
  message: "",
});

const form = reactive({
  username: "",
  password: "",
  name: "",
  role: "teacher",
});

function getMajorVersion(versionText) {
  const major = Number(String(versionText).split(".")[0]);
  return Number.isFinite(major) ? major : 0;
}

function detectBrowser() {
  const ua = navigator.userAgent;
  const rules = {
    Chrome: 90,
    Edge: 90,
    Firefox: 88,
    Safari: 14,
    Opera: 76,
  };

  let name = "未知浏览器";
  let version = "0";

  if (/MSIE\s|Trident\//i.test(ua)) {
    const match = ua.match(/(MSIE\s|rv:)(\d+(\.\d+)?)/i);
    name = "IE";
    version = match?.[2] || "0";
  } else if (/Edg\/(\d+(\.\d+)?)/i.test(ua)) {
    const match = ua.match(/Edg\/(\d+(\.\d+)?)/i);
    name = "Edge";
    version = match?.[1] || "0";
  } else if (/Edge\/(\d+(\.\d+)?)/i.test(ua)) {
    const match = ua.match(/Edge\/(\d+(\.\d+)?)/i);
    name = "Edge Legacy";
    version = match?.[1] || "0";
  } else if (/Firefox\/(\d+(\.\d+)?)/i.test(ua)) {
    const match = ua.match(/Firefox\/(\d+(\.\d+)?)/i);
    name = "Firefox";
    version = match?.[1] || "0";
  } else if (/OPR\/(\d+(\.\d+)?)/i.test(ua)) {
    const match = ua.match(/OPR\/(\d+(\.\d+)?)/i);
    name = "Opera";
    version = match?.[1] || "0";
  } else if (/Chrome\/(\d+(\.\d+)?)/i.test(ua)) {
    const match = ua.match(/Chrome\/(\d+(\.\d+)?)/i);
    name = "Chrome";
    version = match?.[1] || "0";
  } else if (
    /Safari\/(\d+(\.\d+)?)/i.test(ua) &&
    /Version\/(\d+(\.\d+)?)/i.test(ua)
  ) {
    const match = ua.match(/Version\/(\d+(\.\d+)?)/i);
    name = "Safari";
    version = match?.[1] || "0";
  }

  let supported = true;
  let message = "";
  const major = getMajorVersion(version);

  if (name === "IE" || name === "Edge Legacy") {
    supported = false;
  } else if (Object.prototype.hasOwnProperty.call(rules, name)) {
    supported = major >= rules[name];
  }

  if (!supported) {
    message =
      `检测到 ${name} ${version}，当前浏览器不支持本系统。` +
      "请改用最新版 Microsoft Edge 或 Mozilla Firefox。";
  }

  return { name, version, supported, message };
}

// 初始化注册开关状态。请求失败时默认保持可注册，避免页面闪烁。
onMounted(async () => {
  browserInfo.value = detectBrowser();
  if (!browserInfo.value.supported) {
    ElMessage.error("当前浏览器版本不受支持，请更换后再登录");
  }

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

.browser-meta {
  margin-top: 10px;
  color: #3f5f7f;
}

.browser-recommend {
  margin-top: 8px;
  color: #4f6883;
  font-size: 12px;
  line-height: 1.7;
}

.browser-recommend p {
  margin: 4px 0;
  word-break: break-all;
}

.browser-alert {
  margin-bottom: 16px;
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
