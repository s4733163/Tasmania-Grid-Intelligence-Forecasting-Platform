import { Outlet } from "react-router-dom";
import Navbar from "./Navbar.jsx";
import "./Layout.css";

function Layout() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-content">
        <Outlet />
      </main>
      <footer className="app-footer">
        Tasmania Grid Intelligence &amp; Forecasting Platform — data updates automatically
      </footer>
    </div>
  );
}

export default Layout;
