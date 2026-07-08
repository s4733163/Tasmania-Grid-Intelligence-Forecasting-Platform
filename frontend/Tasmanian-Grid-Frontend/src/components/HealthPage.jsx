import { useEffect, useState } from "react";
import { getHealth, formatTimestamp } from "./api.js";
import "./HealthPage.css";

function HealthPage() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getHealth();
        if (!cancelled) setHealth(data);
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
        <h3>Checking system health…</h3>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-card error">
        <h3>Unable to reach the API</h3>
        <p>{error}. Check that the backend API is running at http://127.0.0.1:8000.</p>
      </div>
    );
  }

  const isHealthy = health?.status === "healthy";

  return (
    <div>
      <div className="page-header">
        <h1>System Health</h1>
        <p>Live status of the data and forecasting service.</p>
      </div>

      <div className={`health-status-card ${isHealthy ? "health-ok" : "health-bad"}`}>
        <div className="health-status-dot" />
        <div>
          <div className="health-status-label">
            API Status: {isHealthy ? "Healthy" : "Unhealthy"}
          </div>
          {!isHealthy && health?.error ? (
            <div className="health-status-error">{health.error}</div>
          ) : null}
        </div>
      </div>

      <div className="stat-grid" style={{ marginTop: 20 }}>
        <div className="health-card">
          <div className="health-card-label">Latest Energy Reading</div>
          <div className="health-card-value">
            {health?.latest_energy_reading ? formatTimestamp(health.latest_energy_reading) : "—"}
          </div>
        </div>
        <div className="health-card">
          <div className="health-card-label">Latest Forecast</div>
          <div className="health-card-value">
            {health?.latest_forecast ? formatTimestamp(health.latest_forecast) : "—"}
          </div>
        </div>
        <div className="health-card">
          <div className="health-card-label">Forecasting Models</div>
          <div className="health-card-value">
            {isHealthy ? (health?.models_loaded ? "Loaded" : "Not Loaded") : "—"}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HealthPage;
