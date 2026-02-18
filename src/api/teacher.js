import axios from "axios";

const api = axios.create({
  // baseURL: "http://localhost:5000/api/teacher",
  // baseURL: "http://192.168.149.177:5000/api/teacher",
  baseURL: "/api/teacher",
  timeout: 5000,
});

// 教师任教课程
export const getMyCourses = (userId) => api.get(`/my_courses/${userId}`);

// 成绩列表
export const getScoreList = (params) => api.get("/score_list", { params });

// 批量保存成绩
export const saveScores = (data) => api.post("/save_scores", data);

// 可用考试
export const getAvailableExams = (params) =>
  api.get("/available_exams", { params });

// 导出成绩（Excel）
export const exportScores = (params) =>
  api.get("/export_scores", {
    params,
    responseType: "blob",
  });

// 导入成绩（Excel）
export const importScores = (formData) =>
  api.post("/import_scores", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
