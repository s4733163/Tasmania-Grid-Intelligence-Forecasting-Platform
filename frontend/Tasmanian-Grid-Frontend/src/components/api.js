const BASE_URL = "https://tasmania-grid-intelligence-forecasting-8cre.onrender.com/";

async function request(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return response.json();
}

export async function getCurrent() {
  return request("/current");
}

export async function getForecasts() {
  return request("/forecasts");
}

export async function getSummary() {
  return request("/summary");
}

export async function getHealth() {
  return request("/health");
}

export function formatMW(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toLocaleString("en-AU", { maximumFractionDigits: 0 })} MW`;
}

export function formatPrice(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `$${Number(value).toLocaleString("en-AU", { maximumFractionDigits: 2 })}/MWh`;
}

export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toFixed(1)}%`;
}

export function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-AU", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-AU", {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const RISK_WEIGHT = { Low: 0, Medium: 1, High: 2 };

export function riskWeight(level) {
  return RISK_WEIGHT[level] ?? -1;
}

export function highestRisk(rows) {
  if (!rows || rows.length === 0) return null;
  return rows.reduce((worst, row) => {
    return riskWeight(row.risk_level) > riskWeight(worst?.risk_level) ? row : worst;
  }, rows[0]);
}

export function peakBy(rows, key) {
  if (!rows || rows.length === 0) return null;
  return rows.reduce((max, row) => (row[key] > (max?.[key] ?? -Infinity) ? row : max), rows[0]);
}

export function minBy(rows, key) {
  if (!rows || rows.length === 0) return null;
  return rows.reduce((min, row) => (row[key] < (min?.[key] ?? Infinity) ? row : min), rows[0]);
}

export function surplusHours(rows) {
  if (!rows) return [];
  return rows.filter((row) => row.predicted_renewable_mw > row.predicted_demand_mw);
}

export function networkLoadRisk(rows) {
  if (!rows || rows.length === 0) return null;
  const demands = rows.map((row) => row.predicted_demand_mw);
  const peakDemand = Math.max(...demands);
  const averageDemand = demands.reduce((sum, value) => sum + value, 0) / demands.length;

  if (peakDemand <= averageDemand * 1.05) return "Low";
  if (peakDemand <= averageDemand * 1.15) return "Medium";
  return "High";
}
