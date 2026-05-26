export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SwingPoint {
  date: string;
  level: "STH" | "STL" | "MTH" | "MTL" | "LTH" | "LTL" | "BUY" | "SELL";
  price: number;
}

export interface IndicatorMethod {
  id: string;
  name: string;
  category: string;
  chart_position: string;
  default_params: Record<string, any>;
}

export interface IndicatorSignal {
  value: number;
  label: string;
  details?: Record<string, any>;
}

export interface IndicatorResult {
  id: string;
  signal: number;
  label: string;
  weight: number;
  weighted_score: number;
  details?: any;
}

export interface DecisionResult {
  symbol: string;
  primary: {
    active: boolean;
    signal: number;
    label: string;
    details?: any;
  };
  indicators: IndicatorResult[];
  composite_score: number;
  decision: string;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  selected_methods: string[];
  method_weights: Record<string, number>;
  notify_enabled: boolean;
  added_at: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
}

export interface ScannerResult {
  symbol: string;
  date: string;
  signal_type: string;
  composite_score: number;
  trigger_price: number;
}
