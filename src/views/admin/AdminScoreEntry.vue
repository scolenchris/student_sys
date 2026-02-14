<template>
  <el-card>
    <template #header>
      <div class="header-row">
        <span style="font-weight: bold">
          <el-icon><EditPen /></el-icon> 管理员成绩录入
        </span>
        <div class="controls">
          <el-select
            v-model="selectedClassId"
            placeholder="① 请选择班级"
            filterable
            @change="handleClassChange"
            style="width: 180px"
          >
            <el-option
              v-for="c in classList"
              :key="c.id"
              :label="`${c.grade_name}(${c.class_num})班`"
              :value="c.id"
            />
          </el-select>

          <el-select
            v-model="selectedExamId"
            placeholder="② 选择考试科目"
            :disabled="!selectedClassId"
            @change="handleExamChange"
            style="width: 240px"
          >
            <el-option
              v-for="ex in examList"
              :key="ex.id"
              :label="ex.display_name"
              :value="ex.id"
            />
          </el-select>
        </div>
      </div>
    </template>

    <div v-if="!selectedExamId" class="empty-tip">
      请先选择 <b>班级</b> 和 <b>考试任务</b> 以加载名单
    </div>

    <div v-else>
      <div class="toolbar">
        <div class="exam-info">
          当前录入：<el-tag effect="dark">{{
            currentExamInfo?.display_name
          }}</el-tag>
          满分标准：<el-tag type="warning"
            >{{ currentExamInfo?.full_score }}分</el-tag
          >
        </div>

        <div>
          <el-button
            type="primary"
            size="default"
            @click="saveAllScores"
            :loading="saving"
          >
            <el-icon><Select /></el-icon> 保存成绩
          </el-button>
        </div>
      </div>

      <div class="hint-text">
        <el-icon style="vertical-align: middle"><InfoFilled /></el-icon>
        提示：管理员可直接修改或补录成绩。输入后按 <b>Enter</b> 跳转下一行。
      </div>

      <el-table :data="students" border stripe v-loading="loading" height="550">
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="name" label="姓名" width="120" />

        <el-table-column :label="`成绩 (0-${currentExamInfo?.full_score})`">
          <template #default="scope">
            <el-input
              v-model="scope.row.score"
              placeholder="分数 或 缺考"
              style="width: 100%"
              :ref="(el) => setInputRef(el, scope.$index)"
              @blur="validateInput(scope.row, scope.$index)"
              @keydown.enter.prevent="handleEnter(scope.$index)"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { EditPen, Select, InfoFilled } from "@element-plus/icons-vue";
import {
  getClasses,
  getAdminClassExams,
  getAdminScoreList,
  saveAdminScores,
} from "../../api/admin";

const classList = ref([]);
const examList = ref([]);
const students = ref([]);

const selectedClassId = ref(null);
const selectedExamId = ref(null);

const loading = ref(false);
const saving = ref(false);
const scoreInputRefs = ref({}); // 用于回车跳转

const currentExamInfo = computed(() => {
  return examList.value.find((e) => e.id === selectedExamId.value);
});

// 初始化加载班级
onMounted(async () => {
  try {
    const res = await getClasses();
    classList.value = res.data;
  } catch (err) {
    ElMessage.error("班级列表加载失败");
  }
});

// 班级改变 -> 加载该班级能考的所有试
const handleClassChange = async (val) => {
  selectedExamId.value = null;
  students.value = [];
  examList.value = [];

  if (!val) return;

  try {
    const res = await getAdminClassExams({ class_id: val });
    examList.value = res.data;
    if (examList.value.length === 0) {
      ElMessage.info("该班级所在年级暂无开启的考试任务");
    }
  } catch (err) {
    ElMessage.error("获取考试列表失败");
  }
};

// 考试改变 -> 加载名单
const handleExamChange = async (val) => {
  if (!val) return;

  loading.value = true;
  scoreInputRefs.value = {}; // 重置输入框引用

  try {
    const res = await getAdminScoreList({
      class_id: selectedClassId.value,
      exam_task_id: val,
    });
    students.value = res.data;
  } catch (err) {
    ElMessage.error("加载名单失败");
  } finally {
    loading.value = false;
  }
};

// 保存逻辑
const saveAllScores = async () => {
  saving.value = true;
  try {
    const payload = {
      exam_task_id: selectedExamId.value,
      scores: students.value.map((s) => ({
        student_id: s.student_id,
        score: s.score,
      })),
    };
    await saveAdminScores(payload);
    ElMessage.success("保存成功");
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "保存失败");
  } finally {
    saving.value = false;
  }
};

// --- 以下是辅助逻辑 (回车跳转、验证) 与教师端一致 ---

const setInputRef = (el, index) => {
  if (el) scoreInputRefs.value[index] = el;
};

const handleEnter = (index) => {
  const nextIndex = index + 1;
  if (scoreInputRefs.value[nextIndex]) {
    scoreInputRefs.value[nextIndex].focus();
  } else {
    ElMessage.success("已经是最后一行了");
    // 可选：自动保存
    // saveAllScores();
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
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.controls {
  display: flex;
  gap: 15px;
}
.empty-tip {
  padding: 50px;
  text-align: center;
  color: #909399;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
}
.exam-info {
  font-size: 14px;
}
.hint-text {
  margin-bottom: 10px;
  color: #909399;
  font-size: 13px;
}
</style>
