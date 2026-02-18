<template>
  <div class="pwd-container">
    <el-card class="pwd-card">
      <template #header>
        <h2 style="text-align: center; color: #f56c6c">
          为了账号安全，请修改初始密码
        </h2>
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
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}
.pwd-card {
  width: 400px;
}
</style>
