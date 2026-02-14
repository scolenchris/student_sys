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
        <!-- <el-button type="primary" @click="addVisible = true"
          >新增班级</el-button
        > -->
      </div>
    </template>

    <el-table :data="classes" stripe border>
      <el-table-column prop="entry_year" label="入学年份" />
      <el-table-column prop="grade_name" label="当前年级" />
      <el-table-column prop="class_num" label="班号" />
    </el-table>

    <!-- <el-dialog v-model="addVisible" title="新增班级" width="350px">
      <el-form :model="newClass" label-width="80px">
        <el-form-item label="入学年份">
          <el-input-number v-model="newClass.entry_year" :min="2020" :max="2099" style="width: 100%" />
        </el-form-item>
        <el-form-item label="班级号">
          <el-input-number v-model="newClass.class_num" :min="1" :max="30" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" @click="submitClass" :loading="submitting">确定</el-button>
      </template>
    </el-dialog> -->
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { getClasses, addClass } from "../../api/admin"; // 确保引用了 api
import { ElMessage } from "element-plus";

const classes = ref([]);
const addVisible = ref(false);
const submitting = ref(false);

const newClass = reactive({
  entry_year: new Date().getFullYear(),
  class_num: 1,
});

// 获取班级列表
const fetchClasses = async () => {
  try {
    const res = await getClasses();
    classes.value = res.data;
  } catch (error) {
    ElMessage.error("获取班级列表失败");
  }
};

// 提交新增班级
const submitClass = async () => {
  if (!newClass.entry_year || !newClass.class_num) {
    return ElMessage.warning("请填写完整信息");
  }

  submitting.value = true;
  try {
    const res = await addClass(newClass);
    ElMessage.success(res.data.msg || "添加成功");
    addVisible.value = false; // 关闭弹窗
    fetchClasses(); // 刷新列表
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || "添加失败");
  } finally {
    submitting.value = false;
  }
};

onMounted(fetchClasses);
</script>
