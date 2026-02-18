import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 5000,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      localStorage.removeItem("user_id");
      localStorage.removeItem("user_role");
      localStorage.removeItem("username");
      localStorage.removeItem("must_change_password");
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

export default api;
