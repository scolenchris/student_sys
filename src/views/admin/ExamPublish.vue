<template>
  <el-card>
    <template #header>
      <div class="header">
        <h3>考试发布与管理</h3>
        <el-button type="primary" @click="openDialog">发布新考试</el-button>
      </div>
    </template>

    <div style="margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap">
      <el-select
        v-model="filterAcademicYear"
        placeholder="筛选学年"
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="y in academicYearOptions"
          :key="y"
          :label="`${y}学年`"
          :value="y"
        />
      </el-select>

      <el-select
        v-model="filterEntryYear"
        placeholder="筛选年级"
        clearable
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="y in gradeOptions"
          :key="y.year"
          :label="y.label"
          :value="y.year"
        />
      </el-select>

      <el-select
        v-model="filterSubject"
        placeholder="筛选科目"
        clearable
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="s in subjects"
          :key="s.id"
          :label="s.name"
          :value="s.id"
        />
      </el-select>
    </div>

    <el-table :data="tasks" border stripe v-loading="loading">
      <el-table-column
        prop="academic_year"
        label="所属学年"
        width="100"
        sortable
      >
        <template #default="scope">
          {{ scope.row.academic_year }}学年
        </template>
      </el-table-column>

      <el-table-column prop="name" label="考试名称" min-width="150" />
      <el-table-column prop="grade_name" label="年级" width="100" />
      <el-table-column prop="subject_name" label="科目" width="100" />
      <el-table-column prop="full_score" label="满分" width="80" />
      <el-table-column label="录分进度" min-width="220">
        <template #default="scope">
          <div v-if="scope.row.assigned_class_count > 0" class="progress-cell">
            <div class="progress-text">
              {{ scope.row.progress_text }} 班
            </div>
            <el-progress
              :percentage="scope.row.completion_rate || 0"
              :status="scope.row.is_fully_completed ? 'success' : ''"
              :stroke-width="12"
            />
          </div>
          <el-tag v-else type="info">未分配任课班级</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="录入状态" width="100">
        <template #default="scope">
          <el-switch
            v-model="scope.row.is_active"
            active-text="开"
            inactive-text="关"
            inline-prompt
            @change="handleStatusChange(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="scope">
          <el-button type="primary" link @click="editFullScore(scope.row)"
            >改满分</el-button
          >
          <el-popconfirm
            title="确定删除吗？"
            @confirm="handleDelete(scope.row.id)"
          >
            <template #reference>
              <el-button type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog v-model="dialogVisible" title="发布考试任务" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="所属学年">
          <el-select v-model="form.academic_year" style="width: 100%">
            <el-option
              v-for="y in academicYearOptions"
              :key="y"
              :label="`${y}学年`"
              :value="y"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择年级">
          <el-select
            v-model="form.entry_year"
            style="width: 100%"
            placeholder="例如 2023级"
          >
            <el-option
              v-for="y in gradeOptions"
              :key="y.year"
              :label="y.label"
              :value="y.year"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="考试类型">
          <el-select
            v-model="form.name"
            allow-create
            filterable
            default-first-option
            placeholder="选择或输入自定义名称"
            style="width: 100%"
          >
            <el-option
              v-for="t in predefinedTypes"
              :key="t"
              :label="t"
              :value="t"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择科目">
          <el-select
            v-model="form.subject_id"
            placeholder="选择科目"
            style="width: 100%"
          >
            <el-option
              v-for="s in subjects"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="满分值">
          <el-input-number v-model="form.full_score" :min="1" :max="999" />
        </el-form-item>

        <el-form-item label="初始状态">
          <el-radio-group v-model="form.is_active">
            <el-radio :label="true">允许录入</el-radio>
            <el-radio :label="false">暂时关闭</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定发布</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import {
  getExamTasks,
  addExamTask,
  updateExamTask,
  deleteExamTask,
  getSubjects,
} from "../../api/admin";
import { ElMessage, ElMessageBox } from "element-plus";

const tasks = ref([]);
const subjects = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

