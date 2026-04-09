/**
 * HUNTER.OS - API Client
 * Centralized fetch wrapper for backend communication.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type HuntProgress = {
  phase?: string;
  percent?: number;
  detail?: string;
  queries_total?: number;
  queries_done?: number;
  results_found?: number;
  results_analyzed?: number;
  results_total?: number;
  leads_created?: number;
  leads_reused?: number;
  started_at?: string;
  finished_at?: string;
  error?: string;
};

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("hunter_token", token);
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("hunter_token");
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("hunter_token");
    }
  }

  private async request<T>(endpoint: string, options: RequestOptions & { rawBody?: BodyInit } = {}): Promise<T> {
    const { method = "GET", body, rawBody, headers = {} } = options;

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    let finalBody: BodyInit | undefined;
    if (rawBody) {
      finalBody = rawBody;
    } else if (body) {
      headers["Content-Type"] = "application/json";
      finalBody = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: finalBody,
    });

    if (response.status === 401) {
      this.clearToken();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Unauthorized");
    }

    if (response.status === 402) {
      const error = await response.json().catch(() => ({ detail: "Plan limit reached" }));
      // Dispatch custom event for UpgradeModal
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("hunter:plan-limit", {
          detail: { message: error.detail || "Plan limitinize ulaştınız", endpoint },
        }));
      }
      throw new Error(error.detail || "Plan limitinize ulaştınız. Yükseltme yapın.");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) return {} as T;
    return response.json();
  }

  // ── Auth ────────────────────────────────────────────
  auth = {
    login: (email: string, password: string) => {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);
      return this.request<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        rawBody: formData,
      });
    },
    register: (email: string, password: string, full_name: string) =>
      this.request("/auth/register", {
        method: "POST",
        body: { email, password, full_name },
      }),
    me: () => this.request("/auth/me"),
    updateProfile: (data: { full_name?: string; email?: string }) =>
      this.request("/auth/profile", { method: "PATCH", body: data }),
  };

  // ── Leads ───────────────────────────────────────────
  leads = {
    list: (params?: Record<string, string | number>) => {
      const query = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      return this.request(`/leads${query}`);
    },
    get: (id: number) => this.request(`/leads/${id}`),
    create: (data: Record<string, unknown>) =>
      this.request("/leads", { method: "POST", body: data }),
    update: (id: number, data: Record<string, unknown>) =>
      this.request(`/leads/${id}`, { method: "PATCH", body: data }),
    delete: (id: number) =>
      this.request(`/leads/${id}`, { method: "DELETE" }),
    committee: (id: number) => this.request(`/leads/${id}/committee`),
  };

  // ── Hunt ────────────────────────────────────────────
  hunt = {
    start: (data: Record<string, unknown>) =>
      this.request("/hunt/start", { method: "POST", body: data }),
  };

  // ── Campaigns ───────────────────────────────────────
  campaigns = {
    list: (params?: Record<string, string>) => {
      const query = params ? "?" + new URLSearchParams(params).toString() : "";
      return this.request(`/campaigns${query}`);
    },
    get: (id: number) => this.request(`/campaigns/${id}`),
    create: (data: Record<string, unknown>) =>
      this.request("/campaigns", { method: "POST", body: data }),
    update: (id: number, data: Record<string, unknown>) =>
      this.request(`/campaigns/${id}`, { method: "PATCH", body: data }),
    activate: (id: number) =>
      this.request(`/campaigns/${id}/activate`, { method: "POST" }),
    pause: (id: number) =>
      this.request(`/campaigns/${id}/pause`, { method: "POST" }),
    enqueue: (campaignId: number, leadId: number) =>
      this.request(`/campaigns/${campaignId}/enqueue/${leadId}`, { method: "POST" }),
  };

  // ── Inbox ───────────────────────────────────────────
  inbox = {
    unified: (params?: Record<string, string | number>) => {
      const query = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      return this.request(`/inbox/unified${query}`);
    },
    thread: (threadId: string) => this.request(`/inbox/thread/${threadId}`),
    markRead: (id: number) =>
      this.request(`/inbox/${id}/read`, { method: "POST" }),
    compose: (data: Record<string, unknown>) =>
      this.request("/inbox/compose", { method: "POST", body: data }),
    notifications: (unreadOnly = false) =>
      this.request(`/inbox/notifications?unread_only=${unreadOnly}`),
    bridge: (data: Record<string, unknown>) =>
      this.request("/inbox/bridge/telegram-whatsapp", { method: "POST", body: data }),
  };

  // ── Accounts ────────────────────────────────────────
  accounts = {
    health: () => this.request("/accounts/health"),
    emailList: () => this.request("/accounts/email"),
    emailAdd: (data: Record<string, unknown>) =>
      this.request("/accounts/email", { method: "POST", body: data }),
    emailPause: (id: number) =>
      this.request(`/accounts/email/${id}/pause`, { method: "POST" }),
    emailResume: (id: number) =>
      this.request(`/accounts/email/${id}/resume`, { method: "POST" }),
    linkedinList: () => this.request("/accounts/linkedin"),
    linkedinAdd: (data: Record<string, unknown>) =>
      this.request("/accounts/linkedin", { method: "POST", body: data }),
    blacklist: () => this.request("/accounts/blacklist"),
    blacklistAdd: (data: Record<string, unknown>) =>
      this.request("/accounts/blacklist", { method: "POST", body: data }),
    blacklistRemove: (id: number) =>
      this.request(`/accounts/blacklist/${id}`, { method: "DELETE" }),
  };

  // ── Products ───────────────────────────────────────
  products = {
    create: (data: { name: string; description_prompt: string }) =>
      this.request("/products", { method: "POST", body: data }),
    get: (id: number) => this.request(`/products/${id}`),
    list: () => this.request("/products"),
    update: (id: number, data: Record<string, unknown>) =>
      this.request(`/products/${id}`, { method: "PATCH", body: data }),
    analyze: (id: number) =>
      this.request(`/products/${id}/analyze`, { method: "POST" }),
    startHunting: (id: number) =>
      this.request(`/products/${id}/start-hunting`, { method: "POST" }),
    huntProgress: (id: number) =>
      this.request<{ product_id: number; status: string; progress: HuntProgress }>(`/products/${id}/hunt-progress`),
    getQuestions: (id: number) =>
      this.request<{ product_id: number; questions: Array<{ id: string; question: string; type: string; options?: string[]; placeholder?: string }> }>(`/products/${id}/questions`),
    refineIcp: (id: number, answers: Record<string, unknown>) =>
      this.request(`/products/${id}/refine-icp`, { method: "POST", body: { answers } }),
  };

  // ── Analytics ───────────────────────────────────────
  analytics = {
    dashboard: () => this.request("/analytics/dashboard"),
    campaignAutopsy: (id: number) => this.request(`/analytics/campaigns/${id}/autopsy`),
    scoringDistribution: () => this.request("/analytics/leads/scoring-distribution"),
  };

  // ── Messages ──────────────────────────────────────
  messages = {
    generate: (leadId: number, data: { channel?: string; campaign_context?: string }) =>
      this.request(`/messages/${leadId}/generate`, { method: "POST", body: data }),
    approve: (leadId: number, data: { body: string; subject_line?: string; channel?: string }) =>
      this.request(`/messages/${leadId}/approve`, { method: "POST", body: data }),
    batchGenerate: (data: { lead_ids: number[]; channel?: string; campaign_context?: string }) =>
      this.request("/messages/batch-generate", { method: "POST", body: data }),
    drafts: (leadId: number) => this.request(`/messages/${leadId}/drafts`),
  };

  // ── Footprint (Digital Dossier) ───────────────────
  footprint = {
    scan: (leadId: number, data?: { custom_usernames?: string[]; sites?: string[] }) =>
      this.request(`/footprint/scan/${leadId}`, { method: "POST", body: data || {} }),
    bulkScan: (data: { lead_ids: number[]; custom_usernames?: string[] }) =>
      this.request("/footprint/bulk-scan", { method: "POST", body: data }),
    get: (leadId: number) => this.request(`/footprint/${leadId}`),
    dossier: (leadId: number) => this.request(`/footprint/${leadId}/dossier`),
    enrich: (leadId: number) =>
      this.request(`/footprint/enrich/${leadId}`, { method: "POST" }),
    enrichBatch: (leadIds: number[]) =>
      this.request("/footprint/enrich-batch", { method: "POST", body: leadIds }),
  };

  // ── Billing ───────────────────────────────────────
  billing = {
    usage: () => this.request("/billing/usage"),
    plans: () => this.request("/billing/plans"),
    checkout: () => this.request("/billing/checkout", { method: "POST" }),
  };
}

export const api = new ApiClient();
