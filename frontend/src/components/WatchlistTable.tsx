import React from "react";

interface WatchlistItem {
  symbol: string;
  decision?: string;
  score?: number;
  price?: number;
  change?: number;
}

interface WatchlistTableProps {
  items: WatchlistItem[];
  onRemove: (id: number) => void;
  onSelect: (symbol: string) => void;
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
  rowHover: "rgba(255,255,255,0.04)",
};

function decisionBadge(
  decision: string | undefined
): { bg: string; label: string } {
  if (!decision) return { bg: THEME.textMuted, label: "--" };
  const d = decision.toUpperCase();
  if (d === "BUY") return { bg: THEME.green, label: "BUY" };
  if (d === "SELL") return { bg: THEME.red, label: "SELL" };
  return { bg: THEME.textMuted, label: d };
}

function changeColor(change: number | undefined): string {
  if (change === undefined || change === null) return THEME.text;
  if (change > 0) return THEME.green;
  if (change < 0) return THEME.red;
  return THEME.text;
}

function formatChange(change: number | undefined): string {
  if (change === undefined || change === null) return "--";
  const sign = change > 0 ? "+" : "";
  return `${sign}${change.toFixed(2)}%`;
}

function scoreBar(score: number | undefined): React.ReactNode {
  if (score === undefined || score === null) return "--";
  // Normalize score to 0-100 range for visual; assume score is -1 to 1
  const pct = Math.min(100, Math.max(0, (score + 1) * 50));
  const barColor = score > 0 ? THEME.green : score < 0 ? THEME.red : THEME.textMuted;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          width: 50,
          height: 4,
          background: "rgba(255,255,255,0.08)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: barColor,
            borderRadius: 2,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          color: barColor,
        }}
      >
        {score > 0 ? "+" : ""}
        {score.toFixed(2)}
      </span>
    </div>
  );
}

const cellStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: `1px solid ${THEME.border}`,
  fontSize: 13,
  verticalAlign: "middle",
  whiteSpace: "nowrap",
};

const WatchlistTable: React.FC<WatchlistTableProps> = ({
  items,
  onRemove,
  onSelect,
}) => {
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
                background: "rgba(0,0,0,0.2)",
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: THEME.textMuted,
              }}
            >
              <th style={{ ...cellStyle, textAlign: "left", fontWeight: 600 }}>
                Symbol
              </th>
              <th style={{ ...cellStyle, textAlign: "right", fontWeight: 600 }}>
                Price
              </th>
              <th style={{ ...cellStyle, textAlign: "right", fontWeight: 600 }}>
                Change %
              </th>
              <th style={{ ...cellStyle, textAlign: "left", fontWeight: 600 }}>
                Score
              </th>
              <th style={{ ...cellStyle, textAlign: "center", fontWeight: 600 }}>
                Decision
              </th>
              <th style={{ ...cellStyle, textAlign: "center", fontWeight: 600, width: 60 }}>
                {/* Remove column */}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  style={{
                    ...cellStyle,
                    textAlign: "center",
                    color: THEME.textMuted,
                    padding: "24px 12px",
                  }}
                >
                  No items in watchlist
                </td>
              </tr>
            )}
            {items.map((item, index) => {
              const badge = decisionBadge(item.decision);
              return (
                <tr
                  key={`${item.symbol}-${index}`}
                  onClick={() => onSelect(item.symbol)}
                  style={{
                    cursor: "pointer",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = THEME.rowHover)
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <td
                    style={{
                      ...cellStyle,
                      textAlign: "left",
                      fontWeight: 600,
                      color: "#fff",
                      letterSpacing: "0.02em",
                    }}
                  >
                    {item.symbol}
                  </td>
                  <td
                    style={{
                      ...cellStyle,
                      textAlign: "right",
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {item.price !== undefined && item.price !== null
                      ? item.price.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })
                      : "--"}
                  </td>
                  <td
                    style={{
                      ...cellStyle,
                      textAlign: "right",
                      fontFamily: "'JetBrains Mono', monospace",
                      color: changeColor(item.change),
                      fontWeight: 600,
                    }}
                  >
                    {formatChange(item.change)}
                  </td>
                  <td style={{ ...cellStyle, textAlign: "left" }}>
                    {scoreBar(item.score)}
                  </td>
                  <td style={{ ...cellStyle, textAlign: "center" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "3px 12px",
                        borderRadius: 16,
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        color: "#fff",
                        background: badge.bg,
                      }}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td style={{ ...cellStyle, textAlign: "center" }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemove(index);
                      }}
                      style={{
                        background: "transparent",
                        border: `1px solid ${THEME.border}`,
                        borderRadius: 4,
                        color: THEME.textMuted,
                        cursor: "pointer",
                        padding: "4px 8px",
                        fontSize: 12,
                        lineHeight: 1,
                        transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = THEME.red;
                        e.currentTarget.style.color = THEME.red;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = THEME.border;
                        e.currentTarget.style.color = THEME.textMuted;
                      }}
                      title="Remove from watchlist"
                    >
                      {"✕"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default WatchlistTable;
