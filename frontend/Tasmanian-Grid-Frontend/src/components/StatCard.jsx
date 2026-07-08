import "./StatCard.css";

const ACCENT_CLASS = {
  blue: "stat-card-blue",
  green: "stat-card-green",
  amber: "stat-card-amber",
  red: "stat-card-red",
};

function StatCard({ label, value, sublabel, accent = "blue" }) {
  const accentClass = ACCENT_CLASS[accent] || ACCENT_CLASS.blue;
  return (
    <div className={`stat-card ${accentClass}`}>
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {sublabel ? <div className="stat-card-sublabel">{sublabel}</div> : null}
    </div>
  );
}

export default StatCard;
