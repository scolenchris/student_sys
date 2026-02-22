<template>
  <div class="page-wrap">
    <el-card>
      <template #header>
        <div class="header-bar">
          <span class="title">导入记录与回退</span>
          <div class="tools">
            <el-select
              v-model="query.import_type"
              clearable
              placeholder="按类型筛选"
              style="width: 180px"
              @change="handleFilterChange"
            >
              <el-option label="学生名单" value="student" />
              <el-option label="教师信息" value="teacher" />
              <el-option label="任课分配" value="course_assign" />
              <el-option label="成绩" value="score" />
            </el-select>
            <el-button type="primary" @click="fetchHistory">刷新导入记录</el-button>
          </div>
        </div>
      </template>

      <el-table :data="rows" border v-loading="loading">
        <el-table-column prop="id" label="批次ID" width="90" />
        <el-table-column prop="import_type_label" label="类型" width="120" />
        <el-table-column prop="source_filename" label="文件名" min-width="170" />
        <el-table-column label="导入范围" min-width="200">
          <template #default="{ row }">
            {{ formatScope(row.scope) }}
          </template>
        </el-table-column>
        <el-table-column label="摘要" min-width="220">
          <template #default="{ row }">
            {{ formatSummary(row.summary) }}
          </template>
        </el-table-column>
        <el-table-column label="导入时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <span v-if="row.can_rollback">可回退</span>
            <span v-else>已回退</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              link
              :disabled="!row.can_rollback"
              @click="handleRollback(row)"
            >
              回退该批次
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-wrap">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchHistory"
          @current-change="fetchHistory"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getImportHistory, rollbackImportBatch } from "../../api/admin";

const loading = ref(false);
const rows = ref([]);
const total = ref(0);

const query = reactive({
  page: 1,
  page_size: 20,
  import_type: "",
});

const formatTime = (v) => {
  if (!v) return "-";
  return new Date(v).toLocaleString("zh-CN", { hour12: false });
};

const formatScope = (scope = {}) => {
  if (!scope || Object.keys(scope).length === 0) return "-";

  const parts = [];
  if (scope.academic_year) parts.push(`学年:${scope.academic_year}`);
  if (scope.entry_year) parts.push(`年级:${scope.entry_year}级`);
  if (scope.exam_name) parts.push(`考试:${scope.exam_name}`);
  if (Array.isArray(scope.subject_ids) && scope.subject_ids.length > 0) {
    parts.push(`科目数:${scope.subject_ids.length}`);
  }
  if (Array.isArray(scope.class_ids) && scope.class_ids.length > 0) {
    parts.push(`班级数:${scope.class_ids.length}`);
  }
  return parts.join("，") || "-";
};

const formatSummary = (summary = {}) => {
  if (!summary || Object.keys(summary).length === 0) return "-";

  const parts = [];
  if (summary.added !== undefined) parts.push(`新增:${summary.added}`);
  if (summary.updated !== undefined) parts.push(`更新:${summary.updated}`);
  if (summary.updated_classes !== undefined) {
    parts.push(`班级:${summary.updated_classes}`);
  }
  if (summary.frozen !== undefined) parts.push(`冻结:${summary.frozen}`);
  if (summary.warning_count !== undefined) {
    parts.push(`警告:${summary.warning_count}`);
  }
  if (summary.missing_student_count !== undefined) {
    parts.push(`缺失名单:${summary.missing_student_count}`);
  }
  return parts.join("，") || "-";
};

const fetchHistory = async () => {
  loading.value = true;
  try {
    const res = await getImportHistory(query);
    rows.value = res.data.items || [];
    total.value = res.data.total || 0;
  } catch (err) {
    ElMessage.error(err?.response?.data?.msg || "获取导入记录失败");
  } finally {
    loading.value = false;
  }
};

const handleFilterChange = () => {
  query.page = 1;
  fetchHistory();
};

const handleRollback = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认回退批次 #${row.id} 吗？该操作会恢复该次导入前的数据状态。`,
      "确认回退",
      {
        type: "warning",
      }
    );
  } catch {
    return;
  }

  try {
    const res = await rollbackImportBatch(row.id);
    ElMessage.success(res.data.msg || "回退成功");
    fetchHistory();
  } catch (err) {
    ElMessage.error(err?.response?.data?.msg || "回退失败");
  }
};

onMounted(fetchHistory);
</script>

<style scoped>
.page-wrap {
  padding: 12px;
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.tools {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
