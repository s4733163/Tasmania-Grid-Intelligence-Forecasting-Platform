import { useEffect, useState } from "react";
import {
  getCurrent,
  getForecasts,
  getSummary,
  formatMW,
  formatTimestamp,
  networkLoadRisk,
} from "./api.js";
import StatCard from "./StatCard.jsx";
import ForecastChart from "./ForecastChart.jsx";
import ForecastTable from "./ForecastTable.jsx";
import "./TasNetworksView.css";

function TasNetworksView() {
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
        <h3>Loading network load view…</h3>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-card error">
        <h3>Unable to load TasNetworks view</h3>
        <p>{error}. Check that the backend API is running at http://127.0.0.1:8000.</p>
      </div>
    );
  }

  const hasCurrent = current && !current.message;
  const hasSummary = summary && !summary.message;
  const loadRisk = networkLoadRisk(forecasts);

  return (
    <div>
      <div className="page-header">
        <h1>TasNetworks View</h1>
        <p>Network view — expected load on the transmission and distribution system.</p>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Expected Network Load"
          value={hasCurrent ? formatMW(current.current_demand_mw) : "—"}
          sublabel="Current demand"
          accent="blue"
        />
        <StatCard
          label="Peak Load Time"
          value={hasSummary ? formatMW(summary.peak_demand.value_mw) : "—"}
          sublabel={hasSummary ? formatTimestamp(summary.peak_demand.timestamp) : ""}
          accent="amber"
        />
        <StatCard
          label="Average Demand"
          value={hasSummary ? formatMW(summary.average_demand_mw) : "—"}
          sublabel="Across forecast horizon"
          accent="blue"
        />
        <StatCard
          label="Network Load Risk"
          value={loadRisk || "—"}
          sublabel="Based on forecast demand relative to the expected daily average."
          accent={loadRisk === "High" ? "red" : loadRisk === "Medium" ? "amber" : "green"}
        />
      </div>

      <h2 className="section-title">Demand Forecast</h2>
      <ForecastChart
        data={forecasts}
        yFormatter={(v) => `${Math.round(v)} MW`}
        lines={[{ dataKey: "predicted_demand_mw", name: "Demand", color: "#38bdf8" }]}
      />

      <h2 className="section-title">Forecast Table</h2>
      <ForecastTable rows={forecasts} columns={["time", "demand", "risk"]} />
    </div>
  );
}

export default TasNetworksView;
