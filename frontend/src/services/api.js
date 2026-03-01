import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export const fetchLatestDeployment = async () => {
  const res = await api.get("/api/deployments/latest");
  return res.data;
};
