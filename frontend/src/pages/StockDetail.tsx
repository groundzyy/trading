import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import type { Candle, SwingPoint, DecisionResult, IndicatorMethod } from "@/types";
import CandlestickChart from "@/components/CandlestickChart";
import IndicatorPanel from "@/components/IndicatorPanel";
import DecisionMatrix from "@/components/DecisionMatrix";
import {
  getOHLCV,
  getSwingPoints,
  getDecision,
  getStockInfo,
  getIndicator,
  getMethods,
} from "@/services/api";

const RANGES = ["1M", "3M", "6M", "1Y", "5Y"] as const;

// Map indicator IDs to their chart line configurations
const INDICATOR_LINES: Record<
  string,
  { key: string; color: string; label: string }[]
> = {
  macd: [
    { key: "macd_dif", color: "#2196f3", label: "DIF" },
    { key: "macd_dea", color: "#e94560", label: "DEA" },
    { key: "macd_hist", color: "#8a8a9a", label: "Hist" },
  ],
  kdj: [
    { key: "kdj_k", color: "#2196f3", label: "K" },
    { key: "kdj_d", color: "#e94560", label: "D" },
    { key: "kdj_j", color: "#f0b90b", label: "J" },
  ],
  rsi: [{ key: "rsi", color: "#9c27b0", label: "RSI" }],
};

