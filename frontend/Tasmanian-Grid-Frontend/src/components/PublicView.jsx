import { useEffect, useState } from "react";
import { getCurrent, getForecasts, formatMW, formatPercent, highestRisk } from "./api.js";
import StatCard from "./StatCard.jsx";
import ForecastChart from "./ForecastChart.jsx";
import "./PublicView.css";

const STATUS_COPY = {
  Low: {
    label: "Good",
    color: "green",
    message: "Most of Tasmania's expected electricity demand is forecast to be covered by renewable generation.",
  },
  Medium: {
    label: "Fair",
    color: "amber",
    message: "Tasmania's electricity demand is expected to be mostly covered by renewable generation, with some periods of tighter supply.",
  },
  High: {
    label: "Watch",
    color: "red",
    message: "Renewable generation may not fully cover expected electricity demand during some periods over the next 36 hours.",
  },
};

function groupByDate(forecasts) {
  const groups = {};
  forecasts.forEach((row) => {
    const date = row.forecast_date;
    if (!groups[date]) groups[date] = [];
    groups[date].push(row);
  });
  return groups;
}

function averageCoverage(rows) {
  if (!rows || rows.length === 0) return null;
  const total = rows.reduce((sum, row) => sum + (row.renewable_coverage_percent || 0), 0);
  return total / rows.length;
}

function PublicView() {
  const [current, setCurrent] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [currentData, forecastData] = await Promise.all([getCurrent(), getForecasts()]);
        if (cancelled) return;
        setCurrent(currentData);
        setForecasts(forecastData.value || []);
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
        <h3>Loading Tasmania's grid outlook…</h3>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-card error">
        <h3>Grid information is temporarily unavailable</h3>
        <p>Please try again shortly.</p>
      </div>
    );
  }

  const hasCurrent = current && !current.message;
  const risk = highestRisk(forecasts)?.risk_level;
  const status = STATUS_COPY[risk] || STATUS_COPY.Medium;

  const dateGroups = groupByDate(forecasts);
  const dates = Object.keys(dateGroups).sort();

  return (
    <div>
      <div className="page-header">
        <h1>Tasmania's Electricity Outlook</h1>
        <p>A simple look at today's power supply and how much comes from renewable sources.</p>
      </div>

      <div className={`public-status-card public-status-${status.color}`}>
        <div className="public-status-dot" />
        <div>
          <div className="public-status-label">Grid Status: {status.label}</div>
          <div className="public-status-message">{status.message}</div>
        </div>
      </div>

      <div className="stat-grid" style={{ marginTop: 20 }}>
        <StatCard
          label="Current Demand"
          value={hasCurrent ? formatMW(current.current_demand_mw) : "—"}
          accent="blue"
        />
        <StatCard
          label="Current Renewable Share"
          value={hasCurrent ? formatPercent(current.renewable_coverage_percent) : "—"}
          sublabel="Share of demand from renewable generation"
          accent="green"
        />
      </div>

      <h2 className="section-title">Today &amp; Tomorrow</h2>
      <div className="stat-grid">
        {dates.slice(0, 2).map((date, index) => {
          const avg = averageCoverage(dateGroups[date]);
          return (
            <StatCard
              key={date}
              label={index === 0 ? "Today" : "Tomorrow"}
              value={avg !== null ? formatPercent(avg) : "—"}
              sublabel="Average renewable coverage expected"
              accent="green"
            />
          );
        })}
      </div>

      <h2 className="section-title">Renewable Coverage Outlook</h2>
      <ForecastChart
        data={forecasts}
        yFormatter={(v) => `${Math.round(v)}%`}
        lines={[{ dataKey: "renewable_coverage_percent", name: "Renewable Coverage", color: "#22c55e" }]}
      />
    </div>
  );
}

export default PublicView;
