import api from "./http";

export const loginApi = (data) => api.post("/auth/login", data);
export const registerApi = (data) => api.post("/auth/register", data);
export const changePasswordApi = (data) => api.post("/auth/change_password", data);
export const logoutApi = () => api.post("/auth/logout");
export const getRegisterConfig = () => api.get("/auth/register_config");
