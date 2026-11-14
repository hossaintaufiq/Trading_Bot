import { ColorType, LineType, type DeepPartial, type ChartOptions } from "lightweight-charts";

/** Shared premium chart look: transparent canvas, faint grid, no hard borders. */
export const chartOptions: DeepPartial<ChartOptions> = {
  layout: {
    background: { type: ColorType.Solid, color: "transparent" },
    textColor: "#8d8da9",
    fontFamily: "Inter, system-ui, sans-serif",
    attributionLogo: false,
  },
  grid: { vertLines: { color: "rgba(255,255,255,0.03)" }, horzLines: { color: "rgba(255,255,255,0.04)" } },
  rightPriceScale: { borderVisible: false },
  timeScale: { borderVisible: false },
  crosshair: { vertLine: { color: "rgba(167,139,250,0.4)" }, horzLine: { color: "rgba(167,139,250,0.4)" } },
  autoSize: true,
};

/** Smooth curved line (never a straight/stepped polyline). */
export const curvedLine = {
  color: "#a78bfa",
  lineWidth: 3 as const,
  lineType: LineType.Curved,
  priceLineVisible: false,
  crosshairMarkerRadius: 5,
};
