<template>
  <el-card>
    <template #header>
      <div class="header-row">
        <span style="font-weight: bold">成绩录入工作台</span>
        <div class="controls">
          <el-select
            v-model="selectedKey"
            placeholder="① 选择任教班级与科目"
            @change="handleCourseChange"
            style="width: 240px"
          >
            <el-option
              v-for="item in myCourses"
              :key="item.assignment_id"
              :label="`${item.grade_class} - ${item.subject_name}`"
              :value="item.assignment_id"
            />
          </el-select>

          <el-select
            v-model="selectedExamId"
            placeholder="② 选择管理员发布的考试"
            :disabled="!selectedKey"
            @change="handleExamChange"
            style="width: 220px"
          >
            <el-option
              v-for="ex in examList"
              :key="ex.id"
              :label="`${ex.name} ${!ex.is_active ? '(已锁)' : ''}`"
              :value="ex.id"
              :disabled="!ex.is_active"
            />
          </el-select>
        </div>
      </div>
    </template>

    <div v-if="todoData.total_todos > 0" class="todo-panel">
      <el-alert
        title="⚠️ 待办提醒"
        type="warning"
        :closable="false"
        show-icon
      />
      <div class="todo-list">
        <p v-for="item in todoData.pending_items" :key="`pending-${item.task_id}-${item.class_id}`" class="todo-item">
          ⚠️ 待办：{{ item.msg }}
        </p>
        <p
          v-for="item in todoData.abnormal_items"
          :key="`abnormal-${item.task_id}-${item.class_id}`"
          class="todo-item"
        >
          ⚠️ 待办：{{ item.msg }}
        </p>
      </div>
    </div>

    <div v-if="!selectedExamId" class="empty-tip">
      请先按顺序选择 <b>班级科目</b> 和 <b>考试任务</b>
    </div>

    <div v-else>
      <div class="toolbar">
        <div class="exam-info">
          当前录入：<el-tag>{{ currentExamInfo?.name }}</el-tag>
          满分标准：<el-tag type="warning"
            >{{ currentExamInfo?.full_score }}分</el-tag
          >
        </div>

        <div class="action-buttons">
          <el-input
            v-model="keyword"
            placeholder="按姓名/学号搜索"
            clearable
            style="width: 220px"
            @input="handleKeywordInput"
            @clear="handleKeywordInput"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-button type="success" plain @click="handleExport">
            <el-icon><Download /></el-icon> 导出现有成绩/模板
          </el-button>

          <el-upload
            class="upload-btn"
            action=""
            :show-file-list="false"
            :http-request="handleImport"
            accept=".xlsx, .xls"
          >
            <el-button type="primary" plain>
              <el-icon><Upload /></el-icon> Excel 批量导入
            </el-button>
          </el-upload>
        </div>
      </div>

      <div class="hint-text">
        <el-icon style="vertical-align: middle"><check /></el-icon>
        小提示：输入分数后按 <b>Enter (回车)</b> 可自动跳转下一行
      </div>

      <el-table
        :data="students"
        border
        stripe
        v-loading="loading"
        :row-class-name="getRowClassName"
      >
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column :label="`成绩 (0-${currentExamInfo?.full_score})`">
          <template #default="scope">
            <el-input
              v-model="scope.row.score"
              placeholder="输入分数或'缺考'"
              style="width: 100%"
              :ref="(el) => setInputRef(el, scope.$index)"
              @blur="validateInput(scope.row, scope.$index)"
              @keydown.enter.prevent="handleEnter(scope.$index)"
            />
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 20px; text-align: right">
        <el-button
          type="primary"
          size="large"
          @click="saveAllScores"
          :loading="saving"
        >
          保存所有成绩
        </el-button>
      </div>
    </div>

    <el-dialog
      v-model="resultDialogVisible"
      title="Excel 导入结果反馈"
      width="600px"
    >
      <div style="margin-bottom: 15px">
        <el-alert
          v-if="importSummary.errors && importSummary.errors.length > 0"
          title="导入部分完成，但发现以下问题，请务必核对！"
          type="warning"
          show-icon
          :closable="false"
        />
        <el-alert
          v-else
          title="导入完全成功！"
          type="success"
          show-icon
          :closable="false"
        />
        <p style="margin-top: 10px">
          {{ importSummary.msg }}
        </p>
      </div>

      <el-table
        v-if="importSummary.errors && importSummary.errors.length > 0"
        :data="importSummary.errors"
        border
        height="300"
        style="width: 100%"
      >
        <el-table-column prop="row" label="Excel行号" width="100" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="msg" label="错误原因" show-overflow-tooltip>
          <template #default="scope">
            <span style="color: #f56c6c">{{ scope.row.msg }}</span>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button type="primary" @click="resultDialogVisible = false"
          >知道了</el-button
        >
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { ElMessage, ElNotification } from "element-plus";
import { Check, Download, Upload, Search } from "@element-plus/icons-vue";
import {
  getDashboardTodos,
  getMyCourses,
  getScoreList,
  saveScores,
  getAvailableExams,
  exportScores,
  importScores,
} from "../../api/teacher";

