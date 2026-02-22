<template>
  <el-card>
    <template #header>
      <h3>
        <el-icon style="vertical-align: middle"><User /></el-icon>
        用户审核与状态管理
      </h3>
    </template>

    <el-table :data="pendingUsers" style="width: 100%" border stripe>
      <el-table-column prop="username" label="用户名/工号" width="150" />
      <el-table-column prop="name" label="姓名" width="120" />

      <el-table-column label="当前状态" width="140" align="center">
        <template #default="scope">
          <el-tag
            v-if="scope.row.current_status === '新注册'"
            type="primary"
            effect="light"
          >
            新注册
          </el-tag>

          <el-tag
            v-else-if="
              ['退休', '离职', '非在职'].includes(scope.row.current_status)
            "
            type="info"
            effect="plain"
          >
            {{ scope.row.current_status }} (已冻结)
          </el-tag>

          <el-tag v-else type="warning">{{ scope.row.current_status }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="role" label="申请角色" width="120" align="center">
        <template #default="scope">
          <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'success'">
            {{ scope.row.role === "admin" ? "管理员" : "老师" }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" min-width="200">
        <template #default="scope">
          <el-button
            v-if="scope.row.current_status === '新注册'"
            type="success"
            size="small"
            @click="handleApprove(scope.row.id)"
          >
            通过审核
          </el-button>

          <el-popconfirm
            v-else
            :title="`确定返聘该【${scope.row.current_status}】教师并恢复其账号吗？`"
            @confirm="handleApprove(scope.row.id)"
          >
            <template #reference>
              <el-button type="warning" size="small">恢复账号并返聘</el-button>
            </template>
          </el-popconfirm>

          <el-popconfirm
            v-if="scope.row.current_status === '新注册'"
            title="确定拒绝并删除该申请吗？"
            @confirm="handleReject(scope.row.id)"
          >
            <template #reference>
              <el-button type="danger" size="small" style="margin-left: 10px"
                >拒绝并删除申请</el-button
              >
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getPendingUsers, approveUser, rejectUser } from "../../api/admin";
import { ElMessage } from "element-plus";
import { User } from "@element-plus/icons-vue";

const pendingUsers = ref([]);

const fetchData = async () => {
  try {
    const res = await getPendingUsers();
    pendingUsers.value = res.data;
  } catch (err) {
    ElMessage.error("获取列表失败");
  }
};

const handleApprove = async (id) => {
  try {
    await approveUser(id);
    ElMessage.success("操作成功");
    fetchData();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "操作失败");
  }
};

const handleReject = async (id) => {
  try {
    await rejectUser(id);
    ElMessage.info("已拒绝该申请");
    fetchData();
  } catch (err) {
    ElMessage.error("操作失败");
  }
};

onMounted(fetchData);
</script>
