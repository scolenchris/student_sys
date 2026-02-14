<template>
  <el-card class="stats-card">
    <template #header>
      <div class="header-row">
        <h3>综合成绩统计与排名</h3>
        <div class="action-group">
          <el-button-group>
            <el-button
              type="warning"
              plain
              @click="handleTemplateDownload('template')"
              :disabled="!query.entry_year || query.subject_ids.length === 0"
            >
              <el-icon><Document /></el-icon> 下载录入模版
            </el-button>
            <el-button
              type="success"
              plain
              @click="handleTemplateDownload('backup')"
              :disabled="!query.entry_year || !query.exam_name"
            >
              <el-icon><Download /></el-icon> 导出备份
            </el-button>
          </el-button-group>

          <el-upload
            class="upload-inline"
            action=""
            :show-file-list="false"
            :http-request="handleStrictImport"
            accept=".xlsx, .xls"
            style="display: inline-block; margin-left: 10px"
          >
            <el-button type="primary">
              <el-icon><Upload /></el-icon> 严谨导入成绩
            </el-button>
          </el-upload>

          <el-button
            type="info"
            @click="exportCSV"
            :disabled="tableData.length === 0"
            style="margin-left: 10px"
          >
            导出统计报表
          </el-button>
        </div>
      </div>
    </template>

    <el-form :inline="true" class="filter-bar">
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
          placeholder="先选年级"
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
          placeholder="选择科目"
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

      <el-form-item label="显示班级">
        <el-select
          v-model="query.class_ids"
          multiple
          collapse-tags
          placeholder="默认全级 (可多选)"
          style="width: 220px"
          :disabled="!query.entry_year"
        >
          <el-option
            v-for="c in filteredClassOptions"
            :key="c.id"
            :label="`${c.grade_name}(${c.class_num})班`"
            :value="c.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSearch" :loading="loading"
          >查询</el-button
        >
      </el-form-item>
    </el-form>

    <el-table
      :data="tableData"
      border
      stripe
      height="600"
      v-loading="loading"
      style="width: 100%"
    >
      <el-table-column label="级排名 (Grade Rank)" align="center" fixed>
        <el-table-column
          prop="grade_rank_skip"
          width="95"
          sortable
          align="center"
        >
          <template #header>
            <span>总分排名</span>
            <el-tooltip
              content="仅按总分排序。同分同名，名次跳过 (例: 1, 1, 3)"
              placement="top"
            >
              <el-icon style="margin-left: 3px; vertical-align: middle"
                ><InfoFilled
              /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column
          prop="grade_rank_dense"
          width="95"
          sortable
          align="center"
        >
          <template #header>
            <span>规则排名</span>
            <el-tooltip
              content="严格排序 (1, 2, 3...)。总分相同时，依次比较：语、数、英、听说、理、化、道法、史、生、地、体、信、美、音"
              placement="top"
            >
              <el-icon style="margin-left: 3px; vertical-align: middle"
                ><InfoFilled
              /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table-column>

      <el-table-column label="班排名 (Class Rank)" align="center">
        <el-table-column
          prop="class_rank_skip"
          label="总分"
          width="70"
          align="center"
        />
        <el-table-column
          prop="class_rank_dense"
          label="规则"
          width="70"
          align="center"
        />
      </el-table-column>
      <el-table-column prop="student_id" label="学号" width="120" fixed />
      <el-table-column prop="name" label="姓名" width="100" fixed />
      <el-table-column
        prop="class_name"
        label="班级"
        width="110"
        show-overflow-tooltip
      />
      <el-table-column prop="status" label="状态" width="70">
        <template #default="scope">
          <el-tag
            size="small"
            :type="scope.row.status === '在读' ? 'success' : 'info'"
          >
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column
        v-for="sub in dynamicColumns"
        :key="sub"
        :label="sub"
        min-width="80"
        align="center"
      >
        <template #default="scope">
          <span
            v-if="scope.row.scores[sub] === '缺考'"
            style="color: #f56c6c; font-weight: bold"
          >
            缺考
          </span>
          <span v-else-if="scope.row.scores[sub] !== undefined">
            {{ scope.row.scores[sub] }}
          </span>
          <span v-else style="color: #ddd">-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="total"
        label="总分"
        width="90"
        fixed="right"
        sortable
      />
      <el-table-column
        prop="full_score"
        label="满分值"
        width="80"
        fixed="right"
      />
    </el-table>
    <el-dialog
      v-model="importResult.visible"
      title="导入结果报告"
      width="700px"
    >
      <div v-if="importResult.status === 'error'">
        <el-alert
          title="导入失败：数据未写入"
          type="error"
          show-icon
          :closable="false"
        >
          <template #default>
            <div>
              检测到致命错误，为保证数据一致性，所有操作已回滚。请修正Excel后重试。
            </div>
          </template>
        </el-alert>
        <div class="error-list">
          <h4>致命错误详情：</h4>
          <el-scrollbar max-height="300px">
            <ul>
              <li
                v-for="(err, idx) in importResult.logs.fatal_errors"
                :key="idx"
                style="color: #f56c6c"
              >
                {{ err }}
              </li>
            </ul>
          </el-scrollbar>
        </div>
      </div>

      <div v-else>
        <el-alert
          :title="importResult.msg"
          type="success"
          show-icon
          :closable="false"
        />

        <div v-if="importResult.logs.warnings?.length" style="margin-top: 15px">
          <el-alert
            title="冗余数据警告 (已自动忽略，不影响导入)"
            type="warning"
            :closable="false"
          />
          <el-scrollbar max-height="150px">
            <ul>
              <li
                v-for="(w, idx) in importResult.logs.warnings"
                :key="idx"
                style="color: #e6a23c"
              >
                {{ w }}
              </li>
            </ul>
          </el-scrollbar>
        </div>

        <div
          v-if="importResult.logs.missing_students?.length"
          style="margin-top: 15px"
        >
          <el-alert title="缺失名单提示" type="info" :closable="false" />
          <ul>
            <li
              v-for="(m, idx) in importResult.logs.missing_students"
              :key="idx"
              style="color: #909399"
            >
              {{ m }}
            </li>
          </ul>
        </div>
      </div>

      <template #footer>
        <el-button @click="importResult.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import {
  getSubjects,
  getClasses,
  getExamNames,
  getComprehensiveReport,
  getScoreTemplate,
  importAdminScores,
} from "../../api/admin";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  InfoFilled,
  Document,
  Upload,
  Download,
} from "@element-plus/icons-vue";