const myCourses = ref([]);
const selectedKey = ref(null);
const selectedCourseInfo = ref(null);
const examList = ref([]);
const selectedExamId = ref(null);
const studentsAll = ref([]);
const keyword = ref("");
const loading = ref(false);
const saving = ref(false);

const resultDialogVisible = ref(false);
const importSummary = ref({ msg: "", errors: [] });
const todoData = ref({
  pending_items: [],
  abnormal_items: [],
  total_todos: 0,
});
const hasTodoPopupShown = ref(false);

const scoreInputRefs = ref({});

const currentExamInfo = computed(() => {
  return examList.value.find((e) => e.id === selectedExamId.value);
});

const students = computed(() => {
  const kw = keyword.value.trim();
  if (!kw) return studentsAll.value;
  return studentsAll.value.filter(
    (item) =>
      String(item.name || "").includes(kw) ||
      String(item.student_no || "").includes(kw),
  );
});

const isAbnormalScore = (rawScore) => {
  if (rawScore === null || rawScore === undefined) return false;

  const text = String(rawScore).trim();
  if (!text) return false;
  if (text === "缺考") return true;

  const isStandardNumber = /^-?(\d+\.?\d*|\.\d+)$/.test(text);
  if (!isStandardNumber) return false;

  const numericScore = Number(text);
  if (Number.isNaN(numericScore)) return false;

  const maxScore = Number(currentExamInfo.value?.full_score || 100);
  if (numericScore < 0 || numericScore > maxScore) return false;

  return numericScore < maxScore * 0.6;
};

const getRowClassName = ({ row }) => {
  return isAbnormalScore(row.score) ? "abnormal-score-row" : "";
};

const setInputRef = (el, index) => {
  if (el) scoreInputRefs.value[index] = el;
};

const handleEnter = (index) => {
  const nextIndex = index + 1;
  if (scoreInputRefs.value[nextIndex]) {
    scoreInputRefs.value[nextIndex].focus();
  } else {
    ElMessage.success("已经是最后一位学生了");
  }
};

const fetchMyCourses = async () => {
  try {
    const res = await getMyCourses();
    myCourses.value = res.data;
  } catch (err) {
    console.error(err);
  }
};

const fetchDashboardTodos = async ({ notify = false } = {}) => {
  try {
    const res = await getDashboardTodos();
    const data = res.data || {};
    todoData.value = {
      pending_items: data.pending_items || [],
      abnormal_items: data.abnormal_items || [],
      total_todos: data.total_todos || 0,
    };

    if (
      notify &&
      !hasTodoPopupShown.value &&
      (todoData.value.total_todos || 0) > 0
    ) {
      ElNotification({
        title: "待办提醒",
        type: "warning",
        duration: 4000,
        message: `您当前有 ${todoData.value.total_todos} 条待办，请优先处理未录完成绩。`,
      });
      hasTodoPopupShown.value = true;
    }
  } catch (err) {
    console.error("获取待办提醒失败", err);
  }
};

const handleCourseChange = async (assignmentId) => {
  selectedExamId.value = null;
  studentsAll.value = [];
  keyword.value = "";
  const info = myCourses.value.find(
    (item) => item.assignment_id === assignmentId,
  );
  selectedCourseInfo.value = info;

  try {
    const res = await getAvailableExams({
      class_id: info.class_id,
      subject_id: info.subject_id,
    });
    examList.value = res.data;
    if (examList.value.length === 0) {
      ElMessage.info("暂无考试任务");
    }
  } catch (err) {
    ElMessage.error("获取考试列表失败");
  }
};

const handleExamChange = async (examId) => {
  if (!selectedCourseInfo.value) return;
  loading.value = true;
  scoreInputRefs.value = {};
  try {
    const res = await getScoreList({
      class_id: selectedCourseInfo.value.class_id,
      exam_task_id: examId,
    });
    studentsAll.value = res.data || [];
  } catch (err) {
    ElMessage.error("获取名单失败");
  } finally {
    loading.value = false;
  }
};

