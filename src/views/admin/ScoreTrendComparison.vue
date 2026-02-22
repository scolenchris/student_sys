<template>
  <el-card class="trend-card">
    <template #header>
      <div class="header-row">
        <span>成绩与排名变化比较</span>
        <div class="header-actions">
          <el-switch v-model="onlyChanged" active-text="仅看有变化" />
          <el-button
            type="success"
            plain
            @click="exportExcel"
            :loading="exporting"
            :disabled="total === 0"
          >
            <el-icon><Download /></el-icon> 导出变化分析Excel
          </el-button>
        </div>
      </div>
    </template>

    <el-form :inline="true" class="filter-bar">
      <el-form-item label="年级">
        <el-select
          v-model="query.entry_year"
          placeholder="选择年级"
          style="width: 140px"
          @change="handleYearChange"
        >
          <el-option
            v-for="y in gradeOptions"
            :key="y.year"
            :label="y.label"
            :value="y.year"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="班级">
        <el-select
          v-model="query.class_ids"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="默认全级"
          style="width: 230px"
          :disabled="!query.entry_year"
        >
          <el-option
            v-for="c in filteredClassOptions"
            :key="c.id"
            :label="`${c.grade_name}(${c.class_num})班`"
            :value="c.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="考试批次">
        <el-select
          v-model="query.exam_names"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="至少选择2次考试"
          style="width: 260px"
          :disabled="!query.entry_year"
        >
          <el-option
            v-for="name in examNameOptions"
            :key="name"
            :label="name"
            :value="name"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="科目">
        <el-select
          v-model="query.subject_ids"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择统计科目"
          style="width: 240px"
        >
          <el-option
            v-for="s in subjectOptions"
            :key="s.id"
            :label="s.name"
            :value="s.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSearch(true)" :loading="loading">
          <el-icon><Search /></el-icon> 生成变化分析
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="说明"
      description="成绩变化=本次总分-上次总分；排名变化=上次排名-本次排名（正数代表进步）。"
      style="margin-bottom: 10px"
    />

    <el-alert
      v-if="warnings.length"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 10px"
    >
      <template #title>注意</template>
      <template #default>
        <div v-for="(w, idx) in warnings" :key="idx">{{ w }}</div>
      </template>
    </el-alert>

    <el-table
      :data="displayTableData"
      border
      stripe
      height="620"
      v-loading="loading"
      style="width: 100%"
    >
      <el-table-column prop="student_id" label="学号" width="120" fixed />
      <el-table-column prop="name" label="姓名" width="100" fixed />
      <el-table-column
        prop="class_name"
        label="班级"
        width="110"
        fixed
        show-overflow-tooltip
      />

      <el-table-column
        v-for="exam in examsMeta"
        :key="exam.name"
        :label="exam.name"
        align="center"
      >
        <template #header>
          <div class="exam-header">
            <div>{{ exam.name }}</div>
            <div class="exam-sub">总满分 {{ exam.full_score }}</div>
          </div>
        </template>

        <el-table-column label="科目成绩" min-width="190" align="left">
          <template #default="scope">
            <div class="subject-lines">
              <div
                v-for="sub in subjectColumns"
                :key="`${scope.row.student_id}-${exam.name}-${sub}`"
              >
                {{ sub }}: {{ getExamData(scope.row, exam.name).scores?.[sub] ?? "-" }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="总分" width="85" align="center">
          <template #default="scope">
            {{ getExamData(scope.row, exam.name).total ?? "-" }}
          </template>
        </el-table-column>

        <el-table-column label="分差" width="80" align="center">
          <template #default="scope">
            <span
              :class="
                getDeltaClass(getExamData(scope.row, exam.name).total_change)
              "
            >
              {{ formatDelta(getExamData(scope.row, exam.name).total_change) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="级排" width="70" align="center">
          <template #default="scope">
            {{ getExamData(scope.row, exam.name).grade_rank ?? "-" }}
          </template>
        </el-table-column>

        <el-table-column label="级排变化" width="90" align="center">
          <template #default="scope">
            <span
              :class="
                getDeltaClass(getExamData(scope.row, exam.name).grade_rank_change)
              "
            >
              {{ formatDelta(getExamData(scope.row, exam.name).grade_rank_change) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="班排" width="70" align="center">
          <template #default="scope">
            {{ getExamData(scope.row, exam.name).class_rank ?? "-" }}
          </template>
        </el-table-column>

        <el-table-column label="班排变化" width="90" align="center">
          <template #default="scope">
            <span
              :class="
                getDeltaClass(getExamData(scope.row, exam.name).class_rank_change)
              "
            >
              {{ formatDelta(getExamData(scope.row, exam.name).class_rank_change) }}
            </span>
          </template>
        </el-table-column>
      </el-table-column>
    </el-table>

    <div class="pager-wrap">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import {
  getSubjects,
  getClasses,
  getExamNames,
  getScoreRankTrend,
  exportScoreRankTrendExcel,
} from "../../api/admin";
import { ElMessage } from "element-plus";
import { Search, Download } from "@element-plus/icons-vue";

const loading = ref(false);
const exporting = ref(false);
const onlyChanged = ref(false);

const subjectOptions = ref([]);
const allClassOptions = ref([]);
const examNameOptions = ref([]);

const subjectColumns = ref([]);
const examsMeta = ref([]);
const tableData = ref([]);
const warnings = ref([]);
const total = ref(0);

const query = reactive({
  entry_year: null,
  class_ids: [],
  exam_names: [],
  subject_ids: [],
  page: 1,
  page_size: 20,
});

const gradeOptions = computed(() => {
  if (!allClassOptions.value.length) return [];
  const years = [...new Set(allClassOptions.value.map((c) => c.entry_year))];
  return years.sort((a, b) => b - a).map((y) => ({ year: y, label: `${y}级` }));
});

const filteredClassOptions = computed(() => {
  if (!query.entry_year) return [];
  return allClassOptions.value.filter((c) => c.entry_year === query.entry_year);
});

// 列表分页后端已按 only_changed 过滤，这里直接展示当前页数据。
const displayTableData = computed(() => {
  return tableData.value;
});

const initData = async () => {
  try {
    const [sRes, cRes] = await Promise.all([getSubjects(), getClasses()]);
    subjectOptions.value = sRes.data || [];
    allClassOptions.value = cRes.data || [];
  } catch (err) {
    ElMessage.error("初始化筛选项失败");
  }
};

const resetResult = () => {
  subjectColumns.value = [];
  examsMeta.value = [];
  tableData.value = [];
  warnings.value = [];
  total.value = 0;
  query.page = 1;
};

const handleYearChange = async (val) => {
  query.class_ids = [];
  query.exam_names = [];
  examNameOptions.value = [];
  resetResult();

  if (!val) return;
  try {
    const res = await getExamNames(val);
    examNameOptions.value = Array.isArray(res.data) ? res.data : [];
  } catch (err) {
    ElMessage.error("获取考试列表失败");
  }
};

const handleSearch = async (resetPage = false) => {
  if (!query.entry_year) return ElMessage.warning("请选择年级");
  if (query.exam_names.length < 2)
    return ElMessage.warning("请至少选择2次考试");
  if (query.subject_ids.length === 0)
    return ElMessage.warning("请至少选择一个科目");
  if (resetPage) {
    query.page = 1;
  }

  loading.value = true;
  try {
    const res = await getScoreRankTrend({
      entry_year: query.entry_year,
      class_ids: query.class_ids,
      exam_names: query.exam_names,
      subject_ids: query.subject_ids,
      only_changed: onlyChanged.value,
      paged: true,
      page: query.page,
      page_size: query.page_size,
    });

    subjectColumns.value = res.data?.subjects || [];
    examsMeta.value = res.data?.exams || [];
    tableData.value = res.data?.rows || [];
    warnings.value = res.data?.warnings || [];
    total.value = res.data?.total || 0;

    if (warnings.value.length > 0) {
      ElMessage.warning("部分考试缺少科目任务，已按0分计算对应科目");
    }
    if (examsMeta.value.length < 2) {
      ElMessage.warning("当前可比较的考试不足2次，变化列可能为空");
    }
    if (tableData.value.length === 0) {
      ElMessage.info("当前筛选条件下没有可展示的数据");
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "查询失败");
  } finally {
    loading.value = false;
  }
};

const handlePageChange = () => {
  handleSearch(false);
};

const handlePageSizeChange = () => {
  query.page = 1;
  handleSearch(false);
};

const getExamData = (row, examName) => {
  return row?.exam_data?.[examName] || {};
};

// 变化值统一格式：
// 正数显示 +n，0 显示 0，空值和非法值显示 -。
const formatDelta = (value) => {
  if (value === null || value === undefined) return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  if (Math.abs(num) < 1e-9) return "0";
  return num > 0 ? `+${num}` : `${num}`;
};

const getDeltaClass = (value) => {
  if (value === null || value === undefined) return "delta-neutral";
  const num = Number(value);
  if (Number.isNaN(num) || Math.abs(num) < 1e-9) return "delta-neutral";
  return num > 0 ? "delta-up" : "delta-down";
};

const exportExcel = async () => {
  if (!query.entry_year) return ElMessage.warning("请选择年级");
  if (query.exam_names.length < 2)
    return ElMessage.warning("请至少选择2次考试");
  if (query.subject_ids.length === 0)
    return ElMessage.warning("请至少选择一个科目");

  exporting.value = true;
  try {
    const res = await exportScoreRankTrendExcel({
      entry_year: query.entry_year,
      class_ids: query.class_ids,
      exam_names: query.exam_names,
      subject_ids: query.subject_ids,
      only_changed: onlyChanged.value,
    });

    const blob = new Blob([res.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;

    const suffix = onlyChanged.value ? "_仅变化" : "";
    link.setAttribute("download", `${query.entry_year}级_成绩变化比较${suffix}.xlsx`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "导出失败");
  } finally {
    exporting.value = false;
  }
};

onMounted(initData);

watch(onlyChanged, () => {
  if (!query.entry_year || query.exam_names.length < 2 || query.subject_ids.length === 0) {
    return;
  }
  handleSearch(true);
});
</script>

<style scoped>
.trend-card {
  min-height: 82vh;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.filter-bar {
  margin-bottom: 10px;
  padding: 14px 14px 0 14px;
  background-color: #f5f7fa;
  border-radius: 4px;
}
.subject-lines {
  line-height: 1.4;
  font-size: 12px;
}
.exam-header {
  line-height: 1.25;
}
.exam-sub {
  font-size: 12px;
  color: #909399;
}
.delta-up {
  color: #67c23a;
  font-weight: 600;
}
.delta-down {
  color: #f56c6c;
  font-weight: 600;
}
.delta-neutral {
  color: #909399;
}
.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
