<template>
  <el-card>
    <template #header>
      <div class="header">
        <div style="display: flex; align-items: center; gap: 15px">
          <span style="font-weight: bold; font-size: 16px">任课分配管理</span>

          <el-select
            v-model="currentAcademicYear"
            placeholder="学年"
            style="width: 140px"
            size="small"
            @change="handleYearChange"
          >
            <el-option
              v-for="year in academicYearOptions"
              :key="year"
              :label="`${year}-${year + 1}学年`"
              :value="year"
            />
          </el-select>
        </div>

        <div style="display: flex; gap: 10px">
          <el-upload
            class="upload-demo"
            action=""
            :show-file-list="false"
            :http-request="handleImport"
            accept=".xlsx, .xls"
          >
            <el-button type="success">
              <el-icon style="margin-right: 5px"><Upload /></el-icon>
              批量导入任课表
            </el-button>
          </el-upload>

          <el-button type="primary" @click="openDialog">
            <el-icon style="margin-right: 5px"><Plus /></el-icon>
            新增任课分配
          </el-button>
          <el-button type="warning" @click="handleExport">
            <el-icon style="margin-right: 5px"><Download /></el-icon>
            下载任课表模板
          </el-button>
        </div>
      </div>
    </template>

    <el-table :data="assignments" border stripe v-loading="loading">
      <el-table-column prop="teacher_name" label="教师姓名" />
      <el-table-column prop="grade_class" label="任教班级" sortable />
      <el-table-column prop="subject_name" label="教学科目" sortable />
      <el-table-column label="操作" width="120" align="center">
        <template #default="scope">
          <el-popconfirm
            title="确定取消该任课分配吗？"
            @confirm="handleDelete(scope.row.id)"
          >
            <template #reference>
              <el-button type="danger" link size="small">移除任课分配</el-button>
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

    <el-dialog
      v-model="visible"
      :title="`新增任课 (${currentAcademicYear}学年)`"
      width="400px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="选择教师">
          <el-select
            v-model="form.teacher_id"
            placeholder="请选择"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="t in teachers"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择班级">
          <el-select
            v-model="form.class_id"
            placeholder="请选择"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="c in classes"
              :key="c.id"
              :label="c.grade_name + '(' + c.class_num + ')班'"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择科目">
          <el-select
            v-model="form.subject_id"
            placeholder="请选择"
            filterable
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
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消本次分配</el-button>
        <el-button type="primary" @click="submit">提交任课分配</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="errorDialogVisible"
      title="导入失败 - 请检查以下问题"
      width="600px"
    >
      <div style="margin-bottom: 10px">
        <el-alert
          :title="importErrorMsg"
          type="error"
          show-icon
          :closable="false"
        />
      </div>
      <el-table
        :data="importErrors"
        height="300"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column label="错误详情" prop="msg">
          <template #default="scope">
            <span style="color: #f56c6c">{{ scope.row }}</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="errorDialogVisible = false">关闭错误详情</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from "vue";
import * as adminApi from "../../api/admin";
import { ElMessage } from "element-plus";
import { Upload, Plus, Download } from "@element-plus/icons-vue";

// 学年按 9 月切换。
const now = new Date();
const defaultYear =
  now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
const currentAcademicYear = ref(defaultYear);

const academicYearOptions = computed(() => {
  const years = [];
  for (let i = -2; i < 3; i++) years.push(defaultYear + i);
  return years.sort((a, b) => b - a);
});

const assignments = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const teachers = ref([]);
const classes = ref([]);
const subjects = ref([]);
const visible = ref(false);
const loading = ref(false);

const errorDialogVisible = ref(false);
const importErrors = ref([]);
const importErrorMsg = ref("");

const form = reactive({ teacher_id: "", class_id: "", subject_id: "" });

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await adminApi.getAssignments({
      academic_year: currentAcademicYear.value,
      paged: 1,
      page: page.value,
      page_size: pageSize.value,
    });
    assignments.value = res.data.items || [];
    total.value = res.data.total || 0;
  } finally {
    loading.value = false;
  }
};

const handleYearChange = () => {
  page.value = 1;
  fetchData();
};

const handlePageChange = () => {
  fetchData();
};

const handlePageSizeChange = () => {
  page.value = 1;
  fetchData();
};

const openDialog = async () => {
  const [tRes, cRes, sRes] = await Promise.all([
    adminApi.getTeachers(),
    adminApi.getClasses(),
    adminApi.getSubjects(),
  ]);
  teachers.value = tRes.data;
  classes.value = cRes.data;
  subjects.value = sRes.data;
  visible.value = true;
};

const submit = async () => {
  try {
    const postData = {
      ...form,
      academic_year: currentAcademicYear.value,
    };

    await adminApi.addAssignment(postData);
    ElMessage.success("分配成功");
    visible.value = false;
    fetchData();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "分配失败");
  }
};

const handleDelete = async (id) => {
  try {
    await adminApi.deleteAssignment(id);
    ElMessage.success("已取消分配");
    if (assignments.value.length === 1 && page.value > 1) {
      page.value -= 1;
    }
    fetchData();
  } catch (err) {
    ElMessage.error("操作失败");
  }
};

const handleImport = async (param) => {
  const formData = new FormData();
  formData.append("file", param.file);
  formData.append("academic_year", currentAcademicYear.value);

  const loadingInstance = ElMessage.success({
    message: `正在校验并导入 ${currentAcademicYear.value} 学年任课表...`,
    duration: 0,
  });

  try {
    const res = await adminApi.importCourseAssignmentsExcel(formData);
    loadingInstance.close();
    ElMessage.success(res.data.msg || "导入成功");
    fetchData();
  } catch (err) {
    loadingInstance.close();

    // 业务校验错误由后端返回详细错误列表。
    if (err.response && err.response.data && err.response.data.errors) {
      importErrorMsg.value = err.response.data.msg || "导入数据存在问题";
      importErrors.value = err.response.data.errors;
      errorDialogVisible.value = true;
    } else {
      ElMessage.error(err.response?.data?.msg || "导入失败，请检查文件格式");
    }
  }
};

const handleExport = async () => {
  try {
    const res = await adminApi.exportCourseAssignments();

    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "任课分配表(可直接导入).xlsx");

    document.body.appendChild(link);
    link.click();

    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "导出失败，请稍后重试");
  }
};

onMounted(fetchData);
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
