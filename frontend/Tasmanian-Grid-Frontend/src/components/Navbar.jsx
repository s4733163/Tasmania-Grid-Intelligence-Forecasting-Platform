import { NavLink } from "react-router-dom";
import "./Navbar.css";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/aemo", label: "AEMO" },
  { to: "/hydro", label: "Hydro Tasmania" },
  { to: "/tasnetworks", label: "TasNetworks" },
  { to: "/public", label: "Public View" },
  { to: "/health", label: "System Health" },
];

function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">
          <span className="navbar-brand-dot" />
          <span className="navbar-brand-text">Tasmania Grid Intelligence</span>
        </div>
        <nav className="navbar-links">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                isActive ? "navbar-link navbar-link-active" : "navbar-link"
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}

export default Navbar;
