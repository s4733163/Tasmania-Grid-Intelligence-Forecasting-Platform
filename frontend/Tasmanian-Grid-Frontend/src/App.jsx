import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Dashboard from "./components/Dashboard.jsx";
import AemoView from "./components/AemoView.jsx";
import HydroView from "./components/HydroView.jsx";
import TasNetworksView from "./components/TasNetworksView.jsx";
import PublicView from "./components/PublicView.jsx";
import HealthPage from "./components/HealthPage.jsx";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="aemo" element={<AemoView />} />
          <Route path="hydro" element={<HydroView />} />
          <Route path="tasnetworks" element={<TasNetworksView />} />
          <Route path="public" element={<PublicView />} />
          <Route path="health" element={<HealthPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
