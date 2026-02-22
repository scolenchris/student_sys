<template>
  <el-card>
    <template #header>
      <div
        style="
          display: flex;
          justify-content: space-between;
          align-items: center;
        "
      >
        <span>班级列表</span>
      </div>
    </template>

    <el-table :data="classes" stripe border v-loading="loading">
      <el-table-column prop="entry_year" label="入学年份" />
      <el-table-column prop="grade_name" label="当前年级" />
      <el-table-column prop="class_num" label="班号" />
      <el-table-column prop="student_count" label="学生数" width="90" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            type="danger"
            link
            :loading="deletingClassId === row.id"
            @click="handleDeleteClass(row)"
          >
            删除班级
          </el-button>
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

  </el-card>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getClasses, deleteClass } from "../../api/admin";
import { ElMessage, ElMessageBox } from "element-plus";

const classes = ref([]);
const deletingClassId = ref(null);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

const fetchClasses = async () => {
  loading.value = true;
  try {
    const res = await getClasses({
      paged: 1,
      page: page.value,
      page_size: pageSize.value,
    });
    classes.value = res.data.items || [];
    total.value = res.data.total || 0;
  } catch (error) {
    ElMessage.error("获取班级列表失败");
  } finally {
    loading.value = false;
  }
};

const handlePageChange = () => {
  fetchClasses();
};

const handlePageSizeChange = () => {
  page.value = 1;
  fetchClasses();
};

const handleDeleteClass = async (row) => {
  if (!row || !row.id) return;

  if ((row.student_count || 0) > 0) {
    return ElMessage.warning("该班级仍有学生，无法删除。请先完成学籍调整。");
  }

  const classLabel = `${row.grade_name}(${row.class_num})班`;

  try {
    await ElMessageBox.confirm(
      `确认删除班级【${classLabel}】？删除后无法恢复。`,
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  deletingClassId.value = row.id;
  try {
    const res = await deleteClass(row.id);
    ElMessage.success(res.data?.msg || "班级删除成功");
    if (classes.value.length === 1 && page.value > 1) {
      page.value -= 1;
    }
    fetchClasses();
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || "删除失败");
  } finally {
    deletingClassId.value = null;
  }
};

onMounted(fetchClasses);
</script>

<style scoped>
.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
