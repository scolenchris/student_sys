<template>
  <div class="overview-screen" v-loading="loading">
    <section class="screen-head">
      <div class="head-left">
        <p class="head-caption">校园运营驾驶舱</p>
        <h2>学生成绩管理数据可视化大屏</h2>
      </div>
      <div class="head-right">
        <el-select
          v-model="selectedAcademicYear"
          style="width: 140px"
          @change="loadOverview"
        >
          <el-option
            v-for="year in academicYearOptions"
            :key="year"
            :label="`${year}-${year + 1} 学年`"
            :value="year"
          />
        </el-select>
        <el-button type="primary" @click="loadOverview">
          <el-icon><Refresh /></el-icon>
          刷新总览数据
        </el-button>
      </div>
    </section>

    <section class="kpi-grid">
      <article
        v-for="card in kpiCards"
        :key="card.key"
        class="kpi-card"
        :class="`tone-${card.tone}`"
      >
        <div class="kpi-icon">
          <el-icon>
            <component :is="card.icon" />
          </el-icon>
        </div>
        <div class="kpi-main">
          <p class="kpi-label">{{ card.label }}</p>
          <h3>{{ formatNumber(card.value) }}</h3>
          <p class="kpi-sub">{{ card.sub }}</p>
        </div>
      </article>
    </section>

    <section class="panel-grid">
      <el-card class="panel-card">
        <template #header>
          <div class="panel-title">人员状态占比</div>
        </template>
        <div class="double-donut">
          <div class="donut-block">
            <p class="donut-title">教师状态</p>
            <div class="donut" :style="teacherDonutStyle">
              <div class="donut-core">{{ summary.teacherTotal }}</div>
            </div>
            <div class="legend-list">
              <div
                v-for="item in teacherStatusData"
                :key="`teacher-${item.label}`"
                class="legend-item"
              >
                <span class="dot" :style="{ backgroundColor: item.color }"></span>
                <span>{{ item.label }} {{ item.value }}（{{ item.percent }}%）</span>
              </div>
            </div>
          </div>
          <div class="donut-block">
            <p class="donut-title">学生状态</p>
            <div class="donut" :style="studentDonutStyle">
              <div class="donut-core">{{ summary.studentTotal }}</div>
            </div>
            <div class="legend-list">
              <div
                v-for="item in studentStatusData"
                :key="`student-${item.label}`"
                class="legend-item"
              >
                <span class="dot" :style="{ backgroundColor: item.color }"></span>
                <span>{{ item.label }} {{ item.value }}（{{ item.percent }}%）</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="panel-card">
        <template #header>
          <div class="panel-title">年级学生规模分布</div>
        </template>
        <div v-if="gradeDistribution.length > 0" class="bar-list">
          <div v-for="item in gradeDistribution" :key="item.label" class="bar-item">
            <span class="bar-label">{{ item.label }}</span>
            <div class="bar-track">
              <div
                class="bar-fill grade"
                :style="{ width: getBarWidth(item.value, maxGradeValue) }"
              ></div>
            </div>
            <span class="bar-value">{{ item.value }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无年级数据" :image-size="80" />
      </el-card>

      <el-card class="panel-card">
        <template #header>
          <div class="panel-head">
            <span class="panel-title">成绩分析视图</span>
            <el-radio-group v-model="scoreViewMode" size="small">
              <el-radio-button label="histogram">成绩分布直方图</el-radio-button>
              <el-radio-button label="class_compare">班级均分对比</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <div class="score-controls">
          <el-select
            v-model="scoreEntryYear"
            style="width: 120px"
            @change="handleScoreYearChange"
          >
            <el-option
              v-for="year in scoreYearOptions"
              :key="year"
              :label="`${year}级`"
              :value="year"
            />
          </el-select>
          <el-select
            v-model="scoreExamName"
            style="width: 180px"
            :disabled="!scoreEntryYear || scoreExamOptions.length === 0"
            @change="loadScoreInsight"
          >
            <el-option
              v-for="exam in scoreExamOptions"
              :key="exam"
              :label="exam"
              :value="exam"
            />
          </el-select>
          <el-button type="primary" plain @click="loadScoreInsight">
            刷新成绩图表
          </el-button>
        </div>

        <div class="chart-block" v-loading="scoreLoading">
          <div v-if="scoreViewMode === 'histogram'">
            <div v-if="scoreHistogram.length > 0" class="bar-list">
              <div
                v-for="item in scoreHistogram"
                :key="item.label"
                class="bar-item histogram-row"
              >
                <span class="bar-label">{{ item.label }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill score-hist"
                    :style="{ width: getBarWidth(item.count, maxHistogramCount) }"
                  ></div>
                </div>
                <span class="bar-value">{{ item.count }}</span>
              </div>
            </div>
            <el-empty
              v-else
              description="暂无成绩分布数据，请调整年级/考试"
              :image-size="80"
            />
          </div>

          <div v-else>
            <div v-if="classScoreCompare.length > 0" class="bar-list">
              <div
                v-for="item in classScoreCompare"
                :key="item.label"
                class="bar-item"
              >
                <span class="bar-label">{{ item.label }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill class-score"
                    :style="{ width: getBarWidth(item.value, maxClassScoreValue) }"
                  ></div>
                </div>
                <span class="bar-value">{{ item.value }}</span>
              </div>
            </div>
            <el-empty
              v-else
              description="暂无班级均分数据，请调整年级/考试"
              :image-size="80"
            />
          </div>
        </div>
      </el-card>

      <el-card class="panel-card panel-full">
        <template #header>
          <div class="panel-title">
            近期考试任务（{{ selectedAcademicYear }}-{{ selectedAcademicYear + 1
            }}学年）
          </div>
        </template>
        <el-table :data="recentExamTasks" border stripe max-height="300">
          <el-table-column prop="name" label="考试名称" min-width="220" />
          <el-table-column prop="grade_name" label="年级" width="120" />
          <el-table-column prop="subject_name" label="科目" width="120" />
          <el-table-column prop="full_score" label="满分" width="90" />
          <el-table-column label="状态" width="100" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'info'">
                {{ scope.row.is_active ? "进行中" : "已锁定" }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  CollectionTag,
  Document,
  Histogram,
  Refresh,
  School,
  UserFilled,
} from "@element-plus/icons-vue";
import {
  getClasses,
  getClassScoreStats,
  getComprehensiveReport,
  getExamNames,
  getExamTasks,
  getPendingUsers,
  getStudents,
  getSubjects,
  getTeachers,
} from "../../api/admin";

const now = new Date();
const currentYear = now.getFullYear();
const defaultAcademicYear = now.getMonth() >= 8 ? currentYear : currentYear - 1;

const loading = ref(false);
const selectedAcademicYear = ref(defaultAcademicYear);
const teacherStatusData = ref([]);
const studentStatusData = ref([]);
const gradeDistribution = ref([]);
const recentExamTasks = ref([]);
const allSubjects = ref([]);

const scoreLoading = ref(false);
const scoreViewMode = ref("histogram");
const scoreYearOptions = ref([]);
const scoreExamOptions = ref([]);
const scoreEntryYear = ref(null);
const scoreExamName = ref("");
const scoreHistogram = ref([]);
const classScoreCompare = ref([]);

const summary = reactive({
  studentTotal: 0,
  readingStudentTotal: 0,
  teacherTotal: 0,
  activeTeacherTotal: 0,
  classTotal: 0,
  subjectTotal: 0,
  examTotal: 0,
  activeExamTotal: 0,
  pendingUserTotal: 0,
});

const palette = ["#2f89ff", "#33c08a", "#f8b653", "#fa7b61", "#5d7fdb", "#8c65d3"];

const academicYearOptions = computed(() => {
  const years = [];
  for (let i = -2; i <= 2; i += 1) {
    years.push(defaultAcademicYear + i);
  }
  return years.sort((a, b) => b - a);
});

const maxGradeValue = computed(() => {
  if (gradeDistribution.value.length === 0) return 1;
  return Math.max(...gradeDistribution.value.map((item) => item.value), 1);
});

const maxHistogramCount = computed(() => {
  if (scoreHistogram.value.length === 0) return 1;
  return Math.max(...scoreHistogram.value.map((item) => item.count), 1);
});

const maxClassScoreValue = computed(() => {
  if (classScoreCompare.value.length === 0) return 1;
  return Math.max(...classScoreCompare.value.map((item) => item.value), 1);
});

const kpiCards = computed(() => [
  {
    key: "student",
    label: "学生总数",
    value: summary.studentTotal,
    sub: `在读 ${summary.readingStudentTotal} 人`,
    icon: UserFilled,
    tone: "sky",
  },
  {
    key: "teacher",
    label: "教师总数",
    value: summary.teacherTotal,
    sub: `在职 ${summary.activeTeacherTotal} 人`,
    icon: School,
    tone: "mint",
  },
  {
    key: "class",
    label: "班级总数",
    value: summary.classTotal,
    sub: "按当前系统班级档案统计",
    icon: Histogram,
    tone: "gold",
  },
  {
    key: "exam",
    label: "考试任务",
    value: summary.examTotal,
    sub: `进行中 ${summary.activeExamTotal} 项`,
    icon: Document,
    tone: "orange",
  },
  {
    key: "subject",
    label: "学科数量",
    value: summary.subjectTotal,
    sub: "系统可用科目总数",
    icon: CollectionTag,
    tone: "blue",
  },
  {
    key: "pending",
    label: "待审核账号",
    value: summary.pendingUserTotal,
    sub: "新用户申请待处理",
    icon: UserFilled,
    tone: "rose",
  },
]);

const teacherDonutStyle = computed(() => ({
  background: buildDonutGradient(teacherStatusData.value),
}));

const studentDonutStyle = computed(() => ({
  background: buildDonutGradient(studentStatusData.value),
}));

const formatNumber = (value) => Number(value || 0).toLocaleString("zh-CN");

const getBarWidth = (value, maxValue) => {
  const safeMax = maxValue > 0 ? maxValue : 1;
  return `${((value / safeMax) * 100).toFixed(1)}%`;
};

const buildDonutGradient = (items) => {
  if (!items || items.length === 0) {
    return "conic-gradient(#d7e4f7 0% 100%)";
  }

  let cursor = 0;
  const chunks = items.map((item) => {
    const start = cursor;
    const end = cursor + item.percent;
    cursor = end;
    return `${item.color} ${start}% ${end}%`;
  });

  if (cursor < 100) {
    chunks.push(`#d7e4f7 ${cursor}% 100%`);
  }
  return `conic-gradient(${chunks.join(",")})`;
};

const toDistribution = (counter) => {
  const entries = Object.entries(counter);
  const total = entries.reduce((acc, [, value]) => acc + value, 0);
  if (total === 0) return [];

  return entries
    .sort((a, b) => b[1] - a[1])
    .map(([label, value], idx) => ({
      label,
      value,
      percent: Number(((value / total) * 100).toFixed(1)),
      color: palette[idx % palette.length],
    }));
};

const fetchAllStudents = async () => {
  const limit = 500;
  let page = 1;
  let total = 0;
  const rows = [];

  while (true) {
    const res = await getStudents({ page, limit });
    const payload = res.data || {};
    const batch = payload.data || [];
    total = payload.total || 0;
    rows.push(...batch);

    if (rows.length >= total || batch.length === 0) break;
    page += 1;

    if (page > 50) break;
  }

  return rows;
};

const buildHistogram = (totals, fullScore) => {
  if (!totals || totals.length === 0 || !fullScore) {
    return [];
  }

  const bucketSize = 10;
  const buckets = Array.from({ length: 10 }, (_, idx) => ({
    label: `${idx * bucketSize}-${(idx + 1) * bucketSize}%`,
    count: 0,
  }));

  totals.forEach((score) => {
    const rawPercent = Number((score / fullScore) * 100);
    const percent = Number.isFinite(rawPercent) ? rawPercent : 0;
    const safePercent = Math.max(0, Math.min(100, percent));
    const bucketIndex =
      safePercent === 100 ? 9 : Math.floor(safePercent / bucketSize);
    buckets[bucketIndex].count += 1;
  });

  return buckets;
};

const loadScoreExamOptions = async () => {
  if (!scoreEntryYear.value) {
    scoreExamOptions.value = [];
    scoreExamName.value = "";
    return;
  }

  try {
    const res = await getExamNames(scoreEntryYear.value);
    const names = res.data || [];
    scoreExamOptions.value = names;
    scoreExamName.value = names.length > 0 ? names[names.length - 1] : "";
  } catch (error) {
    scoreExamOptions.value = [];
    scoreExamName.value = "";
    ElMessage.error(error.response?.data?.msg || "获取考试名称失败");
  }
};

const handleScoreYearChange = async () => {
  await loadScoreExamOptions();
  await loadScoreInsight();
};

const loadScoreInsight = async () => {
  if (!scoreEntryYear.value || !scoreExamName.value || allSubjects.value.length === 0) {
    scoreHistogram.value = [];
    classScoreCompare.value = [];
    return;
  }

  scoreLoading.value = true;
  try {
    const subjectIds = allSubjects.value.map((item) => item.id);

    const [reportRes, classStatsRes] = await Promise.all([
      getComprehensiveReport({
        entry_year: scoreEntryYear.value,
        exam_name: scoreExamName.value,
        subject_ids: subjectIds,
        class_ids: [],
      }),
      getClassScoreStats({
        entry_year: scoreEntryYear.value,
        exam_name: scoreExamName.value,
        subject_ids: subjectIds,
        threshold_excellent: 85,
        threshold_pass: 60,
        threshold_low: 30,
      }),
    ]);

    const reportRows = reportRes.data?.data || [];
    const fullScore = reportRows.length > 0 ? Number(reportRows[0].full_score || 0) : 0;
    const totals = reportRows.map((item) => Number(item.total || 0));
    scoreHistogram.value = buildHistogram(totals, fullScore);

    const classRows = classStatsRes.data || [];
    classScoreCompare.value = classRows
      .map((item) => ({
        label: item.class_name,
        value: Number(item.avg_score || 0),
      }))
      .sort((a, b) => b.value - a.value);
  } catch (error) {
    scoreHistogram.value = [];
    classScoreCompare.value = [];
    ElMessage.error(error.response?.data?.msg || "加载成绩分析失败");
  } finally {
    scoreLoading.value = false;
  }
};

const loadOverview = async () => {
  loading.value = true;
  try {
    const [
      pendingRes,
      classesRes,
      subjectsRes,
      teachersRes,
      examsRes,
      allStudents,
    ] = await Promise.all([
      getPendingUsers(),
      getClasses(),
      getSubjects(),
      getTeachers({
        academic_year: selectedAcademicYear.value,
        status: "全部",
      }),
      getExamTasks({ academic_year: selectedAcademicYear.value }),
      fetchAllStudents(),
    ]);

    const pendingUsers = pendingRes.data || [];
    const classes = classesRes.data || [];
    const subjects = subjectsRes.data || [];
    const teachers = teachersRes.data || [];
    const exams = examsRes.data || [];
    const students = allStudents || [];
    allSubjects.value = subjects;

    summary.pendingUserTotal = pendingUsers.length;
    summary.classTotal = classes.length;
    summary.subjectTotal = subjects.length;
    summary.teacherTotal = teachers.length;
    summary.activeTeacherTotal = teachers.filter((t) => t.status === "在职").length;
    summary.studentTotal = students.length;
    summary.readingStudentTotal = students.filter((s) => s.status === "在读").length;
    summary.examTotal = exams.length;
    summary.activeExamTotal = exams.filter((e) => e.is_active).length;

    const teacherCounter = {};
    teachers.forEach((item) => {
      const key = item.status || "未知";
      teacherCounter[key] = (teacherCounter[key] || 0) + 1;
    });
    teacherStatusData.value = toDistribution(teacherCounter);

    const studentCounter = {};
    students.forEach((item) => {
      const key = item.status || "未知";
      studentCounter[key] = (studentCounter[key] || 0) + 1;
    });
    studentStatusData.value = toDistribution(studentCounter);

    const gradeCounter = {};
    classes.forEach((item) => {
      const grade = item.grade_name || `${item.entry_year}级`;
      const count = Number(item.student_count || 0);
      gradeCounter[grade] = (gradeCounter[grade] || 0) + count;
    });
    gradeDistribution.value = Object.entries(gradeCounter)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);

    recentExamTasks.value = exams.slice(0, 8);

    const years = [...new Set(classes.map((item) => item.entry_year))].sort(
      (a, b) => b - a,
    );
    scoreYearOptions.value = years;
    if (!scoreEntryYear.value || !years.includes(scoreEntryYear.value)) {
      scoreEntryYear.value = years[0] || null;
    }
    await loadScoreExamOptions();
    await loadScoreInsight();
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || "加载可视化数据失败");
  } finally {
    loading.value = false;
  }
};

onMounted(loadOverview);
</script>

<style scoped>
.overview-screen {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.screen-head {
  border-radius: 18px;
  padding: 24px;
  color: #f8fbff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(125deg, #115189 0%, #167eb7 45%, #1aa3bb 100%);
  position: relative;
  overflow: hidden;
}

.screen-head::before {
  content: "";
  position: absolute;
  right: -40px;
  top: -40px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
}

.screen-head::after {
  content: "";
  position: absolute;
  left: 42%;
  bottom: -120px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}

.head-left,
.head-right {
  position: relative;
  z-index: 1;
}

.head-caption {
  margin: 0;
  font-size: 14px;
  opacity: 0.85;
}

.screen-head h2 {
  margin: 8px 0 0;
  font-size: 30px;
  letter-spacing: 1px;
}

.head-right {
  display: flex;
  gap: 10px;
  align-items: center;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.kpi-card {
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
  box-shadow: 0 8px 20px rgba(18, 67, 104, 0.08);
  display: flex;
  gap: 12px;
  align-items: center;
}

.kpi-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.kpi-main {
  min-width: 0;
}

.kpi-label {
  margin: 0;
  font-size: 13px;
  color: #607896;
}

.kpi-main h3 {
  margin: 4px 0;
  font-size: 30px;
  line-height: 1;
  color: #103a60;
}

.kpi-sub {
  margin: 0;
  font-size: 12px;
  color: #7b93af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tone-sky .kpi-icon {
  background: #d5e9ff;
  color: #1d78cf;
}

.tone-mint .kpi-icon {
  background: #d5f5e8;
  color: #2c9e75;
}

.tone-gold .kpi-icon {
  background: #fff1d2;
  color: #e39c25;
}

.tone-orange .kpi-icon {
  background: #fee3d9;
  color: #d96d45;
}

.tone-blue .kpi-icon {
  background: #e2e8ff;
  color: #4a5fcf;
}

.tone-rose .kpi-icon {
  background: #ffe4e9;
  color: #d65a78;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.panel-card {
  border-radius: 16px;
  min-height: 320px;
}

.panel-card :deep(.el-card__header) {
  border-bottom: 1px solid #e6edf8;
  padding: 14px 18px;
}

.panel-card :deep(.el-card__body) {
  padding: 16px 18px 18px;
}

.panel-title {
  font-weight: 700;
  color: #16466f;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.double-donut {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.donut-block {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.donut-title {
  margin: 0 0 12px;
  color: #4a6482;
  font-weight: 600;
}

.donut {
  width: 156px;
  height: 156px;
  border-radius: 50%;
  position: relative;
}

.donut::after {
  content: "";
  position: absolute;
  inset: 24px;
  border-radius: 50%;
  background: #ffffff;
}

.donut-core {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: 700;
  color: #17486f;
  z-index: 1;
}

.legend-list {
  margin-top: 12px;
  width: 100%;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4f6682;
  font-size: 12px;
  margin-bottom: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bar-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.score-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.chart-block {
  min-height: 220px;
}

.bar-item {
  display: grid;
  grid-template-columns: 110px 1fr 48px;
  gap: 10px;
  align-items: center;
}

.bar-label,
.bar-value {
  font-size: 13px;
  color: #4c6684;
}

.bar-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 10px;
  border-radius: 10px;
  overflow: hidden;
  background: #eaf0f8;
}

.bar-fill {
  height: 100%;
  border-radius: 10px;
  animation: grow 0.5s ease;
}

.bar-fill.grade {
  background: linear-gradient(90deg, #2d8dff, #59b6ff);
}

.bar-fill.score-hist {
  background: linear-gradient(90deg, #59a6ff, #8bc8ff);
}

.bar-fill.class-score {
  background: linear-gradient(90deg, #21b78f, #62d7b0);
}

.panel-full {
  grid-column: 1 / -1;
  min-height: auto;
}

@keyframes grow {
  from {
    width: 0;
  }
}

@media (max-width: 1500px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .panel-grid {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .double-donut {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .screen-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .screen-head h2 {
    font-size: 22px;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .bar-item {
    grid-template-columns: 90px 1fr 42px;
  }
}
</style>
