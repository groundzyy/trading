import React, { useState } from "react";
import type { SentimentAnalysis } from "@/types";

interface SentimentPanelProps {
  symbol: string;
  sentiment: SentimentAnalysis | null;
  loading: boolean;
  onAnalyze: () => void;
}

function scoreColor(score: number): string {
  if (score > 0.3) return "#16c784";
  if (score < -0.3) return "#e94560";
  return "#f0b90b";
}

function labelColor(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("bullish")) return "#16c784";
  if (l.includes("bearish")) return "#e94560";
  return "#8a8a9a";
}

function confidenceLabel(c: number): string {
  if (c >= 0.8) return "High";
  if (c >= 0.5) return "Medium";
  return "Low";
}

const SentimentPanel: React.FC<SentimentPanelProps> = ({
  symbol,
  sentiment,
  loading,
  onAnalyze,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!sentiment || !sentiment.available) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={aiBadgeStyle}>AI</span>
            <span style={{ fontWeight: 600, fontSize: 15 }}>
              Market Sentiment Analysis
            </span>
          </div>
          <button
            onClick={onAnalyze}
            disabled={loading}
            style={analyzeBtnStyle}
          >
            {loading ? "Analyzing..." : "Run Analysis"}
          </button>
        </div>
        <div style={{ color: "#8a8a9a", fontSize: 13, padding: "12px 0" }}>
          {loading
            ? "Running LLM analysis on market data..."
            : `No sentiment analysis available for ${symbol}. Click "Run Analysis" to generate one.`}
        </div>
      </div>
    );
  }

  const score = sentiment.signal_value ?? 0;
  const label = sentiment.label ?? "Neutral";
  const confidence = sentiment.confidence ?? 0;
  const reasoning = sentiment.reasoning ?? "";
  const factors = sentiment.factors ?? [];
  const analyzedAt = sentiment.analyzed_at ?? "";

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={aiBadgeStyle}>AI</span>
          <span style={{ fontWeight: 600, fontSize: 15 }}>
            Market Sentiment Analysis
          </span>
          {analyzedAt && (
            <span style={{ color: "#8a8a9a", fontSize: 11 }}>
              {sentiment.cached ? "cached" : ""} {analyzedAt.split("T")[0]}
            </span>
          )}
        </div>
        <button
          onClick={onAnalyze}
          disabled={loading}
          style={analyzeBtnStyle}
        >
          {loading ? "Analyzing..." : "Re-analyze"}
        </button>
      </div>

      {/* Score summary row */}
      <div style={scoreRowStyle}>
        <div>
          <span
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: scoreColor(score),
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {score > 0 ? "+" : ""}
            {score.toFixed(2)}
          </span>
          <span
            style={{
              marginLeft: 12,
              fontSize: 15,
              fontWeight: 600,
              color: labelColor(label),
            }}
          >
            {label}
          </span>
        </div>
        <div style={{ textAlign: "right" }}>
          <span style={{ color: "#8a8a9a", fontSize: 12 }}>Confidence: </span>
          <span
            style={{
              fontSize: 14,
              fontWeight: 600,
              color:
                confidence >= 0.7
                  ? "#16c784"
                  : confidence >= 0.4
                    ? "#f0b90b"
                    : "#e94560",
            }}
          >
            {(confidence * 100).toFixed(0)}% ({confidenceLabel(confidence)})
          </span>
        </div>
      </div>

      {/* Reasoning */}
      {reasoning && (
        <div style={reasoningStyle}>
          <p style={{ margin: 0, lineHeight: 1.5 }}>{reasoning}</p>
        </div>
      )}

      {/* Expandable factors */}
      {factors.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            style={expandBtnStyle}
          >
            {expanded ? "Hide" : "Show"} Factor Breakdown ({factors.length})
          </button>
          {expanded && (
            <div style={{ padding: "8px 0" }}>
              {factors.map((f, i) => (
                <div key={i} style={factorRowStyle}>
                  <span style={{ flex: 1, fontSize: 13 }}>{f.name}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={barContainerStyle}>
                      <div
                        style={{
                          position: "absolute",
                          left: "50%",
                          top: 0,
                          bottom: 0,
                          width: 1,
                          background: "#8a8a9a",
                        }}
                      />
                      <div
                        style={{
                          position: "absolute",
                          left: f.score >= 0 ? "50%" : `${50 + f.score * 50}%`,
                          width: `${Math.abs(f.score) * 50}%`,
                          top: 2,
                          bottom: 2,
                          background: scoreColor(f.score),
                          borderRadius: 2,
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: scoreColor(f.score),
                        minWidth: 36,
                        textAlign: "right",
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    >
                      {f.score > 0 ? "+" : ""}
                      {f.score.toFixed(2)}
                    </span>
                  </div>
                  {f.note && (
                    <div
                      style={{
                        width: "100%",
                        fontSize: 11,
                        color: "#8a8a9a",
                        marginTop: 2,
                      }}
                    >
                      {f.note}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Model info */}
      {sentiment.model_used && (
        <div
          style={{
            fontSize: 11,
            color: "#555",
            textAlign: "right",
            paddingTop: 4,
          }}
        >
          Model: {sentiment.model_used}
        </div>
      )}
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 8,
  padding: "16px 20px",
  border: "1px solid #0f3460",
  marginBottom: 16,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 12,
};

const aiBadgeStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  color: "#fff",
  fontSize: 10,
  fontWeight: 700,
  padding: "2px 6px",
  borderRadius: 4,
  letterSpacing: "0.05em",
};

const analyzeBtnStyle: React.CSSProperties = {
  padding: "6px 14px",
  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  border: "none",
  borderRadius: 4,
  color: "#fff",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 600,
};

const scoreRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "8px 0",
};

const reasoningStyle: React.CSSProperties = {
  color: "#d1d4dc",
  fontSize: 13,
  padding: "8px 12px",
  background: "rgba(0,0,0,0.2)",
  borderRadius: 6,
  marginBottom: 8,
};

const expandBtnStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: "#667eea",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 600,
  padding: "4px 0",
};

const factorRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  alignItems: "center",
  gap: 8,
  padding: "6px 0",
  borderBottom: "1px solid rgba(15, 52, 96, 0.3)",
};

const barContainerStyle: React.CSSProperties = {
  position: "relative",
  width: 80,
  height: 12,
  background: "rgba(0,0,0,0.3)",
  borderRadius: 3,
};

export default SentimentPanel;
