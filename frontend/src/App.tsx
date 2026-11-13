import { Navigate, Route, Routes } from "react-router-dom";
import AIMatchesPage from "./pages/dashboard/AIMatchesPage";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";

import OverviewPage from "./pages/dashboard/OverviewPage";
import PlaceholderPage from "./pages/dashboard/PlaceholderPage";
import ResumeProfilePage from "./pages/dashboard/ResumeProfilePage";
import AllJobsPage from "./pages/dashboard/AllJobsPage";
import RecruiterContactsPage from "./pages/contacts/RecruiterContactsPage";
import DashboardLayout from "./layouts/DashboardLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import TelegramJobsPage from "./pages/telegram/TelegramJobsPage";

const modules = [
  {
    path: "telegram",
    title: "Telegram Jobs",
    description: "Jobs collected from Telegram.",
  },
  {
    path: "contacts",
    title: "HR Contacts",
    description: "Explore recruiter contacts.",
  },
  {
    path: "saved",
    title: "Saved Jobs",
    description: "Your saved jobs.",
  },
  {
    path: "applications",
    title: "Applications",
    description: "Track your applications.",
  },
  {
    path: "assistant",
    title: "AI Assistant",
    description: "Your job search assistant.",
  },
  {
    path: "settings",
    title: "Settings",
    description: "Manage your preferences.",
  },
];

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="matches" element={<AIMatchesPage />} />
          <Route path="resume" element={<ResumeProfilePage />} />
          <Route path="contacts" element={<RecruiterContactsPage />} />
          <Route path="telegram" element={<TelegramJobsPage />} />
          {/* Real Jobs page */}
          <Route path="jobs" element={<AllJobsPage />} />

          {/* Remaining placeholder modules */}
          {modules.map((module) => (
            <Route
              key={module.path}
              path={module.path}
              element={
                <PlaceholderPage
                  title={module.title}
                  description={module.description}
                />
              }
            />
          ))}
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
