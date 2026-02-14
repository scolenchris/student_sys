<template>
  <el-card class="stats-card">
    <template #header>
      <div class="header-row">
        <span>班级成绩统计分析</span>
        <el-tooltip
          content="统计仅包含'在读'学生；'考试人数'指至少有一科有效成绩的学生；缺考不计入平均分分母(视具体后端逻辑而定)"
          placement="top"
        >
          <el-icon><InfoFilled /></el-icon>
        </el-tooltip>
      </div>
    </template>

    <el-form :inline="true" :model="query" class="filter-form">
      <div class="filter-row">
        <el-form-item label="年级">
          <el-select
            v-model="query.entry_year"
            placeholder="选择年级"
            @change="handleYearChange"
            style="width: 140px"
          >
            <el-option
              v-for="y in gradeOptions"
              :key="y.year"
              :label="y.label"
              :value="y.year"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="考试名称">
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

        <el-form-item label="统计科目">
          <el-select
            v-model="query.subject_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择科目(多选)"
            style="width: 220px"
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
            <el-icon><Search /></el-icon> 开始统计
          </el-button>
        </el-form-item>
      </div>

      <div class="filter-row settings-row">
        <span class="settings-label">统计阈值设置 (%):</span>
        <el-form-item label="优秀 ≥">
          <el-input-number
            v-model="query.threshold_excellent"
            :min="1"
            :max="100"
            size="small"
            style="width: 100px"
          />
        </el-form-item>
        <el-form-item label="合格 ≥">
          <el-input-number
            v-model="query.threshold_pass"
            :min="1"
            :max="100"
            size="small"
            style="width: 100px"
          />
        </el-form-item>
        <el-form-item label="低分 ≤">
          <el-input-number
            v-model="query.threshold_low"
            :min="1"
            :max="100"
            size="small"
            style="width: 100px"
          />
        </el-form-item>
      </div>
    </el-form>

    <el-table
      :data="tableData"
      border
      stripe
      v-loading="loading"
      height="600"
      style="width: 100%; margin-top: 10px"
      show-summary
      :summary-method="getSummaries"
    >
      <el-table-column
        prop="class_name"
        label="班级"
        width="110"
        fixed
        sortable
      />
      <el-table-column
        prop="full_score"
        label="满分"
        width="70"
        align="center"
      />
      <el-table-column label="人数统计" align="center">
        <el-table-column prop="total_people" label="在读" width="70" />
        <el-table-column prop="exam_people" label="考试" width="70" />
      </el-table-column>

      <el-table-column label="分数指标 (基于选定科目总分)" align="center">
        <el-table-column
          prop="avg_score"
          label="平均分"
          width="90"
          sortable
          align="center"
        >
          <template #default="scope">
            <span style="font-weight: bold; color: #409eff">{{
              scope.row.avg_score
            }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="grade_ratio"
          label="级比率%"
          width="90"
          sortable
          align="center"
        >
          <template #default="scope">
            <el-tag
              :type="
                scope.row.grade_ratio >= 100
                  ? 'success'
                  : scope.row.grade_ratio < 90
                  ? 'danger'
                  : 'warning'
              "
            >
              {{ scope.row.grade_ratio }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="max_score" label="最高" width="80" />
        <el-table-column prop="min_score" label="最低" width="80" />
      </el-table-column>

      <el-table-column label="优秀情况" align="center">
        <el-table-column prop="excellent_count" label="人数" width="60" />
        <el-table-column prop="excellent_rate" label="率%" width="70" />
      </el-table-column>

      <el-table-column label="合格情况" align="center">
        <el-table-column prop="pass_count" label="人数" width="60" />
        <el-table-column prop="pass_rate" label="率%" width="70" />
      </el-table-column>

      <el-table-column label="不合格" align="center">
        <el-table-column prop="fail_count" label="人数" width="60" />
        <el-table-column prop="fail_rate" label="率%" width="70">
          <template #default="scope">
            <span
              :style="{
                color: scope.row.fail_rate > 10 ? '#F56C6C' : 'inherit',
              }"
            >
              {{ scope.row.fail_rate }}
            </span>
          </template>
        </el-table-column>
      </el-table-column>

      <el-table-column label="低分层" align="center">
        <el-table-column prop="low_count" label="人数" width="60" />
        <el-table-column prop="low_rate" label="率%" width="70">
          <template #default="scope">
            <span
              :style="{
                color: scope.row.low_rate > 5 ? '#F56C6C' : 'inherit',
              }"
            >
              {{ scope.row.low_rate }}
            </span>
          </template>
        </el-table-column>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import {
  getSubjects,
  getClasses,
  getExamNames,
  getClassScoreStats,
} from "../../api/admin";
import { ElMessage } from "element-plus";
import { Search, InfoFilled } from "@element-plus/icons-vue";

const loading = ref(false);
const subjectOptions = ref([]);
const allClassOptions = ref([]);
const examNameOptions = ref([]);
const tableData = ref([]);

const query = reactive({
  entry_year: null,
  exam_name: "",
  subject_ids: [],
  threshold_excellent: 85,
  threshold_pass: 60,
  threshold_low: 30,
});

