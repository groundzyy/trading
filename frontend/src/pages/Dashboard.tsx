import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { WatchlistItem, DecisionResult } from "@/types";
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  getDecision,
  validateSymbol,
} from "@/services/api";

// Default methods to use if a watchlist item has none configured
const DEFAULT_METHODS = [
  { id: "swing_structure", weight: 0.4 },
  { id: "macd", weight: 0.2 },
  { id: "kdj", weight: 0.2 },
  { id: "rsi", weight: 0.2 },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [decisions, setDecisions] = useState<Record<string, DecisionResult>>({});
  const [loading, setLoading] = useState(true);
  const [addSymbol, setAddSymbol] = useState("");
  const [addError, setAddError] = useState("");
  const [addingSymbol, setAddingSymbol] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    try {
      const { items } = await getWatchlist();
      setWatchlist(items);
      return items;
    } catch {
      // handled by interceptor
      return [];
    }
  }, []);

  const fetchDecisions = useCallback(async (items: WatchlistItem[]) => {
    const results: Record<string, DecisionResult> = {};
    await Promise.allSettled(
      items.map(async (item) => {
        try {
          const methods =
            item.selected_methods && item.selected_methods.length > 0
              ? item.selected_methods.map((id) => ({
                  id,
                  weight: item.method_weights?.[id] ?? 0.25,
                }))
              : DEFAULT_METHODS;
          const decision = await getDecision(item.symbol, methods);
          results[item.symbol] = decision;
        } catch {
          // skip failed
        }
      })
    );
    setDecisions(results);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const items = await fetchWatchlist();
      if (!cancelled && items.length > 0) {
        await fetchDecisions(items);
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchWatchlist, fetchDecisions]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const sym = addSymbol.trim().toUpperCase();
    if (!sym) return;
    setAddError("");
    setAddingSymbol(true);
    try {
      await validateSymbol(sym);
      await addToWatchlist(sym);
      setAddSymbol("");
      const items = await fetchWatchlist();
      await fetchDecisions(items);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axErr.response?.status === 404) {
          setAddError(`Symbol "${sym}" not found`);
        } else {
          setAddError(axErr.response?.data?.detail || "Failed to add");
        }
      } else {
        setAddError("Failed to add");
      }
    } finally {
      setAddingSymbol(false);
    }
  };

  const handleRemove = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await removeFromWatchlist(id);
      const items = await fetchWatchlist();
      await fetchDecisions(items);
    } catch {
      // ignore
    }
  };

  // Signal summary counts
  const summary = { BUY: 0, SELL: 0, HOLD: 0 };
  Object.values(decisions).forEach((d) => {
    if (d.decision === "BUY") summary.BUY++;
    else if (d.decision === "SELL") summary.SELL++;
    else summary.HOLD++;
  });

  const getDecisionColor = (decision: string) => {
    if (decision === "BUY") return "#16c784";
    if (decision === "SELL") return "#e94560";
    return "#8a8a9a";
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.5) return "#16c784";
    if (score <= -0.5) return "#e94560";
    return "#f0b90b";
  };

  return (
    <div style={pageStyle}>
      {/* Signal Summary */}
      <div style={summaryBarStyle}>
        <div style={summaryCardStyle}>
          <span style={{ color: "#8a8a9a", fontSize: 13 }}>Signal Summary</span>
          <div style={{ display: "flex", gap: 24, marginTop: 8 }}>
            <div>
              <span style={{ color: "#16c784", fontSize: 24, fontWeight: 700 }}>{summary.BUY}</span>
              <span style={{ color: "#16c784", fontSize: 13, marginLeft: 6 }}>BUY</span>
            </div>
            <div>
              <span style={{ color: "#e94560", fontSize: 24, fontWeight: 700 }}>{summary.SELL}</span>
              <span style={{ color: "#e94560", fontSize: 13, marginLeft: 6 }}>SELL</span>
            </div>
            <div>
              <span style={{ color: "#8a8a9a", fontSize: 24, fontWeight: 700 }}>{summary.HOLD}</span>
              <span style={{ color: "#8a8a9a", fontSize: 13, marginLeft: 6 }}>HOLD</span>
            </div>
          </div>
        </div>
      </div>

      {/* Add Stock */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, flex: 1 }}>Watchlist</h2>
        <form onSubmit={handleAdd} style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={addSymbol}
            onChange={(e) => setAddSymbol(e.target.value)}
            placeholder="Add symbol..."
            style={addInputStyle}
          />
          <button type="submit" disabled={addingSymbol} style={addBtnStyle}>
            {addingSymbol ? "..." : "+ Add"}
          </button>
        </form>
      </div>
      {addError && (
        <div style={{ color: "#e94560", fontSize: 13, marginBottom: 12 }}>{addError}</div>
      )}

      {/* Watchlist Table */}
      {loading ? (
        <div style={{ color: "#8a8a9a", textAlign: "center", padding: 40 }}>
          Loading watchlist...
        </div>
      ) : watchlist.length === 0 ? (
        <div style={emptyStyle}>
          <p style={{ fontSize: 16, marginBottom: 8 }}>Your watchlist is empty</p>
          <p style={{ color: "#8a8a9a", fontSize: 14 }}>Add a stock symbol above to get started</p>
        </div>
      ) : (
        <div style={tableContainerStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Symbol</th>
                <th style={thStyle}>Price</th>
                <th style={thStyle}>Signal</th>
                <th style={thStyle}>Score</th>
                <th style={thStyle}>Decision</th>
                <th style={{ ...thStyle, width: 60 }}></th>
              </tr>
            </thead>
            <tbody>
              {watchlist.map((item) => {
                const d = decisions[item.symbol];
                const lastPrice = d?.primary?.details?.current_price as number | undefined;
                const signal = d?.primary?.label ?? "--";
                const score = d?.composite_score;
                const decision = d?.decision ?? "--";

                return (
                  <tr
                    key={item.id}
                    onClick={() => navigate(`/stock/${item.symbol}`)}
                    style={rowStyle}
                  >
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 600, fontSize: 15 }}>{item.symbol}</span>
                    </td>
                    <td style={tdStyle}>
                      {lastPrice != null ? `$${lastPrice.toFixed(2)}` : "--"}
                    </td>
                    <td style={tdStyle}>
                      <span style={{ color: getDecisionColor(signal) }}>{signal}</span>
                    </td>
                    <td style={tdStyle}>
                      {score != null ? (
                        <span style={{ color: getScoreColor(score), fontWeight: 600 }}>
                          {score.toFixed(2)}
                        </span>
                      ) : (
                        "--"
                      )}
                    </td>
                    <td style={tdStyle}>
                      <span
                        style={{
                          background: getDecisionColor(decision),
                          color: "#fff",
                          padding: "3px 10px",
                          borderRadius: 4,
                          fontSize: 13,
                          fontWeight: 600,
                        }}
                      >
                        {decision}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <button
                        onClick={(e) => handleRemove(item.id, e)}
                        style={removeBtnStyle}
                        title="Remove from watchlist"
                      >
                        x
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: 1000,
  margin: "0 auto",
  padding: "24px 20px",
};

const summaryBarStyle: React.CSSProperties = {
  marginBottom: 24,
};

const summaryCardStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 8,
  padding: "16px 24px",
  border: "1px solid #0f3460",
};

const addInputStyle: React.CSSProperties = {
  padding: "8px 12px",
  background: "#16213e",
  border: "1px solid #0f3460",
  borderRadius: 4,
  color: "#e0e0e0",
  width: 140,
  outline: "none",
};

const addBtnStyle: React.CSSProperties = {
  padding: "8px 16px",
  background: "#0f3460",
  border: "none",
  borderRadius: 4,
  color: "#e0e0e0",
  cursor: "pointer",
  fontWeight: 600,
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
  background: "#16213e",
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

const removeBtnStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #e94560",
  borderRadius: 4,
  color: "#e94560",
  cursor: "pointer",
  padding: "2px 8px",
  fontSize: 13,
};

const emptyStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "60px 20px",
  background: "#16213e",
  borderRadius: 8,
  border: "1px solid #0f3460",
};
