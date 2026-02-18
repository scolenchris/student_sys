import axios from "axios";

const api = axios.create({
  // baseURL: "http://localhost:5000/api",
  // baseURL: "http://192.168.149.177:5000/api",
  baseURL: "/api",
  timeout: 5000,
});

export const loginApi = (data) => api.post("/auth/login", data);
export const registerApi = (data) => api.post("/auth/register", data);
export const changePasswordApi = (data) =>
  api.post("/auth/change_password", data);
export const getRegisterConfig = () => api.get("/auth/register_config");
