import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import { formatTime } from "./api.js";
import "./ForecastChart.css";

function CustomTooltip({ active, payload, label, valueFormatter }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="forecast-chart-tooltip">
      <div className="forecast-chart-tooltip-label">{formatTime(label)}</div>
      {payload.map((item) => (
        <div key={item.dataKey} className="forecast-chart-tooltip-row">
          <span className="forecast-chart-tooltip-dot" style={{ background: item.color }} />
          <span className="forecast-chart-tooltip-name">{item.name}</span>
          <span className="forecast-chart-tooltip-value">
            {valueFormatter ? valueFormatter(item.value) : item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function ForecastChart({
  title,
  data,
  lines,
  xKey = "forecast_timestamp",
  yFormatter,
  height = 280,
}) {
  return (
    <div className="forecast-chart-card">
      {title ? <h3 className="forecast-chart-title">{title}</h3> : null}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
          <XAxis
            dataKey={xKey}
            tickFormatter={formatTime}
            stroke="#64748b"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            minTickGap={32}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickFormatter={yFormatter}
            width={70}
          />
          <Tooltip content={<CustomTooltip valueFormatter={yFormatter} />} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
          {lines.map((line) => (
            <Line
              key={line.dataKey}
              type="monotone"
              dataKey={line.dataKey}
              name={line.name}
              stroke={line.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ForecastChart;
