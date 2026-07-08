import "./RiskBadge.css";

const RISK_CLASS = {
  Low: "risk-badge-low",
  Medium: "risk-badge-medium",
  High: "risk-badge-high",
};

function RiskBadge({ level }) {
  const className = RISK_CLASS[level] || "risk-badge-unknown";
  return <span className={`risk-badge ${className}`}>{level || "Unknown"}</span>;
}

export default RiskBadge;
