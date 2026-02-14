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

      <el-table :data="students" border stripe v-loading="loading">
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
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Check, Download, Upload } from "@element-plus/icons-vue";
import {
  getMyCourses,
  getScoreList,
  saveScores,
  getAvailableExams,
  exportScores,
  importScores,
} from "../../api/teacher";

const router = useRouter();
const myCourses = ref([]);
const selectedKey = ref(null);
const selectedCourseInfo = ref(null);
const examList = ref([]);
const selectedExamId = ref(null);
const students = ref([]);
const loading = ref(false);
const saving = ref(false);

// --- 导入导出相关状态 ---
const resultDialogVisible = ref(false);
const importSummary = ref({ msg: "", errors: [] });

// 快捷键引用
const scoreInputRefs = ref({});

const currentExamInfo = computed(() => {
  return examList.value.find((e) => e.id === selectedExamId.value);
});

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
  const userId = localStorage.getItem("user_id");
  if (!userId) return router.push("/");
  try {
    const res = await getMyCourses(userId);
    myCourses.value = res.data;
  } catch (err) {
    console.error(err);
  }
};

const handleCourseChange = async (assignmentId) => {
  selectedExamId.value = null;
  students.value = [];
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
  scoreInputRefs.value = {}; // 重置引用
  try {
    const res = await getScoreList({
      class_id: selectedCourseInfo.value.class_id,
      exam_task_id: examId,
    });
    students.value = res.data;
  } catch (err) {
    ElMessage.error("获取名单失败");
  } finally {
    loading.value = false;
  }
};

const saveAllScores = async () => {
  saving.value = true;
  try {
    await saveScores({
      exam_task_id: selectedExamId.value,
      scores: students.value.map((s) => ({
        student_id: s.student_id,
        score: s.score,
      })),
    });
    ElMessage.success("保存成功");
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "保存失败");
  } finally {
    saving.value = false;
  }
};

// --- 导出逻辑 ---
const handleExport = async () => {
  if (!selectedCourseInfo.value || !selectedExamId.value) return;
  try {
    const res = await exportScores({
      class_id: selectedCourseInfo.value.class_id,
      exam_task_id: selectedExamId.value,
    });

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;

    // 生成友好的文件名
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

// --- 导入逻辑 ---
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

    // 赋值给弹窗数据
    importSummary.value = res.data.logs; // logs 包含 success, updated, errors[]
    importSummary.value.msg = res.data.msg;

    // 显示结果弹窗
    resultDialogVisible.value = true;

    // 导入后自动刷新表格，看到最新成绩
    handleExamChange(selectedExamId.value);
  } catch (err) {
    loadingInstance.close();
    ElMessage.error(err.response?.data?.msg || "导入失败");
  }
};

const validateInput = (row, index) => {
  // 1. 空值预处理
  if (row.score === null || row.score === undefined) return;

  // 转为字符串并去除首尾空格
  const strVal = String(row.score).trim();

  // 如果是空字符串，重置为 null（视为未录入）并不报错
  if (strVal === "") {
    row.score = null;
    return;
  }

  // 2. 检查特殊标识 "缺考"
  if (strVal === "缺考") {
    return;
  }

  // 3. 严格数字校验
  // 【关键修改】：使用 Number() 替代 parseFloat()
  // parseFloat("40a12") -> 40 (宽松，不符合要求)
  // Number("40a12") -> NaN (严格，符合要求)
  const numVal = Number(strVal);

  // 额外正则校验：防止科学计数法 (如 1e2) 或其他边缘情况，只允许标准数字格式
  // 允许：40, 40.5, .5, 40.
  // 不允许：40a12, 12-3, 1e5
  const isStandardNumber = /^-?(\d+\.?\d*|\.\d+)$/.test(strVal);

  const maxScore = currentExamInfo.value?.full_score || 100;

  // 综合校验：必须是有效数字 且 符合正则格式
  if (isNaN(numVal) || !isStandardNumber) {
    ElMessage.warning(
      `第 ${index + 1} 行：输入内容 "${strVal}" 不合法，请输入纯数字或"缺考"`,
    );
    row.score = null; // 清空非法输入
    return;
  }

  // 4. 数值范围校验
  if (numVal < 0 || numVal > maxScore) {
    ElMessage.warning(
      `第 ${index + 1} 行：分数 ${numVal} 超出范围 (0-${maxScore})`,
    );
    row.score = null;
    return;
  }

  // 5. (可选) 自动格式化
  // 将 "090" 修正为 90，将 "40." 修正为 40
  row.score = numVal;
};

onMounted(fetchMyCourses);
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
</style>
