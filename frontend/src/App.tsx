import { BrowserRouter, Route, Routes } from "react-router-dom";
import Shell from "./components/Shell";
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import AdminSlots from "./pages/AdminSlots";
import AdminQuestions from "./pages/AdminQuestions";
import AdminActivity from "./pages/AdminActivity";
import AdminConfig from "./pages/AdminConfig";
import CandidateLogin from "./pages/CandidateLogin";
import SetPassword from "./pages/SetPassword";
import CandidateBooking from "./pages/CandidateBooking";
import CandidateDashboard from "./pages/CandidateDashboard";
import CandidateQA from "./pages/CandidateQA";
import Privacy from "./pages/Privacy";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/slots" element={<AdminSlots />} />
          <Route path="/admin/questions" element={<AdminQuestions />} />
          <Route path="/admin/activity" element={<AdminActivity />} />
          <Route path="/admin/config" element={<AdminConfig />} />
          <Route path="/login" element={<CandidateLogin />} />
          <Route path="/set-password" element={<SetPassword />} />
          <Route path="/dashboard" element={<CandidateDashboard />} />
          <Route path="/questions" element={<CandidateQA />} />
          <Route path="/book" element={<CandidateBooking />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="*" element={<CandidateLogin />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
