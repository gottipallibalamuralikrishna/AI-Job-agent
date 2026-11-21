import ApplicationsPage from "./pages/dashboard/ApplicationsPage";
import { Navigate, Route, Routes } from "react-router-dom";
import AIMatchesPage from "./pages/dashboard/AIMatchesPage";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";

import ResumeProfilePage from "./pages/dashboard/ResumeProfilePage";
import AllJobsPage from "./pages/dashboard/AllJobsPage";
import RecruiterContactsPage from "./pages/contacts/RecruiterContactsPage";
import DashboardLayout from "./layouts/DashboardLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import TelegramJobsPage from "./pages/telegram/TelegramJobsPage";
import LandingPage from "./pages/LandingPage";

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route index element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="matches" element={<AIMatchesPage />} />
          <Route path="resume" element={<ResumeProfilePage />} />
          <Route path="contacts" element={<RecruiterContactsPage />} />
          <Route path="telegram" element={<TelegramJobsPage />} />
          {/* Real Jobs page */}
          <Route path="applications" element={<ApplicationsPage />} />
          <Route path="jobs" element={<AllJobsPage />} />

        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
