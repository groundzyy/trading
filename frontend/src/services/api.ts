import axios from "axios";
import type {
  Candle,
  SwingPoint,
  DecisionResult,
  WatchlistItem,
  ScannerResult,
  User,
  IndicatorMethod,
} from "@/types";

const api = axios.create({
  baseURL: "/api",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// Auth
export async function login(
  username: string,
  password: string
): Promise<{ access_token: string }> {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const res = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
}

export async function register(
  email: string,
  username: string,
  password: string
): Promise<User> {
  const res = await api.post("/auth/register", { email, username, password });
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await api.get("/auth/me");
  return res.data;
}

// Stocks
export async function validateSymbol(
  symbol: string
): Promise<{ symbol: string; valid: boolean }> {
  const res = await api.get(`/stocks/${symbol}/validate`);
  return res.data;
}

export async function getOHLCV(
  symbol: string,
  range: string = "1Y"
): Promise<{ symbol: string; range: string; candles: Candle[] }> {
  const res = await api.get(`/stocks/${symbol}/ohlcv`, { params: { range } });
  return res.data;
}

export async function getStockInfo(
  symbol: string
): Promise<{ symbol: string; name: string; exchange: string; sector: string }> {
  const res = await api.get(`/stocks/${symbol}/info`);
  return res.data;
}

// Signals
export async function getSwingPoints(
  symbol: string,
  range: string = "1Y"
): Promise<{
  symbol: string;
  swing_points: SwingPoint[];
  signal: { value: number; label: string; details?: Record<string, unknown> } | null;
}> {
  const res = await api.get(`/signals/${symbol}/swing`, { params: { range } });
  return res.data;
}

export async function getIndicator(
  symbol: string,
  indicatorId: string,
  range: string = "1Y"
): Promise<{
  symbol: string;
  indicator_id: string;
  data: unknown[];
  signal: { value: number; label: string; details?: Record<string, unknown> } | null;
}> {
  const res = await api.get(`/signals/${symbol}/indicator/${indicatorId}`, {
    params: { range },
  });
  return res.data;
}

export async function getMethods(): Promise<{ methods: IndicatorMethod[] }> {
  const res = await api.get("/signals/methods");
  return res.data;
}

// Decision
export async function getDecision(
  symbol: string,
  methods: { id: string; weight: number; params?: Record<string, unknown> | null }[],
  range: string = "1Y"
): Promise<DecisionResult> {
  const res = await api.post(`/decision/${symbol}`, { methods, range });
  return res.data;
}

// Watchlist
export async function getWatchlist(): Promise<{ items: WatchlistItem[] }> {
  const res = await api.get("/watchlist");
  return res.data;
}

export async function addToWatchlist(
  symbol: string
): Promise<{ id: number; symbol: string; message: string }> {
  const res = await api.post("/watchlist", { symbol });
  return res.data;
}

export async function removeFromWatchlist(id: number): Promise<void> {
  await api.delete(`/watchlist/${id}`);
}

export async function updateWatchlistItem(
  id: number,
  data: {
    selected_methods?: string[];
    method_weights?: Record<string, number>;
    notify_enabled?: boolean;
  }
): Promise<void> {
  await api.put(`/watchlist/${id}`, data);
}

// Scanner
export async function scanSignals(
  signalType?: string,
  days: number = 3
): Promise<{ signals: ScannerResult[] }> {
  const params: Record<string, string | number> = { days };
  if (signalType) params.signal_type = signalType;
  const res = await api.get("/scanner", { params });
  return res.data;
}

export default api;
