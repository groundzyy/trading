import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { ScannerResult } from "@/types";
import { scanSignals } from "@/services/api";

const SIGNAL_TYPES = ["All", "BUY", "SELL"] as const;
const DAY_OPTIONS = [1, 3, 7] as const;

export default function Scanner() {
  const navigate = useNavigate();
  const [signalType, setSignalType] = useState<string>("All");
  const [days, setDays] = useState<number>(3);
  const [results, setResults] = useState<ScannerResult[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const type = signalType === "All" ? undefined : signalType;
      const res = await scanSignals(type, days);
      setResults(res.signals);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [signalType, days]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  const getSignalColor = (signal: string) => {
    if (signal === "BUY") return "#16c784";
    if (signal === "SELL") return "#e94560";
    return "#8a8a9a";
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.5) return "#16c784";
    if (score <= -0.5) return "#e94560";
    return "#f0b90b";
  };

  return (
    <div style={pageStyle}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Market Scanner</h1>

      {/* Filter Bar */}
      <div style={filterBarStyle}>
        <div style={filterGroupStyle}>
          <span style={filterLabelStyle}>Signal Type</span>
          <div style={{ display: "flex", gap: 4 }}>
            {SIGNAL_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => setSignalType(t)}
                style={{
                  ...filterBtnStyle,
                  background: signalType === t ? "#0f3460" : "transparent",
                  color: signalType === t ? "#fff" : "#8a8a9a",
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div style={filterGroupStyle}>
          <span style={filterLabelStyle}>Lookback Days</span>
          <div style={{ display: "flex", gap: 4 }}>
            {DAY_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                style={{
                  ...filterBtnStyle,
                  background: days === d ? "#0f3460" : "transparent",
                  color: days === d ? "#fff" : "#8a8a9a",
                }}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        <button onClick={fetchResults} style={refreshBtnStyle}>
          Refresh
        </button>
      </div>

      {/* Results */}
      {loading ? (
        <div style={{ color: "#8a8a9a", textAlign: "center", padding: 60 }}>
          Scanning signals...
        </div>
      ) : results.length === 0 ? (
        <div style={emptyStyle}>
          <p style={{ fontSize: 16 }}>No signals found</p>
          <p style={{ color: "#8a8a9a", fontSize: 14, marginTop: 8 }}>
            Try adjusting the filters or increasing the lookback period
          </p>
        </div>
      ) : (
        <div style={tableContainerStyle}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid #0f3460" }}>
            <span style={{ color: "#8a8a9a", fontSize: 13 }}>
              {results.length} signal{results.length !== 1 ? "s" : ""} found
            </span>
          </div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Symbol</th>
                <th style={thStyle}>Signal</th>
                <th style={thStyle}>Date</th>
                <th style={thStyle}>Score</th>
                <th style={thStyle}>Price</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr
                  key={`${r.symbol}-${r.date}-${i}`}
                  onClick={() => navigate(`/stock/${r.symbol}`)}
                  style={rowStyle}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = "rgba(15, 52, 96, 0.3)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = "transparent";
                  }}
                >
                  <td style={tdStyle}>
                    <span style={{ fontWeight: 600, fontSize: 15 }}>{r.symbol}</span>
                  </td>
                  <td style={tdStyle}>
                    <span
                      style={{
                        background: getSignalColor(r.signal_type),
                        color: "#fff",
                        padding: "3px 10px",
                        borderRadius: 4,
                        fontSize: 13,
                        fontWeight: 600,
                      }}
                    >
                      {r.signal_type}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, color: "#8a8a9a" }}>{r.date}</td>
                  <td style={tdStyle}>
                    <span
                      style={{
                        color: getScoreColor(r.composite_score),
                        fontWeight: 600,
                      }}
                    >
                      {r.composite_score.toFixed(2)}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    ${r.trigger_price.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------- Styles ----------
const pageStyle: React.CSSProperties = {
  maxWidth: 1000,
  margin: "0 auto",
  padding: "24px 20px",
};

const filterBarStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "flex-end",
  gap: 24,
  marginBottom: 20,
  padding: "16px 20px",
  background: "#16213e",
  borderRadius: 8,
  border: "1px solid #0f3460",
  flexWrap: "wrap",
};

const filterGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
};

const filterLabelStyle: React.CSSProperties = {
  color: "#8a8a9a",
  fontSize: 12,
  fontWeight: 500,
  textTransform: "uppercase",
  letterSpacing: 0.5,
};

const filterBtnStyle: React.CSSProperties = {
  padding: "6px 14px",
  border: "1px solid #0f3460",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};

const refreshBtnStyle: React.CSSProperties = {
  padding: "8px 20px",
  background: "#0f3460",
  border: "none",
  borderRadius: 4,
  color: "#e0e0e0",
  cursor: "pointer",
  fontWeight: 600,
  marginLeft: "auto",
};

const tableContainerStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 8,
  border: "1px solid #0f3460",
  overflow: "hidden",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "12px 16px",
  color: "#8a8a9a",
  fontSize: 13,
  fontWeight: 500,
  borderBottom: "1px solid #0f3460",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid rgba(15, 52, 96, 0.5)",
  fontSize: 14,
};

const rowStyle: React.CSSProperties = {
  cursor: "pointer",
  transition: "background 0.15s",
};

const emptyStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "60px 20px",
  background: "#16213e",
  borderRadius: 8,
  border: "1px solid #0f3460",
};