interface IndicatorDataRow {
  date: string;
  [key: string]: unknown;
}

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const upperSymbol = (symbol ?? "").toUpperCase();

  const [range, setRange] = useState<string>("1Y");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [swingPoints, setSwingPoints] = useState<SwingPoint[]>([]);
  const [swingSignal, setSwingSignal] = useState<{
    value: number;
    label: string;
  } | null>(null);
  const [decision, setDecision] = useState<DecisionResult | null>(null);
  const [stockInfo, setStockInfo] = useState<{
    name: string;
    exchange: string;
    sector: string;
  } | null>(null);
  const [_methods, setMethods] = useState<IndicatorMethod[]>([]);
  const [indicatorData, setIndicatorData] = useState<
    Record<string, IndicatorDataRow[]>
  >({});
  const [loading, setLoading] = useState(true);

  // Fetch available methods once
  useEffect(() => {
    getMethods()
      .then((res) => setMethods(res.methods))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    if (!upperSymbol) return;
    setLoading(true);
    try {
      const [ohlcvRes, swingRes, infoRes] = await Promise.allSettled([
        getOHLCV(upperSymbol, range),
        getSwingPoints(upperSymbol, range),
        getStockInfo(upperSymbol),
      ]);

      if (ohlcvRes.status === "fulfilled") {
        setCandles(ohlcvRes.value.candles);
      }
      if (swingRes.status === "fulfilled") {
        setSwingPoints(swingRes.value.swing_points);
        setSwingSignal(swingRes.value.signal);
      }
      if (infoRes.status === "fulfilled") {
        setStockInfo(infoRes.value);
      }

      // Fetch decision with default methods
      try {
        const defaultMethods = [
          { id: "swing_structure", weight: 0.4 },
          { id: "macd", weight: 0.2 },
          { id: "kdj", weight: 0.2 },
          { id: "rsi", weight: 0.2 },
        ];
        const dec = await getDecision(upperSymbol, defaultMethods, range);
        setDecision(dec);
      } catch {
        setDecision(null);
      }

      // Fetch indicator chart data for sub-panels
      const indicatorIds = ["macd", "kdj", "rsi"];
      const indResults: Record<string, IndicatorDataRow[]> = {};
      await Promise.allSettled(
        indicatorIds.map(async (id) => {
          try {
            const res = await getIndicator(upperSymbol, id, range);
            if (res.data && Array.isArray(res.data)) {
              indResults[id] = res.data as IndicatorDataRow[];
            }
          } catch {
            // skip failed indicators
          }
        })
      );
      setIndicatorData(indResults);
    } finally {
      setLoading(false);
    }
  }, [upperSymbol, range]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Latest price info
  const lastCandle = candles.length > 0 ? candles[candles.length - 1] : null;
  const prevCandle = candles.length > 1 ? candles[candles.length - 2] : null;
  const price = lastCandle?.close ?? 0;
  const change =
    lastCandle && prevCandle ? lastCandle.close - prevCandle.close : 0;
  const changePct = prevCandle ? (change / prevCandle.close) * 100 : 0;
  const isPositive = change >= 0;

  const getDecisionColor = (d: string) => {
    if (d === "BUY") return "#16c784";
    if (d === "SELL") return "#e94560";
    return "#8a8a9a";
  };

  return (
    <div style={pageStyle}>
      {/* Stock Header */}
      <div style={headerStyle}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>
            {upperSymbol}
          </h1>
          {stockInfo && (
            <span style={{ color: "#8a8a9a", fontSize: 14 }}>
              {stockInfo.name}{" "}
              {stockInfo.exchange ? `- ${stockInfo.exchange}` : ""}
              {stockInfo.sector ? ` | ${stockInfo.sector}` : ""}
            </span>
          )}
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>
            ${price.toFixed(2)}
          </div>
          <div
            style={{
              color: isPositive ? "#16c784" : "#e94560",
              fontSize: 16,
              fontWeight: 600,
            }}
          >
            {isPositive ? "+" : ""}
            {change.toFixed(2)} ({isPositive ? "+" : ""}
            {changePct.toFixed(2)}%)
          </div>
        </div>
      </div>

      {/* Range Selector */}
      <div style={rangeSelectorStyle}>
        {RANGES.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            style={{
              ...rangeBtnStyle,
              background: range === r ? "#0f3460" : "transparent",
              color: range === r ? "#fff" : "#8a8a9a",
            }}
          >
            {r}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ color: "#8a8a9a", textAlign: "center", padding: 60 }}>
          Loading data for {upperSymbol}...
        </div>
      ) : (
        <>
          {/* Candlestick Chart (lightweight-charts) */}
          <div style={chartContainerStyle}>
            {candles.length > 0 ? (
              <CandlestickChart candles={candles} swingPoints={swingPoints} />
            ) : (
              <div
                style={{
                  color: "#8a8a9a",
                  textAlign: "center",
                  padding: 40,
                }}
              >
                No chart data available
              </div>
            )}
          </div>

          {/* Indicator Sub-Panels (MACD, KDJ, RSI) */}
          <div style={{ marginBottom: 16 }}>
            {(["macd", "kdj", "rsi"] as const).map((id) => {
              const data = indicatorData[id];
              const lines = INDICATOR_LINES[id];
              if (!data || !lines || data.length === 0) return null;
              return (
                <IndicatorPanel
                  key={id}
                  title={id.toUpperCase()}
                  data={data}
                  lines={lines}
                />
              );
            })}
          </div>

          {/* Swing Signal */}
          {swingSignal && (
            <div style={signalBarStyle}>
              <span style={{ color: "#8a8a9a", fontSize: 13 }}>
                Primary Signal (Swing Structure):
              </span>
              <span
                style={{
                  color: getDecisionColor(swingSignal.label),
                  fontWeight: 700,
                  fontSize: 15,
                  marginLeft: 12,
                }}
              >
                {swingSignal.label} ({swingSignal.value > 0 ? "+" : ""}
                {swingSignal.value.toFixed(2)})
              </span>
            </div>
          )}

          {/* Decision Matrix */}
          {decision && (
            <div style={{ marginBottom: 16 }}>
              <h3
                style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}
              >
                Decision Matrix
              </h3>
              <DecisionMatrix
                indicators={decision.indicators}
                compositeScore={decision.composite_score}
                decision={decision.decision}
                primaryActive={decision.primary.active}
                primaryLabel={decision.primary.label}
              />
            </div>
          )}

          {/* Swing Points List */}
          {swingPoints.length > 0 && (
            <div style={swingListStyle}>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
                Recent Swing Points
              </h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {swingPoints
                  .slice(-20)
                  .reverse()
                  .map((sp, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 4,
                        fontSize: 13,
                        background:
                          sp.level.includes("H") || sp.level === "SELL"
                            ? "rgba(233, 69, 96, 0.15)"
                            : "rgba(22, 199, 132, 0.15)",
                        color:
                          sp.level.includes("H") || sp.level === "SELL"
                            ? "#e94560"
                            : "#16c784",
                        border: `1px solid ${
                          sp.level.includes("H") || sp.level === "SELL"
                            ? "rgba(233, 69, 96, 0.3)"
                            : "rgba(22, 199, 132, 0.3)"
                        }`,
                      }}
                    >
                      {sp.level} ${sp.price.toFixed(2)} ({sp.date})
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------- Styles ----------
const pageStyle: React.CSSProperties = {
  maxWidth: 1100,
  margin: "0 auto",
  padding: "24px 20px",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: 20,
  padding: "20px 24px",
  background: "#16213e",
  borderRadius: 8,
  border: "1px solid #0f3460",
};

const rangeSelectorStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
  marginBottom: 16,
};

const rangeBtnStyle: React.CSSProperties = {
  padding: "6px 16px",
  border: "1px solid #0f3460",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
};

const chartContainerStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 8,
  padding: "16px 20px",
  border: "1px solid #0f3460",
  marginBottom: 16,
  minHeight: 420,
};

const signalBarStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 8,
  padding: "12px 20px",
  border: "1px solid #0f3460",
  marginBottom: 16,
  display: "flex",
  alignItems: "center",
};

const swingListStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 8,
  padding: "16px 20px",
  border: "1px solid #0f3460",
};
