import { api } from "../api/client";
import { useNavigate } from "react-router-dom";

export default function CandidateDashboard() {
  const nav = useNavigate();
  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } finally {
      nav("/login");
    }
  }
  return (
    <div>
      <h1>Welcome</h1>
      <button onClick={logout}>Log out</button>
    </div>
  );
}
