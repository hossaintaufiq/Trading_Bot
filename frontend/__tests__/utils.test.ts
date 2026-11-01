import { describe, it, expect } from "vitest";
import { toChartTime, formatUsdt, formatPct, formatDurationMs } from "../app/lib/utils";

describe("Frontend Utility Functions", () => {
  it("converts ISO 8601 UTC timestamp to Unix seconds for Lightweight Charts (ADR-012)", () => {
    const iso = "2026-11-01T20:00:00.000Z";
    const chartTime = toChartTime(iso);
    expect(chartTime).toBe(Math.floor(new Date(iso).getTime() / 1000));
  });

  it("formats USDT currency properly", () => {
    expect(formatUsdt(1000)).toBe("$1,000.00");
    expect(formatUsdt(-250.5)).toBe("-$250.50");
  });

  it("formats percentage with sign", () => {
    expect(formatPct(5.25)).toBe("+5.25%");
    expect(formatPct(-1.8)).toBe("-1.80%");
  });

  it("formats duration ms", () => {
    expect(formatDurationMs(450)).toBe("450ms");
    expect(formatDurationMs(2500)).toBe("2.5s");
  });
});
