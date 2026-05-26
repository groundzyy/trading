import React, { useRef, useEffect, useState } from "react";
import {
  createChart,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type Time,
  type MouseEventParams,
} from "lightweight-charts";

interface LineConfig {
  key: string;
  color: string;
  label: string;
}

interface IndicatorPanelProps {
  title: string;
  data: { date: string; [key: string]: any }[];
  lines: LineConfig[];
}

const THEME = {
  bg: "#1a1a2e",
  card: "#16213e",
  text: "#d1d4dc",
  grid: "#1e2a3a",
};

const PANEL_HEIGHT = 120;

const IndicatorPanel: React.FC<IndicatorPanelProps> = ({
  title,
  data,
  lines,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesMapRef = useRef<
    Map<string, ISeriesApi<"Line"> | ISeriesApi<"Histogram">>
  >(new Map());
  const [legendValues, setLegendValues] = useState<Record<string, string>>({});

  // Create chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: PANEL_HEIGHT,
      layout: {
        background: { color: THEME.bg },
        textColor: THEME.text,
        fontFamily: "'Inter', sans-serif",
        fontSize: 10,
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
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: THEME.grid,
        visible: false,
      },
      handleScroll: false,
      handleScale: false,
    });

    chartRef.current = chart;

    // Create series for each line
    for (const line of lines) {
      const isHistogram =
        line.key.toLowerCase() === "histogram" ||
        line.key.toLowerCase() === "macd_hist";

      if (isHistogram) {
        const series = chart.addHistogramSeries({
          priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
          priceLineVisible: false,
          lastValueVisible: false,
        });
        seriesMapRef.current.set(line.key, series);
      } else {
        const series = chart.addLineSeries({
          color: line.color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: 3,
        });
        seriesMapRef.current.set(line.key, series);
      }
    }

    // Crosshair legend handler
    chart.subscribeCrosshairMove((param: MouseEventParams) => {
      const vals: Record<string, string> = {};
      for (const line of lines) {
        const series = seriesMapRef.current.get(line.key);
        if (series && param.seriesData) {
          const point = param.seriesData.get(series);
          if (point && "value" in point) {
            vals[line.key] = (point as { value: number }).value.toFixed(4);
          }
        }
      }
      setLegendValues(vals);
    });

    // ResizeObserver
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesMapRef.current.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update data
  useEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    for (const line of lines) {
      const series = seriesMapRef.current.get(line.key);
      if (!series) continue;

      const isHistogram =
        line.key.toLowerCase() === "histogram" ||
        line.key.toLowerCase() === "macd_hist";

      if (isHistogram) {
        const histData = data
          .filter((d) => d[line.key] !== undefined && d[line.key] !== null)
          .map((d) => ({
            time: d.date as Time,
            value: Number(d[line.key]),
            color:
              Number(d[line.key]) >= 0
                ? "rgba(22,199,132,0.7)"
                : "rgba(233,69,96,0.7)",
          }));
        series.setData(histData);
      } else {
        const lineData = data
          .filter((d) => d[line.key] !== undefined && d[line.key] !== null)
          .map((d) => ({
            time: d.date as Time,
            value: Number(d[line.key]),
          }));
        series.setData(lineData);
      }
    }
  }, [data, lines]);

  return (
    <div
      style={{
        background: THEME.card,
        borderRadius: 6,
        border: `1px solid ${THEME.grid}`,
        overflow: "hidden",
        marginBottom: 8,
      }}
    >
      {/* Header with legend */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "4px 10px",
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          color: THEME.text,
          background: "rgba(0,0,0,0.2)",
          borderBottom: `1px solid ${THEME.grid}`,
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 600, marginRight: 4 }}>{title}</span>
        {lines.map((line) => (
          <span key={line.key} style={{ color: line.color }}>
            {line.label}:{" "}
            <span style={{ color: THEME.text }}>
              {legendValues[line.key] ?? "--"}
            </span>
          </span>
        ))}
      </div>

      <div
        ref={containerRef}
        style={{ width: "100%", height: PANEL_HEIGHT }}
      />
    </div>
  );
};

export default IndicatorPanel;
