import axios from "axios";

const api = axios.create({
  // baseURL: "http://localhost:5000/api/admin",
  // baseURL: "http://192.168.149.177:5000/api/admin",
  baseURL: "/api/admin",
  timeout: 5000,
});

// 用户与教师管理
export const getPendingUsers = () => api.get("/pending_users");
export const approveUser = (id) => api.post(`/approve_user/${id}`);
export const rejectUser = (id) => api.delete(`/reject_user/${id}`);
export const getTeachers = (params) => api.get("/teachers", { params });
export const updateTeacher = (id, data) => api.put(`/teachers/${id}`, data);

// 班级管理
export const getClasses = () => api.get("/classes");
export const addClass = (data) => api.post("/classes", data);
export const deleteClass = (id) => api.delete(`/classes/${id}`);

// 学生管理
export const getStudents = (params) => api.get("/students", { params });
export const addStudent = (data) => api.post("/students", data);
export const updateStudent = (id, data) => api.put(`/students/${id}`, data);

// 成绩统计
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

// 任课分配与科目
export const getAssignments = (params) => api.get("/assignments", { params });
export const addAssignment = (data) => api.post("/assignments", data);
export const deleteAssignment = (id) => api.delete(`/assignments/${id}`);
export const getSubjects = () => api.get("/subjects");

// 学生导入
export const importStudentsExcel = (formData) =>
  api.post("/students/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

// 教师导入
export const importTeachersExcel = (formData) =>
  api.post("/teachers/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

// 教师密码重置
export const resetTeacherPassword = (teacherId) =>
  api.post(`/teachers/${teacherId}/reset_password`);

// 考试任务
export const getExamTasks = (params) => api.get("/exam_tasks", { params });
export const addExamTask = (data) => api.post("/exam_tasks", data);
export const updateExamTask = (id, data) => api.put(`/exam_tasks/${id}`, data);
export const deleteExamTask = (id) => api.delete(`/exam_tasks/${id}`);

// 任课分配导入导出
export const importCourseAssignmentsExcel = (formData) =>
  api.post("/assignments/import", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

export const exportCourseAssignments = () =>
  api.get("/assignments/export", {
    // 以二进制流下载文件。
    responseType: "blob",
  });

// 教师导出
export const exportTeachers = (params) =>
  api.get("/teachers/export", {
    params,
    responseType: "blob",
  });

// 学生学籍证明
export const getStudentCertificate = (studentId) =>
  api.get(`/students/${studentId}/certificate`, {
    responseType: "blob",
  });

// 班级统计
export const getClassScoreStats = (data) =>
  api.post("/stats/class_score_stats", data);

// 教师统计
export const getTeacherScoreStats = (data) =>
  api.post("/stats/teacher_score_stats", data);

// 成绩模板/备份
export const getScoreTemplate = (data) =>
  api.post("/stats/score_template", data, {
    responseType: "blob",
  });

// 管理端成绩导入
export const importAdminScores = (formData) =>
  api.post("/stats/import_scores", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

// 系统设置
export const getSystemSettings = () => api.get("/system/settings");
export const updateSystemSettings = (data) =>
  api.post("/system/settings", data);

// 导入历史与回退
export const getImportHistory = (params) => api.get("/imports/history", { params });
export const rollbackImportBatch = (id) => api.post(`/imports/${id}/rollback`);

// 管理员成绩录入
export const getAdminClassExams = (params) =>
  api.get("/score_entry/exams", { params });

export const getAdminScoreList = (params) =>
  api.get("/score_entry/student_list", { params });

export const saveAdminScores = (data) => api.post("/score_entry/save", data);

// 学生导出
export const exportStudents = (params) =>
  api.get("/students/export", {
    params,
    responseType: "blob",
  });

export const deleteStudent = (id) => api.delete(`/students/${id}`);
