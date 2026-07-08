import { formatTimestamp, formatMW, formatPrice, formatPercent } from "./api.js";
import RiskBadge from "./RiskBadge.jsx";
import "./ForecastTable.css";

const COLUMN_DEFS = {
  time: {
    label: "Time",
    render: (row) => formatTimestamp(row.forecast_timestamp),
  },
  demand: {
    label: "Demand MW",
    render: (row) => formatMW(row.predicted_demand_mw),
  },
  renewable: {
    label: "Renewable MW",
    render: (row) => formatMW(row.predicted_renewable_mw),
  },
  price: {
    label: "Estimated Price",
    render: (row) => formatPrice(row.estimated_price_per_mwh),
  },
  coverage: {
    label: "Coverage %",
    render: (row) => formatPercent(row.renewable_coverage_percent),
  },
  risk: {
    label: "Risk",
    render: (row) => <RiskBadge level={row.risk_level} />,
  },
};

const DEFAULT_COLUMNS = ["time", "demand", "renewable", "price", "coverage", "risk"];

function ForecastTable({ rows, columns = DEFAULT_COLUMNS }) {
  if (!rows || rows.length === 0) {
    return <div className="forecast-table-empty">No forecast rows available.</div>;
  }

  return (
    <div className="forecast-table-wrap">
      <table className="forecast-table">
        <thead>
          <tr>
            {columns.map((key) => (
              <th key={key}>{COLUMN_DEFS[key].label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.forecast_timestamp}>
              {columns.map((key) => (
                <td key={key}>{COLUMN_DEFS[key].render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ForecastTable;
