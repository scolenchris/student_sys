import axios from "axios";

const api = axios.create({
  // baseURL: "http://localhost:5000/api/admin", // 确保指向 Flask 后端
  // baseURL: "http://192.168.149.177:5000/api/admin", // 确保指向 Flask 后端
  baseURL: "/api/admin",
  timeout: 5000,
});

// --- 用户与教师管理 ---
export const getPendingUsers = () => api.get("/pending_users");
export const approveUser = (id) => api.post(`/approve_user/${id}`);
export const rejectUser = (id) => api.delete(`/reject_user/${id}`);
export const getTeachers = (params) => api.get("/teachers", { params });
export const updateTeacher = (id, data) => api.put(`/teachers/${id}`, data);

// --- 班级管理 ---
export const getClasses = () => api.get("/classes");
export const addClass = (data) => api.post("/classes", data);

// --- 学生管理 ---
export const getStudents = (params) => api.get("/students", { params });
export const addStudent = (data) => api.post("/students", data);
export const updateStudent = (id, data) => api.put(`/students/${id}`, data);

// --- 成绩统计 ---
export const getClassReport = (params) =>
  api.get("/stats/class_report", { params });
export const getExamNames = (entry_year) =>
  api.get("/stats/exam_names", { params: { entry_year } });
export const getComprehensiveReport = (data) =>
  api.post("/stats/comprehensive_report", data);
export const getScoreRankTrend = (data) =>
  api.post("/stats/score_rank_trend", data);
export const exportScoreRankTrendExcel = (data) =>
  api.post("/stats/score_rank_trend_export", data, {
    responseType: "blob",
  });

// --- 科目登记 ---
export const getAssignments = (params) => api.get("/assignments", { params });
export const addAssignment = (data) => api.post("/assignments", data);
export const deleteAssignment = (id) => api.delete(`/assignments/${id}`);
export const getSubjects = () => api.get("/subjects"); //科目下拉框选择

// --- 导入学生 Excel ---
export const importStudentsExcel = (formData) =>
  api.post("/students/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

// --- 导入老师信息 Excel ---
export const importTeachersExcel = (formData) =>
  api.post("/teachers/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

// --- 重置教师密码 ---
export const resetTeacherPassword = (teacherId) =>
  api.post(`/teachers/${teacherId}/reset_password`);

// --- 考试发布管理 ---
export const getExamTasks = (params) => api.get("/exam_tasks", { params });
export const addExamTask = (data) => api.post("/exam_tasks", data);
export const updateExamTask = (id, data) => api.put(`/exam_tasks/${id}`, data);
export const deleteExamTask = (id) => api.delete(`/exam_tasks/${id}`);

// --- 导入科目登记 Excel ---
export const importCourseAssignmentsExcel = (formData) =>
  api.post("/assignments/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

// --- 导出科目登记 Excel ---
export const exportCourseAssignments = () =>
  api.get("/assignments/export", {
    responseType: "blob", // 重要：必须声明接收二进制流
  });

// --- 导出教师信息 (Excel) ---
export const exportTeachers = (params) =>
  api.get("/teachers/export", {
    params, // 将参数传递给后端
    responseType: "blob",
  });

// --- 获取学生学籍证明 ---
export const getStudentCertificate = (studentId) =>
  api.get(`/students/${studentId}/certificate`, {
    responseType: "blob", // 必须加这个
  });

// --- 获取班级成绩统计 ---
export const getClassScoreStats = (data) =>
  api.post("/stats/class_score_stats", data);

// --- 教师教学成绩统计 ---
export const getTeacherScoreStats = (data) =>
  api.post("/stats/teacher_score_stats", data);

// 获取成绩录入模版 (或备份)
export const getScoreTemplate = (data) =>
  api.post("/stats/score_template", data, {
    responseType: "blob",
  });

// 严谨导入成绩
export const importAdminScores = (formData) =>
  api.post("/stats/import_scores", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

// --- 注册系统设置 ---
export const getSystemSettings = () => api.get("/system/settings");
export const updateSystemSettings = (data) =>
  api.post("/system/settings", data);

// --- 导入记录与回退 ---
export const getImportHistory = (params) => api.get("/imports/history", { params });
export const rollbackImportBatch = (id) => api.post(`/imports/${id}/rollback`);

// --- 管理员成绩录入专用接口 ---
// 1. 根据班级ID获取该班级能参加的所有考试 (带科目名)
export const getAdminClassExams = (params) =>
  api.get("/score_entry/exams", { params });

// 2. 获取打分名单
export const getAdminScoreList = (params) =>
  api.get("/score_entry/student_list", { params });

// 3. 保存成绩
export const saveAdminScores = (data) => api.post("/score_entry/save", data);

// 导出学生信息或者模板
export const exportStudents = (params) =>
  api.get("/students/export", {
    params,
    responseType: "blob",
  });

export const deleteStudent = (id) => api.delete(`/students/${id}`);
