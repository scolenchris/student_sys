<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 style="text-align: center">
          {{ isRegister ? "新用户注册申请" : "学生管理系统登录" }}
        </h2>
      </template>

      <el-form :model="form" label-width="80px">
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
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>

        <div class="btn-group">
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="loading"
            style="width: 100%"
          >
            {{ isRegister ? "提交申请" : "立即登录" }}
          </el-button>

          <div style="margin-top: 15px; font-size: 14px">
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
                style="color: #909399; cursor: not-allowed"
                title="管理员已关闭注册"
              >
                (系统当前已关闭注册)
              </span>
            </template>
            <el-link v-else @click="isRegister = false"> 返回登录 </el-link>
          </div>
        </div>
      </el-form>
    </el-card>
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
          if (res.data.role === "admin") router.push("/admin/approval");
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
