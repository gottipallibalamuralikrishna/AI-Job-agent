import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { CircularProgress, Box } from "@mui/material";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <Box className="center-screen">
        <CircularProgress />
      </Box>
    );
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
