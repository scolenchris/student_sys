<template>
  <el-card>
    <template #header>
      <h3>系统全局设置</h3>
    </template>

    <el-form label-width="120px" style="max-width: 500px; margin-top: 20px">
      <el-form-item label="开放用户注册">
        <el-switch
          v-model="settings.allow_register"
          active-text="开启"
          inactive-text="关闭"
          @change="handleUpdate"
        />
        <div style="font-size: 12px; color: #909399; margin-left: 10px">
          关闭后，登录页将隐藏注册入口，且 API 会拒绝注册请求。
        </div>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { getSystemSettings, updateSystemSettings } from "../../api/admin";
import { ElMessage } from "element-plus";

const settings = reactive({
  allow_register: true,
});

const fetchSettings = async () => {
  try {
    const res = await getSystemSettings();
    settings.allow_register = res.data.allow_register;
  } catch (e) {
    ElMessage.error("获取设置失败");
  }
};

const handleUpdate = async () => {
  try {
    await updateSystemSettings({ allow_register: settings.allow_register });
    ElMessage.success("设置已更新");
  } catch (e) {
    // 失败回滚开关状态
    settings.allow_register = !settings.allow_register;
    ElMessage.error("更新失败");
  }
};

onMounted(fetchSettings);
</script>
