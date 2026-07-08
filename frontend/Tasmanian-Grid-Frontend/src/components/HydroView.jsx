import { useEffect, useState } from "react";
import {
  getCurrent,
  getForecasts,
  getSummary,
  formatMW,
  formatTimestamp,
  surplusHours,
} from "./api.js";
import StatCard from "./StatCard.jsx";
import ForecastChart from "./ForecastChart.jsx";
import "./HydroView.css";

function HydroView() {
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
        <h3>Loading generation view…</h3>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-card error">
        <h3>Unable to load Hydro Tasmania view</h3>
        <p>{error}. Check that the backend API is running at http://127.0.0.1:8000.</p>
      </div>
    );
  }

  const hasCurrent = current && !current.message;
  const hasSummary = summary && !summary.message;
  const surplus = surplusHours(forecasts);

  return (
    <div>
      <div className="page-header">
        <h1>Hydro Tasmania View</h1>
        <p>Generator view — renewable output and surplus supply opportunities.</p>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Current Renewable Generation"
          value={hasCurrent ? formatMW(current.current_renewable_mw) : "—"}
          accent="green"
        />
        <StatCard
          label="Peak Renewable Generation"
          value={hasSummary ? formatMW(summary.peak_renewable.value_mw) : "—"}
          sublabel={hasSummary ? formatTimestamp(summary.peak_renewable.timestamp) : ""}
          accent="green"
        />
        <StatCard
          label="Lowest Renewable Period"
          value={hasSummary ? formatMW(summary.lowest_renewable.value_mw) : "—"}
          sublabel={hasSummary ? formatTimestamp(summary.lowest_renewable.timestamp) : ""}
          accent="amber"
        />
        <StatCard
          label="Expected Surplus Hours"
          value={`${surplus.length} of ${forecasts.length}`}
          sublabel="Renewable generation exceeds demand"
          accent="blue"
        />
      </div>

      <div className="insight-grid" style={{ marginTop: 24 }}>
        <div className="insight-card insight-green">
          <div className="insight-title">High Generation Opportunity</div>
          <div className="insight-body">
            {hasSummary
              ? `Peak output of ${formatMW(summary.peak_renewable.value_mw)} expected around ${formatTimestamp(summary.peak_renewable.timestamp)}.`
              : "No forecast data available."}
          </div>
        </div>
        <div className="insight-card insight-amber">
          <div className="insight-title">Low Renewable Output Period</div>
          <div className="insight-body">
            {hasSummary
              ? `Output may fall to ${formatMW(summary.lowest_renewable.value_mw)} around ${formatTimestamp(summary.lowest_renewable.timestamp)}.`
              : "No forecast data available."}
          </div>
        </div>
        <div className="insight-card insight-blue">
          <div className="insight-title">Expected Surplus Hours</div>
          <div className="insight-body">
            {surplus.length > 0
              ? `${surplus.length} hour${surplus.length === 1 ? "" : "s"} where renewable generation is forecast to exceed demand.`
              : "No surplus hours expected in this forecast window."}
          </div>
        </div>
      </div>

      <h2 className="section-title">Renewable Generation Forecast</h2>
      <ForecastChart
        data={forecasts}
        yFormatter={(v) => `${Math.round(v)} MW`}
        lines={[{ dataKey: "predicted_renewable_mw", name: "Renewable Generation", color: "#22c55e" }]}
      />

      <h2 className="section-title">Renewable vs Demand</h2>
      <ForecastChart
        data={forecasts}
        yFormatter={(v) => `${Math.round(v)} MW`}
        lines={[
          { dataKey: "predicted_renewable_mw", name: "Renewable Generation", color: "#22c55e" },
          { dataKey: "predicted_demand_mw", name: "Demand", color: "#38bdf8" },
        ]}
      />
    </div>
  );
}

export default HydroView;