// --- State ---
const loading = ref(false);
const subjectOptions = ref([]); // 所有可选科目
const allClassOptions = ref([]); // 所有班级列表
const examNameOptions = ref([]); // 当前年级的考试名称列表

const tableData = ref([]);
const dynamicColumns = ref([]); // 后端返回的科目名称列表，用于表头

const query = reactive({
  entry_year: null,
  exam_name: "",
  subject_ids: [],
  class_ids: [],
});

const importResult = reactive({
  visible: false,
  status: "success",
  msg: "",
  logs: {},
});

// --- Computed ---

// 生成最近5年的年级选项
const currentYear = new Date().getFullYear();
const gradeOptions = computed(() => {
  // 1. 如果还没有加载到班级数据，返回空
  if (!allClassOptions.value || allClassOptions.value.length === 0) {
    return [];
  }

  // 2. 提取所有班级的 entry_year
  const years = allClassOptions.value.map((c) => c.entry_year);

  // 3. 去重 (利用 Set)
  const uniqueYears = [...new Set(years)];

  // 4. 排序 (降序，让最近的年份如 2025 排在前面)
  uniqueYears.sort((a, b) => b - a);

  // 5. 映射为下拉框需要的格式
  return uniqueYears.map((y) => ({ year: y, label: `${y}级` }));
});

// 根据选中的年级，筛选出属于该年级的班级选项
const filteredClassOptions = computed(() => {
  if (!query.entry_year) return [];
  return allClassOptions.value.filter((c) => c.entry_year === query.entry_year);
});

// --- Methods ---

// 初始化加载基础数据
const initData = async () => {
  try {
    const [sRes, cRes] = await Promise.all([getSubjects(), getClasses()]);
    subjectOptions.value = sRes.data;
    allClassOptions.value = cRes.data;

    // 默认选中所有科目方便用户
    // query.subject_ids = sRes.data.map(s => s.id);
  } catch (err) {
    ElMessage.error("初始化数据失败");
  }
};

// 年级改变时：1. 清空考试名和班级选择 2. 获取该年级的考试列表
const handleYearChange = async (val) => {
  query.exam_name = "";
  query.class_ids = [];
  tableData.value = [];
  examNameOptions.value = [];

  if (!val) return;

  try {
    const res = await getExamNames(val);
    examNameOptions.value = res.data;
  } catch (err) {
    ElMessage.error("获取考试列表失败");
  }
};

// 执行查询
const handleSearch = async () => {
  // 简单校验
  if (!query.entry_year || !query.exam_name || query.subject_ids.length === 0) {
    // 还没选完时不强制报错，只是不查
    return;
  }

  loading.value = true;
  try {
    const res = await getComprehensiveReport({
      entry_year: query.entry_year,
      exam_name: query.exam_name,
      subject_ids: query.subject_ids,
      class_ids: query.class_ids,
    });

    tableData.value = res.data.data;
    dynamicColumns.value = res.data.subjects; // 确保表头顺序和后端一致

    if (tableData.value.length === 0) {
      ElMessage.info("未查询到相关成绩数据");
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "查询失败");
  } finally {
    loading.value = false;
  }
};

