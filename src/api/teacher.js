import api from "./http";

// 教师任教课程
export const getMyCourses = () => api.get("/teacher/my_courses");

// 成绩列表
export const getScoreList = (params) => api.get("/teacher/score_list", { params });

// 批量保存成绩
export const saveScores = (data) => api.post("/teacher/save_scores", data);

// 可用考试
export const getAvailableExams = (params) =>
  api.get("/teacher/available_exams", { params });

// 导出成绩（Excel）
export const exportScores = (params) =>
  api.get("/teacher/export_scores", {
    params,
    responseType: "blob",
  });

// 导入成绩（Excel）
export const importScores = (formData) =>
  api.post("/teacher/import_scores", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
