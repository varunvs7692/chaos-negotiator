import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "",
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  console.log(`[API] REQUEST: ${(config.method || "GET").toUpperCase()} ${config.url}`);
  return config;
});

api.interceptors.response.use(
  (response) => {
    console.log(`[API] RESPONSE (${response.status}):`, response.data);
    return response;
  },
  (error) => {
    console.error(
      `[API] ERROR (${error.response?.status || "Unknown"}):`,
      error.response?.data || error.message
    );
    return Promise.reject(error);
  }
);

export default api;
