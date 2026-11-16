import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Alert, Button, CircularProgress, Box } from "@mui/material";

export default function ProtectedRoute() {
  const { user, loading, sessionUnavailable, retrySession } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <Box className="center-screen">
        <CircularProgress />
      </Box>
    );
  if (sessionUnavailable)
    return (
      <Box className="center-screen" sx={{ p: 2 }}>
        <Alert severity="warning" action={<Button onClick={retrySession}>Retry</Button>}>
          Unable to verify your session. Check your connection and retry.
        </Alert>
      </Box>
    );
  return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location }} />;
}