// 导出 CSV
const exportCSV = () => {
  if (tableData.value.length === 0) return;

  // 更新表头
  const headers = [
    "级排名(总分并列)",
    "级排名(规则严格)",
    "班排名(总分并列)",
    "班排名(规则严格)",
    "学号",
    "姓名",
    "班级",
    "状态",
    ...dynamicColumns.value,
    "总分",
    "满分值",
  ];

  let csvContent =
    "data:text/csv;charset=utf-8,\ufeff" + headers.join(",") + "\n";

  tableData.value.forEach((row) => {
    const subScores = dynamicColumns.value.map((sub) =>
      row.scores[sub] !== undefined ? row.scores[sub] : "-",
    );

    const rowData = [
      row.grade_rank_skip,
      row.grade_rank_dense,
      row.class_rank_skip,
      row.class_rank_dense,
      row.student_id,
      row.name,
      row.class_name,
      row.status,
      ...subScores,
      row.total,
      row.full_score,
    ];
    csvContent += rowData.join(",") + "\n";
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  const fileName = `${query.entry_year}级_${query.exam_name}_成绩报表.csv`;
  link.setAttribute("download", fileName);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

const handleTemplateDownload = async (type) => {
  // 校验
  if (!query.entry_year) return ElMessage.warning("请选择年级");
  if (query.subject_ids.length === 0)
    return ElMessage.warning("请至少选择一个科目");

  if (type === "backup" && !query.exam_name) {
    return ElMessage.warning("导出备份必须选择考试名称");
  }

  try {
    const res = await getScoreTemplate({
      entry_year: query.entry_year,
      class_ids: query.class_ids, // 支持按班级筛选导出
      subject_ids: query.subject_ids,
      exam_name: type === "backup" ? query.exam_name : null,
    });

    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    const prefix = type === "backup" ? "成绩备份" : "录入模版";
    link.setAttribute("download", `${query.entry_year}级_${prefix}.xlsx`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (err) {
    ElMessage.error("下载失败");
  }
};

// 2. 严谨导入
const handleStrictImport = async (param) => {
  // 前置校验
  if (!query.entry_year || !query.exam_name || query.subject_ids.length === 0) {
    return ElMessage.warning(
      "请务必先在上方筛选栏选择：年级、考试名称、以及本次要导入的科目！",
    );
  }

  // 二次确认
  try {
    await ElMessageBox.confirm(
      `即将向【${query.entry_year}级 - ${query.exam_name}】导入 ${query.subject_ids.length} 个科目的成绩。\n请确保Excel表头与系统科目名称严格一致。`,
      "导入确认",
      {
        confirmButtonText: "确定导入",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  const formData = new FormData();
  formData.append("file", param.file);
  formData.append("entry_year", query.entry_year);
  formData.append("exam_name", query.exam_name);
  formData.append("subject_ids", JSON.stringify(query.subject_ids)); // 传数组
  formData.append("class_ids", JSON.stringify(query.class_ids)); // 传数组

  const loadingInst = ElMessage.success({
    message: "正在进行原子性校验与导入...",
    duration: 0,
  });

  try {
    const res = await importAdminScores(formData);
    loadingInst.close();

    // 无论是 success 还是 error (如果是后端处理过的业务error)，都弹窗显示详情
    // 注意：axios 拦截器可能会拦截非 200 响应。
    // 如果后端返回 200 但 status='error' (业务逻辑拒绝)，走这里：
    if (res.data.status === "error") {
      importResult.status = "error";
      importResult.msg = res.data.msg;
    } else {
      importResult.status = "success";
      importResult.msg = res.data.msg;
      // 导入成功后刷新列表
      handleSearch();
    }
    importResult.logs = res.data.logs;
    importResult.visible = true;
  } catch (err) {
    loadingInst.close();
    // 如果是 400 等 HTTP 错误，通常在这里捕获
    if (err.response && err.response.data && err.response.data.logs) {
      // 这是我们在后端返回的带 logs 的 400/200 响应
      importResult.status = "error";
      importResult.msg = err.response.data.msg;
      importResult.logs = err.response.data.logs;
      importResult.visible = true;
    } else {
      ElMessage.error(err.response?.data?.msg || "导入请求失败");
    }
  }
};

onMounted(initData);
</script>

<style scoped>
.error-list ul {
  padding-left: 20px;
  margin: 5px 0;
}
.upload-inline {
  display: inline-block;
}
.stats-card {
  min-height: 80vh;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-bar {
  margin-bottom: 10px;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}
</style>
