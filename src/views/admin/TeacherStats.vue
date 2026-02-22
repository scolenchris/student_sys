<template>
  <el-card>
    <template #header>
      <div class="header-row">
        <span>教师教学质量统计</span>
        <el-button
          type="success"
          @click="exportToExcel"
          :loading="exporting"
          :disabled="tableData.length === 0"
        >
          <el-icon><Download /></el-icon> 导出教师统计Excel
        </el-button>
      </div>
    </template>

    <el-form :inline="true" :model="query" class="filter-form">
      <el-form-item label="学年">
        <el-select
          v-model="query.academic_year"
          placeholder="选择学年"
          style="width: 140px"
        >
          <el-option
            v-for="y in academicYearOptions"
            :key="y"
            :label="`${y}学年`"
            :value="y"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="年级">
        <el-select
          v-model="query.entry_year"
          placeholder="选择年级"
          style="width: 120px"
          @change="handleEntryYearChange"
        >
          <el-option
            v-for="y in gradeOptions"
            :key="y.year"
            :label="y.label"
            :value="y.year"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="考试批次">
        <el-select
          v-model="query.exam_name"
          placeholder="请先选年级"
          :disabled="!query.entry_year"
          style="width: 180px"
        >
          <el-option
            v-for="name in examNameOptions"
            :key="name"
            :label="name"
            :value="name"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="fetchData" :loading="loading">
          <el-icon><Search /></el-icon> 生成教师统计
        </el-button>
      </el-form-item>

      <div class="threshold-area">
        <span class="label">统计标准：</span>
        <el-form-item
          label="优秀率 ≥"
          style="margin-bottom: 0; margin-right: 15px"
        >
          <el-input-number
            v-model="query.threshold_excellent"
            :min="1"
            :max="100"
            size="small"
            style="width: 80px"
          />
          %
        </el-form-item>
        <el-form-item label="合格率 ≥" style="margin-bottom: 0">
          <el-input-number
            v-model="query.threshold_pass"
            :min="1"
            :max="100"
            size="small"
            style="width: 80px"
          />
          %
        </el-form-item>
      </div>
    </el-form>

    <el-table
      :data="tableData"
      border
      stripe
      v-loading="loading"
      height="600"
      :row-class-name="tableRowClassName"
    >
      <el-table-column prop="name" label="姓名" width="140" fixed />
      <el-table-column prop="subject" label="学科" width="80" />
      <el-table-column
        prop="exam_name"
        label="成绩类别"
        width="120"
        show-overflow-tooltip
      />
      <el-table-column
        prop="full_score"
        label="满分"
        width="60"
        align="center"
      />

      <el-table-column
        prop="classes"
        label="任教班级"
        min-width="180"
        show-overflow-tooltip
      />

      <el-table-column label="人数详情" align="center">
        <el-table-column prop="total_people" label="学生" width="60" />
        <el-table-column prop="exam_people" label="考试" width="60" />
      </el-table-column>

      <el-table-column label="平均分" align="center">
        <el-table-column prop="avg_score" label="得分" width="80">
          <template #default="scope">
            <span style="font-weight: bold; color: #409eff">{{
              scope.row.avg_score
            }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rank" label="名次" width="60" />
        <el-table-column prop="grade_ratio" label="与级比" width="70" />
      </el-table-column>

      <el-table-column label="优秀情况" align="center">
        <el-table-column prop="excellent_count" label="人数" width="60" />
        <el-table-column prop="excellent_rate" label="率%" width="70">
          <template #default="scope">{{ scope.row.excellent_rate }}%</template>
        </el-table-column>
      </el-table-column>

      <el-table-column label="合格情况" align="center">
        <el-table-column prop="pass_count" label="人数" width="60" />
        <el-table-column prop="pass_rate" label="率%" width="70">
          <template #default="scope">{{ scope.row.pass_rate }}%</template>
        </el-table-column>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import {
  getTeacherScoreStats,
  exportTeacherScoreStatsExcel,
  getClasses,
  getExamNames,
} from "../../api/admin";
import { ElMessage } from "element-plus";
import { Search, Download } from "@element-plus/icons-vue";

const loading = ref(false);
const exporting = ref(false);
const tableData = ref([]);
const allClasses = ref([]);
const examNameOptions = ref([]);

// 学年按 8 月切换：8 月前视为上一学年，8 月及以后视为当前年。
const now = new Date();
const currentYear =
  now.getMonth() >= 7 ? now.getFullYear() : now.getFullYear() - 1;

const query = reactive({
  academic_year: currentYear,
  entry_year: null,
  exam_name: "",
  threshold_excellent: 85,
  threshold_pass: 60,
});

const academicYearOptions = computed(() => {
  const years = [];
  for (let i = -2; i < 3; i++) years.push(currentYear + i);
  return years.sort((a, b) => b - a);
});

const gradeOptions = computed(() => {
  if (!allClasses.value.length) return [];
  const years = [...new Set(allClasses.value.map((c) => c.entry_year))];
  return years.sort((a, b) => b - a).map((y) => ({ year: y, label: `${y}级` }));
});

const init = async () => {
  const res = await getClasses();
  allClasses.value = res.data;
};

const handleEntryYearChange = async (val) => {
  query.exam_name = "";
  if (!val) return;
  try {
    const res = await getExamNames(val);
    examNameOptions.value = res.data;
  } catch (e) {
    ElMessage.error("获取考试列表失败");
  }
};

const fetchData = async () => {
  if (!query.academic_year || !query.entry_year || !query.exam_name) {
    return ElMessage.warning("请选择学年、年级和考试批次");
  }
  loading.value = true;
  try {
    const res = await getTeacherScoreStats(query);
    tableData.value = res.data;
    if (tableData.value.length === 0) {
      ElMessage.info("该条件下无数据");
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "统计失败");
  } finally {
    loading.value = false;
  }
};

const tableRowClassName = ({ row }) => {
  if (row.name.includes("总计")) {
    return "total-row";
  }
  return "";
};

const exportToExcel = async () => {
  if (!query.academic_year || !query.entry_year || !query.exam_name) {
    return ElMessage.warning("请先选择学年、年级和考试批次");
  }

  exporting.value = true;
  try {
    const res = await exportTeacherScoreStatsExcel(query);
    const blob = new Blob([res.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `${query.entry_year}级_${query.exam_name}_教师教学统计.xlsx`,
    );
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

onMounted(init);
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-form {
  background-color: #f8f9fa;
  padding: 15px 15px 5px 15px;
  border-radius: 4px;
  margin-bottom: 10px;
}
.threshold-area {
  display: inline-flex;
  align-items: center;
  margin-left: 20px;
  padding-left: 20px;
  border-left: 1px solid #dcdfe6;
}
.label {
  font-size: 14px;
  color: #606266;
  font-weight: bold;
  margin-right: 10px;
}
:deep(.total-row) {
  background-color: #f0f9eb !important;
  font-weight: bold;
}
</style>
