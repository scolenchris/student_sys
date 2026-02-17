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
            @click="exportCSV"
            :disabled="displayTableData.length === 0"
          >
            <el-icon><Download /></el-icon> 导出CSV
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
        <el-button type="primary" @click="handleSearch" :loading="loading">
          <el-icon><Search /></el-icon> 查询
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
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import {
  getSubjects,
  getClasses,
  getExamNames,
  getScoreRankTrend,
} from "../../api/admin";
import { ElMessage } from "element-plus";
import { Search, Download } from "@element-plus/icons-vue";

const loading = ref(false);
const onlyChanged = ref(false);

const subjectOptions = ref([]);
const allClassOptions = ref([]);
const examNameOptions = ref([]);

const subjectColumns = ref([]);
const examsMeta = ref([]);
const tableData = ref([]);
const warnings = ref([]);

const query = reactive({
  entry_year: null,
  class_ids: [],
  exam_names: [],
  subject_ids: [],
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

const displayTableData = computed(() => {
  if (!onlyChanged.value) return tableData.value;
  return tableData.value.filter((row) => row.has_change);
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

const handleSearch = async () => {
  if (!query.entry_year) return ElMessage.warning("请选择年级");
  if (query.exam_names.length < 2)
    return ElMessage.warning("请至少选择2次考试");
  if (query.subject_ids.length === 0)
    return ElMessage.warning("请至少选择一个科目");

  loading.value = true;
  try {
    const res = await getScoreRankTrend({
      entry_year: query.entry_year,
      class_ids: query.class_ids,
      exam_names: query.exam_names,
      subject_ids: query.subject_ids,
    });

    subjectColumns.value = res.data.subjects || [];
    examsMeta.value = res.data.exams || [];
    tableData.value = res.data.rows || [];
    warnings.value = res.data.warnings || [];

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

const getExamData = (row, examName) => {
  return row?.exam_data?.[examName] || {};
};

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

const toCSVCell = (value) => {
  const str = value === null || value === undefined ? "-" : String(value);
  return `"${str.replace(/"/g, '""')}"`;
};

const exportCSV = () => {
  if (!displayTableData.value.length) return;

  const headers = ["学号", "姓名", "班级", "状态"];
  examsMeta.value.forEach((exam) => {
    headers.push(
      `${exam.name}-科目成绩`,
      `${exam.name}-总分`,
      `${exam.name}-分差`,
      `${exam.name}-级排`,
      `${exam.name}-级排变化`,
      `${exam.name}-班排`,
      `${exam.name}-班排变化`,
    );
  });

  let csvContent =
    "data:text/csv;charset=utf-8,\ufeff" + headers.map(toCSVCell).join(",") + "\n";

  displayTableData.value.forEach((row) => {
    const line = [row.student_id, row.name, row.class_name, row.status];

    examsMeta.value.forEach((exam) => {
      const examData = getExamData(row, exam.name);
      const scoreText = subjectColumns.value
        .map((sub) => `${sub}:${examData.scores?.[sub] ?? "-"}`)
        .join("；");

      line.push(
        scoreText,
        examData.total ?? "-",
        formatDelta(examData.total_change),
        examData.grade_rank ?? "-",
        formatDelta(examData.grade_rank_change),
        examData.class_rank ?? "-",
        formatDelta(examData.class_rank_change),
      );
    });

    csvContent += line.map(toCSVCell).join(",") + "\n";
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute(
    "download",
    `${query.entry_year}级_成绩与排名变化比较_${new Date().getTime()}.csv`,
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

onMounted(initData);
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
</style>
