import React from "react";
import type { IndicatorResult } from "../types";

interface DecisionMatrixProps {
  indicators: IndicatorResult[];
  compositeScore: number;
  decision: string;
  primaryActive: boolean;
  primaryLabel: string;
  onWeightChange?: (id: string, weight: number) => void;
}

const THEME = {
  bg: "#1a1a2e",
  card: "#16213e",
  border: "#1e2a3a",
  text: "#d1d4dc",
  textMuted: "#8b8fa3",
  green: "#16c784",
  red: "#e94560",
  accent: "#0f3460",
};

function decisionColor(decision: string): string {
  const d = decision.toUpperCase();
  if (d === "BUY") return THEME.green;
  if (d === "SELL") return THEME.red;
  return THEME.textMuted;
}

function signalColor(value: number): string {
  if (value > 0.3) return THEME.green;
  if (value < -0.3) return THEME.red;
  return THEME.text;
}

function primaryStatus(
  active: boolean,
  label: string
): { icon: string; text: string; color: string } {
  if (!active) {
    return { icon: "—", text: "No active primary signal", color: THEME.textMuted };
  }
  const lower = label.toLowerCase();
  if (lower.includes("low") || lower.includes("buy")) {
    return {
      icon: "▼",
      text: `${label}`,
      color: THEME.green,
    };
  }
  if (lower.includes("high") || lower.includes("sell")) {
    return {
      icon: "▲",
      text: `${label}`,
      color: THEME.red,
    };
  }
  return { icon: "—", text: label, color: THEME.textMuted };
}

const cellStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: `1px solid ${THEME.border}`,
  fontSize: 13,
  verticalAlign: "middle",
};

const DecisionMatrix: React.FC<DecisionMatrixProps> = ({
  indicators,
  compositeScore,
  decision,
  primaryActive,
  primaryLabel,
  onWeightChange,
}) => {
  const primary = primaryStatus(primaryActive, primaryLabel);

  return (
    <div
      style={{
        background: THEME.card,
        borderRadius: 8,
        border: `1px solid ${THEME.border}`,
        overflow: "hidden",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Primary signal status bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 16px",
          background: "rgba(0,0,0,0.25)",
          borderBottom: `1px solid ${THEME.border}`,
          fontSize: 13,
          fontWeight: 600,
          color: primary.color,
        }}
      >
        <span style={{ fontSize: 16 }}>{primary.icon}</span>
        <span>{primary.text}</span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 10,
            color: THEME.textMuted,
            fontWeight: 400,
          }}
        >
          PRIMARY SIGNAL
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            color: THEME.text,
          }}
        >
          <thead>
            <tr
              style={{
                background: "rgba(0,0,0,0.15)",
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: THEME.textMuted,
              }}
            >
              <th style={{ ...cellStyle, textAlign: "left", fontWeight: 600 }}>
                Indicator
              </th>
              <th style={{ ...cellStyle, textAlign: "center", fontWeight: 600, minWidth: 120 }}>
                Weight
              </th>
              <th style={{ ...cellStyle, textAlign: "center", fontWeight: 600 }}>
                Signal
              </th>
              <th style={{ ...cellStyle, textAlign: "center", fontWeight: 600 }}>
                Label
              </th>
              <th style={{ ...cellStyle, textAlign: "right", fontWeight: 600 }}>
                Weighted
              </th>
            </tr>
          </thead>
          <tbody>
            {indicators.map((ind) => (
              <tr
                key={ind.id}
                style={{
                  transition: "background 0.15s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "rgba(255,255,255,0.03)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <td style={{ ...cellStyle, textAlign: "left", fontWeight: 500 }}>
                  {ind.id}
                  {ind.id === "sentiment" && (
                    <span
                      style={{
                        marginLeft: 6,
                        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                        color: "#fff",
                        fontSize: 9,
                        fontWeight: 700,
                        padding: "1px 4px",
                        borderRadius: 3,
                        letterSpacing: "0.05em",
                        verticalAlign: "middle",
                      }}
                    >
                      AI
                    </span>
                  )}
                </td>
                <td style={{ ...cellStyle, textAlign: "center" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                    }}
                  >
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={ind.weight}
                      onChange={(e) =>
                        onWeightChange?.(ind.id, parseFloat(e.target.value))
                      }
                      style={{
                        width: 70,
                        accentColor: THEME.accent,
                        cursor: "pointer",
                      }}
                    />
                    <span
                      style={{
                        fontSize: 11,
                        color: THEME.textMuted,
                        minWidth: 28,
                        textAlign: "right",
                      }}
                    >
                      {ind.weight.toFixed(2)}
                    </span>
                  </div>
                </td>
                <td
                  style={{
                    ...cellStyle,
                    textAlign: "center",
                    fontFamily: "'JetBrains Mono', monospace",
                    color: signalColor(ind.signal),
                    fontWeight: 600,
                  }}
                >
                  {ind.signal > 0 ? "+" : ""}
                  {ind.signal.toFixed(2)}
                </td>
                <td style={{ ...cellStyle, textAlign: "center", fontSize: 12 }}>
                  {ind.label}
                </td>
                <td
                  style={{
                    ...cellStyle,
                    textAlign: "right",
                    fontFamily: "'JetBrains Mono', monospace",
                    color: signalColor(ind.weighted_score),
                    fontWeight: 600,
                  }}
                >
                  {ind.weighted_score > 0 ? "+" : ""}
                  {ind.weighted_score.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr
              style={{
                background: "rgba(0,0,0,0.2)",
                fontWeight: 700,
              }}
            >
              <td style={{ ...cellStyle, textAlign: "left" }}>TOTAL</td>
              <td style={cellStyle} />
              <td
                style={{
                  ...cellStyle,
                  textAlign: "center",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 15,
                  color: signalColor(compositeScore),
                }}
              >
                {compositeScore > 0 ? "+" : ""}
                {compositeScore.toFixed(3)}
              </td>
              <td
                colSpan={2}
                style={{
                  ...cellStyle,
                  textAlign: "right",
                  paddingRight: 16,
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    padding: "4px 16px",
                    borderRadius: 20,
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    color: "#fff",
                    background: decisionColor(decision),
                  }}
                >
                  {decision.toUpperCase()}
                </span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
};

export default DecisionMatrix;