const saveAllScores = async () => {
  saving.value = true;
  try {
    const res = await saveScores({
      exam_task_id: selectedExamId.value,
      scores: studentsAll.value.map((s) => ({
        student_id: s.student_id,
        score: s.score,
      })),
    });
    const data = res?.data || {};
    if ((data.missing_count || 0) > 0 || (data.invalid_count || 0) > 0) {
      ElMessage.warning(data.msg || "部分成绩未填写，已保存已填写项");
    } else {
      ElMessage.success(data.msg || "保存成功");
    }
    await fetchDashboardTodos();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "保存失败");
  } finally {
    saving.value = false;
  }
};

const handleExport = async () => {
  if (!selectedCourseInfo.value || !selectedExamId.value) return;
  try {
    const res = await exportScores({
      class_id: selectedCourseInfo.value.class_id,
      exam_task_id: selectedExamId.value,
    });

    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;

    const clsName = selectedCourseInfo.value.grade_class;
    const subName = selectedCourseInfo.value.subject_name;
    const examName = currentExamInfo.value?.name || "考试";
    link.setAttribute("download", `${clsName}-${subName}-${examName}.xlsx`);

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (err) {
    ElMessage.error("导出失败");
  }
};

const handleImport = async (param) => {
  const formData = new FormData();
  formData.append("file", param.file);
  formData.append("class_id", selectedCourseInfo.value.class_id);
  formData.append("exam_task_id", selectedExamId.value);

  const loadingInstance = ElMessage.success({
    message: "正在导入并校验数据，请稍候...",
    duration: 0,
  });

  try {
    const res = await importScores(formData);
    loadingInstance.close();

    importSummary.value = res.data.logs;
    importSummary.value.msg = res.data.msg;

    resultDialogVisible.value = true;

    // 导入后刷新名单，展示最新结果。
    handleExamChange(selectedExamId.value);
    await fetchDashboardTodos();
  } catch (err) {
    loadingInstance.close();
    ElMessage.error(err.response?.data?.msg || "导入失败");
  }
};

const validateInput = (row, index) => {
  if (row.score === null || row.score === undefined) return;

  const strVal = String(row.score).trim();

  if (strVal === "") {
    row.score = null;
    return;
  }

  if (strVal === "缺考") {
    return;
  }

  // 严格数字校验：禁止 "40a12"、"1e5" 等非标准输入。
  const numVal = Number(strVal);
  const isStandardNumber = /^-?(\d+\.?\d*|\.\d+)$/.test(strVal);

  const maxScore = currentExamInfo.value?.full_score || 100;

  if (isNaN(numVal) || !isStandardNumber) {
    ElMessage.warning(
      `第 ${index + 1} 行：输入内容 "${strVal}" 不合法，请输入纯数字或"缺考"`,
    );
    row.score = null;
    return;
  }

  if (numVal < 0 || numVal > maxScore) {
    ElMessage.warning(
      `第 ${index + 1} 行：分数 ${numVal} 超出范围 (0-${maxScore})`,
    );
    row.score = null;
    return;
  }

  // 归一化数值格式，例如 "090" -> 90。
  row.score = numVal;
};

const handleKeywordInput = () => {
  scoreInputRefs.value = {};
};

onMounted(async () => {
  await fetchMyCourses();
  await fetchDashboardTodos({ notify: true });
});
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.controls {
  display: flex;
  gap: 10px;
}
.empty-tip {
  padding: 40px;
  text-align: center;
  color: #909399;
}
.todo-panel {
  margin-bottom: 14px;
  border: 1px solid #f7d8b2;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff8ef;
}
.todo-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.todo-item {
  margin: 0;
  color: #8c5a1d;
  font-size: 13px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
}
.exam-info {
  display: flex;
  gap: 15px;
  align-items: center;
}
.action-buttons {
  display: flex;
  gap: 10px;
}
.upload-btn {
  display: inline-block;
}
.hint-text {
  margin-bottom: 10px;
  color: #909399;
  font-size: 13px;
}

:deep(.el-table__body tr.abnormal-score-row > td.el-table__cell) {
  background-color: #fff6cc !important;
}

:deep(.el-table__body tr.abnormal-score-row:hover > td.el-table__cell) {
  background-color: #ffefad !important;
}
</style>
