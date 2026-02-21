<template>
  <div class="pwd-container">
    <div class="halo halo-a"></div>
    <div class="halo halo-b"></div>
    <el-card class="pwd-card">
      <template #header>
        <div class="title-wrap">
          <h2>为了账号安全，请修改初始密码</h2>
          <p>首次登录必须完成密码更新</p>
        </div>
      </template>
      <el-form :model="form" label-width="80px">
        <el-form-item label="旧密码">
          <el-input
            v-model="form.old_password"
            type="password"
            show-password
            placeholder="请输入当前密码（如123456）"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="form.new_password"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="form.confirm_password"
            type="password"
            show-password
            placeholder="再次输入新密码"
          />
        </el-form-item>
        <el-button
          type="primary"
          @click="handleSubmit"
          style="width: 100%; margin-top: 10px"
          >确认修改</el-button
        >
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { changePasswordApi } from "../api/auth";
import { ElMessage } from "element-plus";

const router = useRouter();
const form = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const handleSubmit = async () => {
  if (!form.old_password || !form.new_password) {
    return ElMessage.warning("请填写完整");
  }
  if (form.new_password !== form.confirm_password) {
    return ElMessage.warning("两次新密码输入不一致");
  }

  try {
    await changePasswordApi({
      old_password: form.old_password,
      new_password: form.new_password,
    });
    ElMessage.success("密码修改成功，请重新登录");
    localStorage.clear();
    router.push("/");
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "修改失败");
  }
};
</script>

<style scoped>
.pwd-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(140deg, #f3f9ff 0%, #e7f1fb 45%, #f9fbff 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.pwd-card {
  width: 400px;
  border-radius: 16px;
  z-index: 1;
}

.title-wrap {
  text-align: center;
}

.title-wrap h2 {
  margin: 0;
  color: #dd4a65;
  font-size: 22px;
}

.title-wrap p {
  margin: 8px 0 0;
  color: #6f88a4;
  font-size: 13px;
}

.halo {
  position: absolute;
  border-radius: 50%;
}

.halo-a {
  width: 300px;
  height: 300px;
  left: -90px;
  top: -90px;
  background: rgba(79, 173, 255, 0.24);
}

.halo-b {
  width: 320px;
  height: 320px;
  right: -120px;
  bottom: -120px;
  background: rgba(101, 209, 188, 0.24);
}
</style>
