import { useEffect, useState } from "react";
import {
  getCurrent,
  getForecasts,
  formatMW,
  formatPrice,
  formatPercent,
  formatTimestamp,
} from "./api.js";
import StatCard from "./StatCard.jsx";
import ForecastChart from "./ForecastChart.jsx";
import ForecastTable from "./ForecastTable.jsx";
import "./Dashboard.css";

function Dashboard() {
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
        <h3>Loading grid data…</h3>
        <p>Fetching the latest readings and forecast.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-card error">
        <h3>Unable to load dashboard data</h3>
        <p>{error}. Check that the backend API is running at http://127.0.0.1:8000.</p>
      </div>
    );
  }

  const nextForecast = forecasts[0] || null;
  const hasCurrent = current && !current.message;

  return (
    <div>
      <div className="page-header">
        <h1>Tasmania Grid Intelligence &amp; Forecasting Platform</h1>
        <p>
          {hasCurrent
            ? `Latest actual reading: ${formatTimestamp(current.timestamp)}`
            : "Latest actual reading unavailable"}
        </p>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Current Demand"
          value={hasCurrent ? formatMW(current.current_demand_mw) : "—"}
          accent="blue"
        />
        <StatCard
          label="Current Renewable Generation"
          value={hasCurrent ? formatMW(current.current_renewable_mw) : "—"}
          accent="green"
        />
        <StatCard
          label="Current Price"
          value={hasCurrent ? formatPrice(current.current_price_per_mwh) : "—"}
          accent="amber"
        />
        <StatCard
          label="Renewable Coverage"
          value={hasCurrent ? formatPercent(current.renewable_coverage_percent) : "—"}
          accent="green"
        />
      </div>

      <h2 className="section-title">Forecast Horizon: Next 36 Hours</h2>

      {nextForecast ? (
        <div className="dashboard-next-forecast">
          <div className="dashboard-next-forecast-label">Next Hour Forecast</div>
          <div className="dashboard-next-forecast-grid">
            <div>
              <span className="dashboard-next-forecast-key">Time</span>
              <span className="dashboard-next-forecast-value">
                {formatTimestamp(nextForecast.forecast_timestamp)}
              </span>
            </div>
            <div>
              <span className="dashboard-next-forecast-key">Demand</span>
              <span className="dashboard-next-forecast-value">
                {formatMW(nextForecast.predicted_demand_mw)}
              </span>
            </div>
            <div>
              <span className="dashboard-next-forecast-key">Renewable Generation</span>
              <span className="dashboard-next-forecast-value">
                {formatMW(nextForecast.predicted_renewable_mw)}
              </span>
            </div>
            <div>
              <span className="dashboard-next-forecast-key">Coverage</span>
              <span className="dashboard-next-forecast-value">
                {formatPercent(nextForecast.renewable_coverage_percent)}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="state-card">
          <h3>No forecast data yet</h3>
          <p>Forecast rows will appear here once generated.</p>
        </div>
      )}

      <div className="chart-grid" style={{ marginTop: 24 }}>
        <ForecastChart
          title="Demand Forecast"
          data={forecasts}
          yFormatter={(v) => `${Math.round(v)} MW`}
          lines={[{ dataKey: "predicted_demand_mw", name: "Demand", color: "#38bdf8" }]}
        />
        <ForecastChart
          title="Renewable Generation Forecast"
          data={forecasts}
          yFormatter={(v) => `${Math.round(v)} MW`}
          lines={[
            { dataKey: "predicted_renewable_mw", name: "Renewable Generation", color: "#22c55e" },
          ]}
        />
        <ForecastChart
          title="Renewable Coverage Forecast"
          data={forecasts}
          yFormatter={(v) => `${Math.round(v)}%`}
          lines={[
            { dataKey: "renewable_coverage_percent", name: "Coverage", color: "#38bdf8" },
          ]}
        />
      </div>

      <h2 className="section-title">36-Hour Forecast Table</h2>
      <ForecastTable rows={forecasts} />
    </div>
  );
}

export default Dashboard;
