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

    <el-table :data="classes" stripe border>
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
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

  </el-card>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getClasses, deleteClass } from "../../api/admin";
import { ElMessage, ElMessageBox } from "element-plus";

const classes = ref([]);
const deletingClassId = ref(null);

const fetchClasses = async () => {
  try {
    const res = await getClasses();
    classes.value = res.data;
  } catch (error) {
    ElMessage.error("获取班级列表失败");
  }
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
    fetchClasses();
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || "删除失败");
  } finally {
    deletingClassId.value = null;
  }
};

onMounted(fetchClasses);
</script>
