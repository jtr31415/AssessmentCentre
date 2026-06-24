import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import AdminSlots from "./pages/AdminSlots";
import CandidateLogin from "./pages/CandidateLogin";
import SetPassword from "./pages/SetPassword";
import CandidateBooking from "./pages/CandidateBooking";
import CandidateDashboard from "./pages/CandidateDashboard";
import Privacy from "./pages/Privacy";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/slots" element={<AdminSlots />} />
        <Route path="/login" element={<CandidateLogin />} />
        <Route path="/set-password" element={<SetPassword />} />
        <Route path="/dashboard" element={<CandidateDashboard />} />
        <Route path="/book" element={<CandidateBooking />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="*" element={<CandidateLogin />} />
      </Routes>
      <footer style={{ padding: 16, fontSize: 12 }}>
        <Link to="/privacy">Privacy</Link>
      </footer>
    </BrowserRouter>
  );
}
