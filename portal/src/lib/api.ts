import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("dh_portal_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("dh_portal_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export type PortalLoginResponse = { access_token: string; token_type: string };

export async function portalLogin(email: string, password: string): Promise<PortalLoginResponse> {
  const r = await api.post<PortalLoginResponse>("/api/portal/auth/login", { email, password });
  if (typeof window !== "undefined") localStorage.setItem("dh_portal_token", r.data.access_token);
  return r.data;
}

export async function getProfile() {
  return (await api.get("/api/portal/my/profile")).data;
}

export async function getUsage() {
  return (await api.get("/api/portal/my/usage")).data;
}

export async function getInvoices() {
  return (await api.get("/api/portal/my/invoices")).data;
}

export async function getTickets() {
  return (await api.get("/api/portal/my/tickets")).data;
}

export async function createTicket(data: {
  category: string; title: string; description: string; priority?: string;
}) {
  return (await api.post("/api/portal/my/tickets", data)).data;
}

export async function getAreaOutage() {
  return (await api.get("/api/portal/area/outage")).data;
}
