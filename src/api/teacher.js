import axios from "axios";

// 配置指向后端 teacher 蓝图的地址
const api = axios.create({
  // baseURL: "http://localhost:5000/api/teacher",
  // baseURL: "http://192.168.149.177:5000/api/teacher",
  baseURL: "/api/teacher",
  timeout: 5000,
});

/**
 * 获取老师的任教课程列表
 * @param {number} userId
 */
export const getMyCourses = (userId) => api.get(`/my_courses/${userId}`);

/**
 * 获取指定班级、科目、学期的学生成绩列表
 * @param {Object} params { class_id, subject_id, term }
 */
export const getScoreList = (params) => api.get("/score_list", { params });

/**
 * 批量保存成绩
 * @param {Object} data { subject_id, term, scores: [...] }
 */
export const saveScores = (data) => api.post("/save_scores", data);

// 获取可用考试
export const getAvailableExams = (params) =>
  api.get("/available_exams", { params });

// 导出成绩单 (Excel)
export const exportScores = (params) =>
  api.get("/export_scores", {
    params,
    responseType: "blob", //以此格式接收二进制流文件
  });

// 导入成绩单 (Excel)
export const importScores = (formData) =>
  api.post("/import_scores", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
