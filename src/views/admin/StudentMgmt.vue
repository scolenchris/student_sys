<template>
  <el-card>
    <div
      style="margin-bottom: 20px; display: flex; justify-content: space-between"
    >
      <div style="display: flex; gap: 10px">
        <el-select
          v-model="filterClassId"
          placeholder="按班级筛选"
          clearable
          @change="handleFilterChange"
          style="width: 200px"
        >
          <el-option
            v-for="c in classes"
            :key="c.id"
            :label="formatClassName(c)"
            :value="c.id"
          />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="按姓名/学号搜索"
          clearable
          style="width: 220px"
          @keyup.enter="handleKeywordSearch"
          @clear="handleKeywordSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" plain @click="handleKeywordSearch">
          搜索
        </el-button>
        <el-button type="warning" plain @click="handleExport">
          <el-icon style="margin-right: 5px"><Download /></el-icon>
          下载学生名单模板
        </el-button>
      </div>

      <div>
        <el-upload
          class="upload-demo"
          action=""
          :show-file-list="false"
          :http-request="handleUpload"
          accept=".xlsx, .xls"
          style="display: inline-block; margin-right: 10px"
        >
          <el-button type="success">导入学生Excel</el-button>
        </el-upload>
        <el-button type="primary" @click="openDialog('add')"
          >新增学生</el-button
        >
      </div>
    </div>

    <el-table
      :data="studentData"
      v-loading="loading"
      border
      stripe
      size="small"
    >
      <el-table-column prop="name" label="姓名" width="80" fixed />
      <el-table-column prop="gender" label="性别" width="50" />
      <el-table-column prop="student_id" label="学号" width="110" />
      <el-table-column prop="grade_class" label="班级" width="110" />
      <el-table-column prop="status" label="状态" width="70">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)" size="small">{{
            scope.row.status
          }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column
        prop="id_card_number"
        label="身份证号"
        width="170"
        show-overflow-tooltip
      />
      <el-table-column
        prop="city_school_id"
        label="市学籍号"
        width="130"
        show-overflow-tooltip
      />
      <el-table-column
        prop="national_school_id"
        label="国家学籍号"
        width="150"
        show-overflow-tooltip
      />
      <el-table-column prop="household_registration" label="户籍" width="80" />

      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button
            type="primary"
            link
            size="small"
            @click="openDialog('edit', scope.row)"
          >
            编辑学生
          </el-button>
          <el-popconfirm
            title="确定要删除该学生吗？"
            description="此操作将同步删除该学生的所有成绩记录，且不可恢复！"
            confirm-button-text="确定删除"
            cancel-button-text="取消"
            @confirm="handleDelete(scope.row)"
          >
            <template #reference>
              <el-button size="small" type="danger" plain>删除学生</el-button>
            </template>
          </el-popconfirm>
          <el-button
            type="warning"
            link
            size="small"
            @click="handlePrintCert(scope.row)"
          >
            <el-icon><Document /></el-icon> 下载证明
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '录入新学生' : '编辑学生信息'"
      width="650px"
    >
      <el-form :model="form" label-width="100px" :inline="true">
        <el-form-item label="学号">
          <el-input
            v-model="form.student_id"
            :disabled="dialogType === 'edit'"
            style="width: 170px"
          />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.name" style="width: 170px" />
        </el-form-item>

        <el-form-item label="班级">
          <el-select v-model="form.class_id" style="width: 170px">
            <el-option
              v-for="c in classes"
              :key="c.id"
              :label="formatClassName(c)"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input
            v-model="form.id_card_number"
            placeholder="请输入18位身份证"
            maxlength="18"
            style="width: 170px"
          />
        </el-form-item>

        <el-divider content-position="left">学籍详细信息</el-divider>

        <el-form-item label="市学籍号">
          <el-input
            v-model="form.city_school_id"
            placeholder="纯数字"
            style="width: 170px"
          />
        </el-form-item>
        <el-form-item label="国家学籍号">
          <el-input
            v-model="form.national_school_id"
            placeholder="如 G440..."
            style="width: 170px"
          />
        </el-form-item>

        <el-form-item label="户口属地">
          <el-select v-model="form.household_registration" style="width: 170px">
            <el-option label="本市" value="本市" />
            <el-option label="外市" value="外市" />
            <el-option label="港澳台" value="港澳台" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 170px">
            <el-option label="在读" value="在读" />
            <el-option label="休学" value="休学" />
            <el-option label="转出" value="转出" />
            <el-option label="毕业" value="毕业" />
            <el-option label="复学" value="复学" />
          </el-select>
        </el-form-item>

        <el-form-item label="性别" style="width: 100%">
          <el-radio-group v-model="form.gender">
            <el-radio label="男">男</el-radio>
            <el-radio label="女">女</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="备注" style="width: 100%">
          <el-input
            v-model="form.remarks"
            type="textarea"
            :rows="2"
            style="width: 460px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消编辑</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting"
          >保存学生信息</el-button
        >
      </template>
    </el-dialog>

    <el-pagination
      layout="total, sizes, prev, pager, next"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      @current-change="handlePageChange"
      @size-change="handlePageSizeChange"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      style="margin-top: 20px; text-align: right"
    />
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import {
  getStudents,
  addStudent,
  updateStudent,
  getClasses,
  importStudentsExcel,
  getStudentCertificate,
  exportStudents,
  deleteStudent,
} from "../../api/admin";
import { ElMessage } from "element-plus";
import { Document, Upload, Download, Search } from "@element-plus/icons-vue";

