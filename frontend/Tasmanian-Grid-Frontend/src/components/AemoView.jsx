import { useEffect, useState } from "react";
import {
  getCurrent,
  getForecasts,
  getSummary,
  formatMW,
  formatPrice,
  formatPercent,
  formatTimestamp,
  formatTime,
  highestRisk,
} from "./api.js";
import StatCard from "./StatCard.jsx";
import RiskBadge from "./RiskBadge.jsx";
import ForecastChart from "./ForecastChart.jsx";
import "./AemoView.css";

const RISK_COLOR = { Low: "#22c55e", Medium: "#f59e0b", High: "#ef4444" };

const SUPPLY_MESSAGE = {
  Low: "Yes — supply is forecast to comfortably meet demand.",
  Medium: "Mostly — supply should meet demand, with some pressure expected.",
  High: "Caution — supply may struggle to meet demand during peak periods.",
};

function AemoView() {
  const [current, setCurrent] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [currentData, forecastData, summaryData] = await Promise.all([
          getCurrent(),
          getForecasts(),
          getSummary(),
        ]);
        if (cancelled) return;
        setCurrent(currentData);
        setForecasts(forecastData.value || []);
        setSummary(summaryData);
      } catch (err) {
        if (!cancelled) setError(err.message || "Unable to reach the grid data service.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="state-card">
        <h3>Loading market view…</h3>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-card error">
        <h3>Unable to load AEMO view</h3>
        <p>{error}. Check that the backend API is running at http://127.0.0.1:8000.</p>
      </div>
    );
  }

  const hasCurrent = current && !current.message;
  const hasSummary = summary && !summary.message;
  const risk = hasSummary ? summary.highest_risk : highestRisk(forecasts)?.risk_level;

  return (
    <div>
      <div className="page-header">
        <h1>AEMO View</h1>
        <p>Market and operator view — balancing forecast demand against forecast supply.</p>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Current Demand"
          value={hasCurrent ? formatMW(current.current_demand_mw) : "—"}
          accent="blue"
        />
        <StatCard
          label="Peak Demand Period"
          value={hasSummary ? formatMW(summary.peak_demand.value_mw) : "—"}
          sublabel={hasSummary ? formatTimestamp(summary.peak_demand.timestamp) : ""}
          accent="amber"
        />
        <StatCard
          label="Expected Renewable Coverage"
          value={hasSummary ? formatPercent(summary.average_renewable_coverage_percent) : "—"}
          sublabel="Average across forecast horizon"
          accent="green"
        />
        <StatCard
          label="Market Price Signal"
          value={hasSummary ? formatPrice(summary.average_price_per_mwh) : "—"}
          sublabel={
            hasSummary
              ? `Highest expected: ${formatPrice(summary.highest_price.value_per_mwh)} at ${formatTime(summary.highest_price.timestamp)}`
              : ""
          }
          accent="amber"
        />
      </div>

      <div className="aemo-supply-card">
        <div className="aemo-supply-question">Will supply likely meet demand?</div>
        <div className="aemo-supply-answer">
          <RiskBadge level={risk} />
          <span>{SUPPLY_MESSAGE[risk] || "Not enough data to assess supply risk."}</span>
        </div>
      </div>

      <h2 className="section-title">Demand vs Renewable Generation</h2>
      <ForecastChart
        data={forecasts}
        yFormatter={(v) => `${Math.round(v)} MW`}
        lines={[
          { dataKey: "predicted_demand_mw", name: "Demand", color: "#38bdf8" },
          { dataKey: "predicted_renewable_mw", name: "Renewable Generation", color: "#22c55e" },
        ]}
      />

      <h2 className="section-title">Risk Timeline</h2>
      <div className="risk-timeline-card">
        <div className="risk-timeline-strip">
          {forecasts.map((row) => (
            <div
              key={row.forecast_timestamp}
              className="risk-timeline-block"
              style={{ background: RISK_COLOR[row.risk_level] || "#334155" }}
              title={`${formatTimestamp(row.forecast_timestamp)} — ${row.risk_level} risk`}
            />
          ))}
        </div>
        <div className="risk-timeline-legend">
          <span><i style={{ background: RISK_COLOR.Low }} /> Low</span>
          <span><i style={{ background: RISK_COLOR.Medium }} /> Medium</span>
          <span><i style={{ background: RISK_COLOR.High }} /> High</span>
        </div>
      </div>
    </div>
  );
}

export default AemoView;
