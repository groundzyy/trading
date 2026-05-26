import React, { useRef, useEffect } from "react";
import {
  createChart,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import type { Candle, SwingPoint } from "../types";

interface MALine {
  time: string;
  value: number;
}

interface CandlestickChartProps {
  candles: Candle[];
  swingPoints: SwingPoint[];
  maData?: Record<string, MALine[]>;
}

const MA_COLORS: Record<string, string> = {
  MA5: "#f0e130",
  MA10: "#2196f3",
  MA20: "#9c27b0",
  MA60: "#16c784",
};

const THEME = {
  bg: "#1a1a2e",
  text: "#d1d4dc",
  grid: "#1e2a3a",
};

function buildMarkers(swingPoints: SwingPoint[]): SeriesMarker<Time>[] {
  const markerConfig: Record<
    string,
    {
      shape: SeriesMarker<Time>["shape"];
      position: SeriesMarker<Time>["position"];
      color: string;
      size: number;
      text?: string;
    }
  > = {
    STH: {
      shape: "circle",
      position: "aboveBar",
      color: "#ff6b6b",
      size: 1,
    },
    STL: {
      shape: "circle",
      position: "belowBar",
      color: "#51cf66",
      size: 1,
    },
    MTH: {
      shape: "arrowDown",
      position: "aboveBar",
      color: "#e94560",
      size: 2,
      text: "MTH",
    },
    MTL: {
      shape: "arrowUp",
      position: "belowBar",
      color: "#16c784",
      size: 2,
      text: "MTL",
    },
    LTH: {
      shape: "arrowDown",
      position: "aboveBar",
      color: "#ff0000",
      size: 3,
      text: "LTH",
    },
    LTL: {
      shape: "arrowUp",
      position: "belowBar",
      color: "#00ff00",
      size: 3,
      text: "LTL",
    },
    BUY: {
      shape: "arrowUp",
      position: "belowBar",
      color: "#16c784",
      size: 3,
      text: "BUY",
    },
    SELL: {
      shape: "arrowDown",
      position: "aboveBar",
      color: "#e94560",
      size: 3,
      text: "SELL",
    },
  };

  const markers: SeriesMarker<Time>[] = swingPoints
    .map((sp) => {
      const cfg = markerConfig[sp.level];
      if (!cfg) return null;
      return {
        time: sp.date as Time,
        position: cfg.position,
        shape: cfg.shape,
        color: cfg.color,
        size: cfg.size,
        text: cfg.text,
      } as SeriesMarker<Time>;
    })
    .filter((m): m is SeriesMarker<Time> => m !== null);

  // Markers must be sorted by time ascending
  markers.sort((a, b) => {
    if (a.time < b.time) return -1;
    if (a.time > b.time) return 1;
    return 0;
  });

  return markers;
}

const legendStyle: React.CSSProperties = {
  position: "absolute",
  top: 8,
  left: 12,
  zIndex: 10,
  fontSize: 11,
  fontFamily: "'JetBrains Mono', monospace",
  color: THEME.text,
  pointerEvents: "none",
  lineHeight: "18px",
  userSelect: "none",
};

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  candles,
  swingPoints,
  maData,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const maSeriesRefs = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight || 500,
      layout: {
        background: { color: THEME.bg },
        textColor: THEME.text,
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: THEME.grid },
        horzLines: { color: THEME.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: THEME.grid,
      },
      timeScale: {
        borderColor: THEME.grid,
        timeVisible: true,
      },
    });

    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#16c784",
      downColor: "#e94560",
      borderDownColor: "#e94560",
      borderUpColor: "#16c784",
      wickDownColor: "#e94560",
      wickUpColor: "#16c784",
    });
    candleSeriesRef.current = candleSeries;

    // Volume series (overlay at bottom, separate price scale)
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.85,
        bottom: 0,
      },
    });
    volumeSeriesRef.current = volumeSeries;

    // ResizeObserver
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      maSeriesRefs.current.clear();
    };
  }, []);

  // Update candle data
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;

    const candleData = candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candleSeriesRef.current.setData(candleData);

    const volumeData = candles.map((c) => ({
      time: c.time as Time,
      value: c.volume,
      color: c.close >= c.open ? "rgba(22,199,132,0.35)" : "rgba(233,69,96,0.35)",
    }));
    volumeSeriesRef.current.setData(volumeData);
  }, [candles]);

  // Update swing point markers
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    const markers = buildMarkers(swingPoints);
    candleSeriesRef.current.setMarkers(markers);
  }, [swingPoints]);

  // Update MA lines
  useEffect(() => {
    if (!chartRef.current) return;

    // Remove old MA series that are no longer present
    const currentKeys = maData ? Object.keys(maData) : [];
    for (const [key, series] of maSeriesRefs.current.entries()) {
      if (!currentKeys.includes(key)) {
        chartRef.current.removeSeries(series);
        maSeriesRefs.current.delete(key);
      }
    }

    if (!maData) return;

    for (const [key, values] of Object.entries(maData)) {
      const color =
        MA_COLORS[key.toUpperCase()] ?? MA_COLORS[key] ?? "#888888";
      let series = maSeriesRefs.current.get(key);

      if (!series) {
        series = chartRef.current.addLineSeries({
          color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        maSeriesRefs.current.set(key, series);
      }

      series.setData(
        values.map((v) => ({
          time: v.time as Time,
          value: v.value,
        }))
      );
    }
  }, [maData]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: 400,
      }}
    >
      {/* Legend overlay */}
      <div style={legendStyle}>
        <div>
          <span style={{ color: "#d1d4dc", fontWeight: 600 }}>HIGH: </span>
          <span style={{ color: "#ff6b6b" }}>{"·"}STH</span>
          {"  "}
          <span style={{ color: "#e94560" }}>{"▲"}MTH</span>
          {"  "}
          <span style={{ color: "#ff0000" }}>{"★"}LTH</span>
        </div>
        <div>
          <span style={{ color: "#d1d4dc", fontWeight: 600 }}>LOW: </span>
          <span style={{ color: "#51cf66" }}>{"·"}STL</span>
          {"  "}
          <span style={{ color: "#16c784" }}>{"▼"}MTL</span>
          {"  "}
          <span style={{ color: "#00ff00" }}>{"★"}LTL</span>
        </div>
      </div>

      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
};

export default CandlestickChart;
