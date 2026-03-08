<template>
  <el-card class="history-card">
    <template #header>
      <div class="header-row">
        <span>历史成绩查询（只读）</span>
      </div>
    </template>

    <el-form :inline="true" class="filter-bar">
      <el-form-item label="班级科目">
        <el-select
          v-model="query.course_key"
          placeholder="请选择班级与科目"
          style="width: 280px"
          @change="handleCourseChange"
        >
          <el-option
            v-for="course in courseOptions"
            :key="course.key"
            :label="course.label"
            :value="course.key"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="历史考试">
        <el-select
          v-model="query.exam_task_id"
          placeholder="请选择考试"
          style="width: 260px"
          :disabled="!query.course_key"
        >
          <el-option
            v-for="exam in examList"
            :key="exam.id"
            :label="formatExamLabel(exam)"
            :value="exam.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="姓名/学号"
          style="width: 180px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="loading" @click="handleSearch">
          查询成绩
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="说明"
      description="本页仅提供历史成绩查询，不提供任何写入能力。"
      style="margin-bottom: 10px"
    />

    <el-table
      :data="tableData"
      border
      stripe
      v-loading="loading"
      height="620"
      style="width: 100%"
    >
      <el-table-column prop="student_no" label="学号" width="150" />
      <el-table-column prop="name" label="姓名" width="130" />
      <el-table-column prop="score" label="成绩" width="120" align="center" />
      <el-table-column prop="remark" label="备注" width="120" align="center" />
    </el-table>

    <div class="foot-tip">共 {{ total }} 条历史成绩记录</div>
  </el-card>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getHistoryExams,
  getHistoryScores,
  getRankTrendContexts,
} from "../../api/teacher";

const loading = ref(false);
const contexts = ref([]);
const examList = ref([]);
const tableData = ref([]);
const total = ref(0);

const query = reactive({
  course_key: "",
  exam_task_id: null,
  keyword: "",
});

const courseOptions = computed(() => {
  const dedup = new Map();

  contexts.value.forEach((ctx) => {
    const subjectId = ctx.subject_id;
    const subjectName = ctx.subject_name;
    const entryYear = ctx.entry_year;

    (ctx.classes || []).forEach((cls) => {
      const key = `${cls.class_id}-${subjectId}`;
      if (!dedup.has(key)) {
        dedup.set(key, {
          key,
          class_id: cls.class_id,
          class_num: cls.class_num,
          entry_year: entryYear,
          subject_id: subjectId,
          subject_name: subjectName,
          label: `${entryYear}级(${cls.class_num})班 - ${subjectName}`,
        });
      }
    });
  });

  return Array.from(dedup.values()).sort((a, b) => {
    if (a.entry_year !== b.entry_year) return b.entry_year - a.entry_year;
    if (a.class_num !== b.class_num) return a.class_num - b.class_num;
    return a.subject_id - b.subject_id;
  });
});

const selectedCourse = computed(() =>
  courseOptions.value.find((item) => item.key === query.course_key),
);

const formatExamLabel = (exam) => {
  const statusText = exam.is_active ? "进行中" : "已关闭";
  return `${exam.name}（${exam.academic_year}学年，${statusText}）`;
};

const fetchContexts = async () => {
  try {
    const res = await getRankTrendContexts();
    contexts.value = Array.isArray(res.data) ? res.data : [];

    if (courseOptions.value.length > 0) {
      query.course_key = courseOptions.value[0].key;
      await handleCourseChange();
    } else {
      tableData.value = [];
      examList.value = [];
      total.value = 0;
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "获取班级科目失败");
  }
};

const handleCourseChange = async () => {
  if (!selectedCourse.value) return;
  query.exam_task_id = null;
  tableData.value = [];
  total.value = 0;

  try {
    const res = await getHistoryExams({
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.subject_id,
    });
    examList.value = Array.isArray(res.data) ? res.data : [];
    if (examList.value.length === 0) {
      ElMessage.info("该班级科目暂无可查询的历史考试");
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "获取历史考试失败");
  }
};

const handleSearch = async () => {
  if (!selectedCourse.value) {
    return ElMessage.warning("请先选择班级科目");
  }
  if (!query.exam_task_id) {
    return ElMessage.warning("请选择历史考试");
  }

  loading.value = true;
  try {
    const res = await getHistoryScores({
      class_id: selectedCourse.value.class_id,
      exam_task_id: query.exam_task_id,
      keyword: query.keyword,
    });
    const data = res.data || {};
    tableData.value = Array.isArray(data.items) ? data.items : [];
    total.value = Number(data.total || 0);

    if (total.value === 0) {
      ElMessage.info("未查询到历史成绩");
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "查询历史成绩失败");
  } finally {
    loading.value = false;
  }
};

onMounted(fetchContexts);
</script>

<style scoped>
.history-card {
  min-height: 82vh;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.filter-bar {
  margin-bottom: 10px;
  padding: 14px 14px 0 14px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.foot-tip {
  margin-top: 10px;
  text-align: right;
  color: #909399;
  font-size: 13px;
}
</style>