const gradeOptions = computed(() => {
  if (!allClassOptions.value || allClassOptions.value.length === 0) return [];
  const years = [...new Set(allClassOptions.value.map((c) => c.entry_year))];
  return years.sort((a, b) => b - a).map((y) => ({ year: y, label: `${y}级` }));
});

const initData = async () => {
  try {
    const [sRes, cRes] = await Promise.all([getSubjects(), getClasses()]);
    subjectOptions.value = sRes.data;
    allClassOptions.value = cRes.data;
    query.subject_ids = sRes.data.map((s) => s.id);
  } catch (err) {
    ElMessage.error("初始化数据失败");
  }
};

const handleYearChange = async (val) => {
  query.exam_name = "";
  tableData.value = [];
  if (!val) return;
  try {
    const res = await getExamNames(val);
    examNameOptions.value = res.data;
  } catch (err) {
    ElMessage.error("获取考试列表失败");
  }
};

const handleSearch = async () => {
  if (!query.entry_year || !query.exam_name || query.subject_ids.length === 0) {
    return ElMessage.warning("请选择年级、考试名称及至少一门科目");
  }

  loading.value = true;
  try {
    const res = await getClassScoreStats(query);
    tableData.value = res.data;
    if (tableData.value.length === 0) {
      ElMessage.info("未查询到相关数据或该考试下无成绩");
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "统计失败");
  } finally {
    loading.value = false;
  }
};

// --- 核心新增：合计行计算逻辑 ---
const getSummaries = (param) => {
  const { columns, data } = param;
  const sums = [];

  if (data.length === 0) return sums;

  const totalExamPeople = data.reduce(
    (prev, curr) => prev + (curr.exam_people || 0),
    0
  );
  const totalSumScore = data.reduce(
    (prev, curr) => prev + (curr.sum_score || 0),
    0
  );

  columns.forEach((column, index) => {
    if (index === 0) {
      sums[index] = "全级合计";
      return;
    }

    const prop = column.property;

    if (prop === "full_score") {
      sums[index] = data[0]?.full_score;
      return;
    }

    const sumFields = [
      "total_people",
      "exam_people",
      "excellent_count",
      "pass_count",
      "fail_count",
      "low_count",
    ];
    if (sumFields.includes(prop)) {
      const values = data.map((item) => Number(item[prop]));
      sums[index] = values.reduce((prev, curr) => {
        const value = Number(curr);
        return !Number.isNaN(value) ? prev + value : prev;
      }, 0);
      return;
    }

    // --- 修改点：计算最高分时，过滤掉无人考试的班级 ---
    if (prop === "max_score") {
      const validData = data.filter((item) => item.exam_people > 0);
      if (validData.length > 0) {
        const values = validData.map((item) => Number(item[prop]));
        sums[index] = Math.max(...values);
      } else {
        sums[index] = 0;
      }
      return;
    }

    // --- 修改点：计算最低分时，过滤掉无人考试的班级，避免“缺考的0分”干扰 ---
    if (prop === "min_score") {
      const validData = data.filter((item) => item.exam_people > 0);
      if (validData.length > 0) {
        const values = validData.map((item) => Number(item[prop]));
        sums[index] = Math.min(...values);
      } else {
        sums[index] = 0;
      }
      return;
    }

    if (prop === "avg_score") {
      sums[index] =
        totalExamPeople > 0
          ? (totalSumScore / totalExamPeople).toFixed(1)
          : "0.0";
      return;
    }

    if (prop === "grade_ratio") {
      sums[index] = "100%";
      return;
    }

    // 各种率的重算逻辑保持不变
    if (prop === "excellent_rate") {
      const totalCount = data.reduce(
        (prev, curr) => prev + (curr.excellent_count || 0),
        0
      );
      sums[index] =
        totalExamPeople > 0
          ? ((totalCount / totalExamPeople) * 100).toFixed(1) + "%"
          : "0.0%";
      return;
    }
    if (prop === "pass_rate") {
      const totalCount = data.reduce(
        (prev, curr) => prev + (curr.pass_count || 0),
        0
      );
      sums[index] =
        totalExamPeople > 0
          ? ((totalCount / totalExamPeople) * 100).toFixed(1) + "%"
          : "0.0%";
      return;
    }
    if (prop === "fail_rate") {
      const totalCount = data.reduce(
        (prev, curr) => prev + (curr.fail_count || 0),
        0
      );
      sums[index] =
        totalExamPeople > 0
          ? ((totalCount / totalExamPeople) * 100).toFixed(1) + "%"
          : "0.0%";
      return;
    }
    if (prop === "low_rate") {
      const totalCount = data.reduce(
        (prev, curr) => prev + (curr.low_count || 0),
        0
      );
      sums[index] =
        totalExamPeople > 0
          ? ((totalCount / totalExamPeople) * 100).toFixed(1) + "%"
          : "0.0%";
      return;
    }
  });

  return sums;
};
onMounted(initData);
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}
.filter-form {
  background-color: #f8f9fa;
  padding: 15px 15px 0 15px;
  border-radius: 4px;
  margin-bottom: 10px;
}
.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.settings-row {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #dcdfe6;
}
.settings-label {
  font-size: 13px;
  color: #606266;
  margin-right: 15px;
  font-weight: bold;
}
</style>
