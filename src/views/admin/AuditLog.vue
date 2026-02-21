<template>
  <el-card>
    <template #header>
      <div class="header-row">
        <span class="title">敏感操作审计日志</span>
        <el-button type="primary" plain @click="fetchLogs">刷新</el-button>
      </div>
    </template>

    <el-alert
      v-if="!canView"
      title="仅超级管理员（adminwds）可查看此日志"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 12px"
    />

    <div class="filters">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索：操作者/学生/考试/班级"
        clearable
        style="width: 280px"
        @keyup.enter="handleSearch"
      />

      <el-select
        v-model="filters.action_type"
        clearable
        placeholder="操作类型"
        style="width: 150px"
      >
        <el-option label="成绩修改" value="score_update" />
      </el-select>

      <el-select v-model="filters.source" clearable placeholder="来源" style="width: 180px">
        <el-option label="教师手动保存" value="teacher_save_scores" />
        <el-option label="教师Excel导入" value="teacher_import_scores" />
        <el-option label="管理员手动保存" value="admin_score_entry_save" />
      </el-select>

      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />

      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <el-table :data="logs" border stripe v-loading="loading">
      <el-table-column prop="create_time" label="时间" width="170" />
      <el-table-column label="操作者" width="170">
        <template #default="scope">
          {{ scope.row.actor_real_name }} ({{ roleText(scope.row.actor_role) }})
        </template>
      </el-table-column>
      <el-table-column label="目标学生" width="160">
        <template #default="scope">
          {{ scope.row.target_student_name }} / {{ scope.row.target_student_no }}
        </template>
      </el-table-column>
      <el-table-column label="考试科目" min-width="190">
        <template #default="scope">
          {{ scope.row.exam_task_name }} - {{ scope.row.subject_name }}
        </template>
      </el-table-column>
      <el-table-column prop="class_name_snapshot" label="班级" width="120" />
      <el-table-column label="分数变化" width="150">
        <template #default="scope">
          <el-tag type="danger">{{ scope.row.old_value }}</el-tag>
          <span class="arrow">→</span>
          <el-tag type="success">{{ scope.row.new_value }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="source" label="来源" width="160" />
      <el-table-column prop="client_ip" label="IP" width="130" />
      <el-table-column prop="detail_text" label="明细" min-width="320" show-overflow-tooltip />
    </el-table>

    <div class="pager">
      <el-pagination
        background
        layout="total, prev, pager, next, sizes"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getAuditLogs } from "../../api/admin";

const loading = ref(false);
const canView = ref(true);
const logs = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const dateRange = ref([]);

const filters = ref({
  keyword: "",
  action_type: "",
  source: "",
});

const roleText = (role) => {
  if (role === "admin") return "管理员";
  if (role === "teacher") return "普通教师";
  return role || "-";
};

const fetchLogs = async () => {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.value.keyword || undefined,
      action_type: filters.value.action_type || undefined,
      source: filters.value.source || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
    };

    const res = await getAuditLogs(params);
    logs.value = res.data.items || [];
    total.value = res.data.total || 0;
    canView.value = true;
  } catch (err) {
    logs.value = [];
    total.value = 0;
    if (err.response?.status === 403) {
      canView.value = false;
      ElMessage.warning(err.response?.data?.msg || "无权查看审计日志");
      return;
    }
    ElMessage.error(err.response?.data?.msg || "审计日志加载失败");
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  page.value = 1;
  fetchLogs();
};

const resetFilters = () => {
  filters.value.keyword = "";
  filters.value.action_type = "";
  filters.value.source = "";
  dateRange.value = [];
  page.value = 1;
  fetchLogs();
};

const handlePageChange = (val) => {
  page.value = val;
  fetchLogs();
};

const handleSizeChange = (val) => {
  pageSize.value = val;
  page.value = 1;
  fetchLogs();
};

onMounted(fetchLogs);
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-weight: 700;
}

.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.arrow {
  margin: 0 8px;
  color: #909399;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