// 学年按 8 月切换：8 月前为上一学年，8 月及以后为当前学年。
const now = new Date();
const currentRealYear = now.getFullYear();
const defaultAcademicYear =
  now.getMonth() >= 7 ? currentRealYear : currentRealYear - 1;

const filterAcademicYear = ref(defaultAcademicYear);
const filterEntryYear = ref(null);
const filterSubject = ref(null);

const academicYearOptions = computed(() => {
  const years = [];
  for (let i = -2; i < 3; i++) {
    years.push(defaultAcademicYear + i);
  }
  return years.sort((a, b) => b - a);
});

const gradeOptions = computed(() => {
  const base = now.getMonth() >= 7 ? currentRealYear : currentRealYear - 1;
  return [
    { year: base, label: `${base}级` },
    { year: base - 1, label: `${base - 1}级` },
    { year: base - 2, label: `${base - 2}级` },
  ];
});

const predefinedTypes = [
  "入学考",
  "初一上期末",
  "初一上期中",
  "初二上期中",
  "初二上期末",
  "初三上期中",
  "初三上期末",
  "初一下期中",
  "初一下期末",
  "初二下期中",
  "初二下期末",
  "初三下期中",
  "初三下期末",
  "初三校一模",
  "初三区一模",
  "初三区二模",
];

const form = reactive({
  academic_year: defaultAcademicYear,
  entry_year: null,
  name: "",
  subject_id: null,
  full_score: 100,
  is_active: true,
});

const fetchTasks = async () => {
  loading.value = true;
  try {
    const res = await getExamTasks({
      academic_year: filterAcademicYear.value,
      entry_year: filterEntryYear.value,
      subject_id: filterSubject.value,
      paged: 1,
      page: page.value,
      page_size: pageSize.value,
    });
    tasks.value = res.data.items || [];
    total.value = res.data.total || 0;
  } finally {
    loading.value = false;
  }
};

const handleFilterChange = () => {
  page.value = 1;
  fetchTasks();
};

const handlePageChange = () => {
  fetchTasks();
};

const handlePageSizeChange = () => {
  page.value = 1;
  fetchTasks();
};

const fetchSubjects = async () => {
  const res = await getSubjects();
  subjects.value = res.data;
};

const openDialog = () => {
  // 默认沿用当前筛选学年，便于连续录入。
  form.academic_year = filterAcademicYear.value || defaultAcademicYear;
  form.entry_year = null;
  form.name = "";
  form.subject_id = null;
  form.full_score = 100;
  form.is_active = true;
  dialogVisible.value = true;
};

const submitForm = async () => {
  if (
    !form.academic_year ||
    !form.entry_year ||
    !form.name ||
    !form.subject_id
  ) {
    return ElMessage.warning("请填写完整信息（含学年）");
  }
  try {
    await addExamTask(form);
    ElMessage.success("发布成功");
    dialogVisible.value = false;
    fetchTasks();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "发布失败");
  }
};

const handleStatusChange = async (row) => {
  try {
    await updateExamTask(row.id, { is_active: row.is_active });
    ElMessage.success("状态已更新");
  } catch (err) {
    row.is_active = !row.is_active;
    ElMessage.error("更新失败");
  }
};

const editFullScore = (row) => {
  ElMessageBox.prompt("请输入新的满分值", "修改满分", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    inputPattern: /^\d+$/,
    inputErrorMessage: "请输入数字",
    inputValue: row.full_score,
  }).then(async ({ value }) => {
    await updateExamTask(row.id, { full_score: value });
    ElMessage.success("修改成功");
    fetchTasks();
  });
};

const handleDelete = async (id) => {
  try {
    await deleteExamTask(id);
    ElMessage.success("删除成功");
    if (tasks.value.length === 1 && page.value > 1) {
      page.value -= 1;
    }
    fetchTasks();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "删除失败");
  }
};

onMounted(() => {
  fetchSubjects();
  fetchTasks();
});
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-text {
  color: #606266;
  font-size: 12px;
}
.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