const formatClassName = (c) =>
  `${String(c.entry_year).slice(-2)}级(${String(c.class_num).padStart(
    2,
    "0",
  )})班`;
const getStatusType = (s) =>
  ({ 在读: "success", 休学: "warning", 转出: "info" })[s] || "";

const studentData = ref([]);
const classes = ref([]);
const filterClassId = ref(null);
const keyword = ref("");
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const dialogVisible = ref(false);
const dialogType = ref("add");
const submitting = ref(false);

const form = reactive({
  id: null,
  student_id: "",
  name: "",
  gender: "男",
  class_id: null,
  status: "在读",
  household_registration: "本市",
  city_school_id: "",
  national_school_id: "",
  id_card_number: "",
  remarks: "",
});

const openDialog = (type, row = null) => {
  dialogType.value = type;
  dialogVisible.value = true;
  if (type === "add") {
    Object.assign(form, {
      id: null,
      student_id: "",
      name: "",
      gender: "男",
      class_id: filterClassId.value || null,
      status: "在读",
      household_registration: "本市",
      city_school_id: "",
      national_school_id: "",
      id_card_number: "",
      remarks: "",
    });
  } else {
    Object.assign(form, row);
  }
};

const validateForm = () => {
  if (!form.student_id || !form.name || !form.class_id) {
    ElMessage.warning("请填写必填项(学号、姓名、班级)");
    return false;
  }
  if (form.city_school_id && !/^\d+$/.test(form.city_school_id)) {
    ElMessage.warning("市学籍号必须为纯数字");
    return false;
  }
  // 身份证号做基础长度校验，完整校验交给后端。
  if (form.id_card_number && form.id_card_number.length !== 18) {
    ElMessage.warning("身份证号应为18位");
    return false;
  }
  return true;
};

const submitForm = async () => {
  if (!validateForm()) return;

  submitting.value = true;
  try {
    if (dialogType.value === "add") {
      await addStudent(form);
      ElMessage.success("添加成功");
    } else {
      await updateStudent(form.id, form);
      ElMessage.success("更新成功");
    }
    dialogVisible.value = false;
    fetchStudents();
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || "操作失败");
  } finally {
    submitting.value = false;
  }
};

const fetchStudents = async () => {
  loading.value = true;
  try {
    const res = await getStudents({
      page: currentPage.value,
      page_size: pageSize.value,
      class_id: filterClassId.value,
      keyword: keyword.value,
    });
    studentData.value = res.data.data;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
};

const handlePageChange = (page) => {
  currentPage.value = page;
  fetchStudents();
};

const handlePageSizeChange = (size) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchStudents();
};

const handleFilterChange = () => {
  currentPage.value = 1;
  fetchStudents();
};

const handleKeywordSearch = () => {
  currentPage.value = 1;
  fetchStudents();
};

const fetchClasses = async () => {
  const res = await getClasses();
  classes.value = res.data;
};

onMounted(() => {
  fetchClasses();
  fetchStudents();
});

const handleUpload = async (param) => {
  const formData = new FormData();
  formData.append("file", param.file);

  const loadingInstance = ElMessage.success({
    message: "正在导入中，请稍候...",
    duration: 0,
  });

  try {
    const res = await importStudentsExcel(formData);
    loadingInstance.close();

    ElMessage.success(
      `导入成功！新增: ${res.data.added} 人，更新: ${res.data.updated} 人`,
    );

    // 导入后同步刷新班级与学生列表。
    fetchClasses();
    fetchStudents();
  } catch (err) {
    loadingInstance.close();
    ElMessage.error(err.response?.data?.msg || "导入失败");
  }
};

const handlePrintCert = async (row) => {
  const loading = ElMessage.success({
    message: "正在生成学籍证明，请稍候...",
    duration: 0,
  });

  try {
    const res = await getStudentCertificate(row.id);

    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${row.name}_学籍证明.docx`);
    document.body.appendChild(link);
    link.click();

    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    loading.close();
  } catch (err) {
    loading.close();
    ElMessage.error("生成失败，请检查是否缺少学籍号或模板文件");
  }
};

const handleExport = async () => {
  try {
    const res = await exportStudents({ class_id: filterClassId.value });

    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;

    let fname = "学生名单_备份.xlsx";
    if (filterClassId.value) {
      const cls = classes.value.find((c) => c.id === filterClassId.value);
      if (cls) fname = `${formatClassName(cls)}_学生名单.xlsx`;
    }

    link.setAttribute("download", fname);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    ElMessage.error("导出失败，请稍后重试");
    console.error(err);
  }
};

const handleDelete = async (row) => {
  try {
    await deleteStudent(row.id);
    ElMessage.success("删除成功");
    fetchStudents();
  } catch (err) {
    console.error(err);
    ElMessage.error(err.response?.data?.msg || "删除失败");
  }
};
</script>
