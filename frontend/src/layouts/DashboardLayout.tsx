import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  BriefcaseBusiness,
  Bot,
  Bookmark,
  FileUser,
  LayoutDashboard,
  Menu,
  RadioTower,
  Settings,
  Users,
  ClipboardList,
  Target,
  LogOut,
  Search,
  ArrowUpRight,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const drawerWidth = 252;

const navigation = [
  { label: "Overview", path: "/", icon: LayoutDashboard },
  { label: "All Jobs", path: "/jobs", icon: BriefcaseBusiness },
  { label: "AI Matches", path: "/matches", icon: Target },
  { label: "Telegram Jobs", path: "/telegram", icon: RadioTower },
  { label: "HR Contacts", path: "/contacts", icon: Users },
  { label: "Saved Jobs", path: "/saved", icon: Bookmark },
  { label: "Applications", path: "/applications", icon: ClipboardList },
  { label: "Resume Profile", path: "/resume", icon: FileUser },
  { label: "AI Assistant", path: "/assistant", icon: Bot },
  { label: "Settings", path: "/settings", icon: Settings },
];

export default function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const sidebar = (
    <Box className="sidebar-content">
      <Box className="sidebar-brand">
        <Box className="brand-symbol">✦</Box>
        <Box>
          <Typography fontWeight={800} letterSpacing={-0.5}>
            JobPilot AI
          </Typography>
          <Typography variant="caption" color="text.secondary">
            JOB SEARCH WORKSPACE
          </Typography>
        </Box>
      </Box>
      <Divider />
      <Typography className="nav-section-label">WORKSPACE</Typography>
      <List className="sidebar-nav">
        {navigation.map(({ label, path, icon: Icon }) => {
          const selected = location.pathname === path;
          return (
            <ListItemButton
              key={path}
              selected={selected}
              onClick={() => {
                navigate(path);
                setMobileOpen(false);
              }}
              className="nav-item"
            >
              <ListItemIcon>
                <Icon size={18} />
              </ListItemIcon>
              <ListItemText primary={label} />
            </ListItemButton>
          );
        })}
      </List>
      <Box className="sidebar-bottom">
        <Divider />
        <Box className="sidebar-user">
          <Avatar>{user?.full_name?.[0] ?? "U"}</Avatar>
          <Box flex={1} minWidth={0}>
            <Typography variant="body2" fontWeight={650} noWrap>
              {user?.full_name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {user?.email}
            </Typography>
          </Box>
          <IconButton
            size="small"
            aria-label="Sign out"
            onClick={() => void logout()}
          >
            <LogOut size={17} />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box className="dashboard-shell">
      <Drawer
        variant={isDesktop ? "permanent" : "temporary"}
        open={isDesktop || mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          width: isDesktop ? drawerWidth : "auto",
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            boxSizing: "border-box",
            background: "#0e1422",
            borderRight: "1px solid #222d42",
          },
        }}
      >
        {sidebar}
      </Drawer>
      <Box className="dashboard-main">
        <AppBar position="sticky" elevation={0} className="dashboard-topbar">
          <Toolbar className="topbar-toolbar premium-toolbar">
            {!isDesktop && (
              <IconButton
                color="inherit"
                onClick={() => setMobileOpen(true)}
                edge="start"
                sx={{ mr: 1 }}
              >
                <Menu size={20} />
              </IconButton>
            )}

            {/* Dynamic page information */}
            <Box className="topbar-page-info">
              <Box className="topbar-breadcrumb">
                <Typography>JOBPILOT AI</Typography>
                <span>/</span>
                <Typography className="topbar-current-page">
                  {navigation.find((item) => item.path === location.pathname)
                    ?.label ?? "Overview"}
                </Typography>
              </Box>

              <Typography className="topbar-heading">
                {location.pathname === "/"
                  ? "Your job search command center"
                  : (navigation.find((item) => item.path === location.pathname)
                      ?.label ?? "Your workspace")}
              </Typography>

              <Typography className="topbar-description">
                Discover opportunities and move your career forward.
              </Typography>
            </Box>

            {/* Right side actions */}
            <Box className="topbar-actions">
              <Button
                variant="outlined"
                startIcon={<Search size={16} />}
                endIcon={<ArrowUpRight size={14} />}
                onClick={() => navigate("/jobs")}
                className="topbar-search-button"
              >
                Search opportunities
              </Button>

              <Tooltip title="Your workspace is active">
                <Box className="topbar-status-pill">
                  <span className="topbar-status-dot" />
                  <Typography>Workspace active</Typography>
                </Box>
              </Tooltip>

              <Tooltip title={user?.full_name ?? "My account"}>
                <Avatar className="topbar-avatar">
                  {user?.full_name?.[0] ?? "U"}
                </Avatar>
              </Tooltip>
            </Box>
          </Toolbar>
        </AppBar>

        <main>
          <Outlet />
        </main>
      </Box>
    </Box>
  );
}
