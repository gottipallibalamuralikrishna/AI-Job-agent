import { useLayoutEffect, useState } from "react";
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
  FileUser,
  Ellipsis,
  Sparkles,
  RadioTower,
  Users,
  ClipboardList,
  Target,
  LogOut,
  Search,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const drawerWidth = 252;

const navigation = [
  { label: "AI Matches", path: "/matches", icon: Target },
  { label: "All Jobs", path: "/jobs", icon: BriefcaseBusiness },
  { label: "Telegram Jobs", path: "/telegram", icon: RadioTower },
  { label: "HR Contacts", path: "/contacts", icon: Users },
  { label: "Applications", path: "/applications", icon: ClipboardList },
  { label: "Resume Profile", path: "/resume", icon: FileUser },
];

export default function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const currentPage = navigation.find((item) => item.path === location.pathname);
  const mobileTabs = [navigation[0], navigation[1], navigation[4], navigation[5]];
  const moreSelected = location.pathname === "/telegram" || location.pathname === "/contacts";

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);

  const sidebar = (
    <Box className="sidebar-content">
      <Box className="sidebar-brand">
        <Box className="brand-symbol"><Sparkles size={19} aria-hidden="true" /></Box>
        <Box>
          <Typography fontWeight={800} letterSpacing={-0.5}>
            JobPilot AI
          </Typography>
        </Box>
      </Box>
      <Divider />
      <List className="sidebar-nav" component="nav" aria-label="Workspace">
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
          <Box minWidth={0} title={user?.full_name}>
            <Typography variant="body2" fontWeight={650} noWrap>
              {user?.full_name}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" noWrap title={user?.email}>
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
            maxWidth: "100vw",
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
          {isDesktop ? (
            <Toolbar className="workspace-header">
              <Typography variant="h6" fontWeight={750}>{currentPage?.label ?? "Workspace"}</Typography>
              <Box className="workspace-header-actions">
                <Button variant="outlined" startIcon={<Search size={16} />} onClick={() => navigate("/jobs")}>
                  Find jobs
                </Button>
                <Tooltip title={user?.full_name ?? "My account"}>
                  <Avatar sx={{ width: 34, height: 34 }}>{user?.full_name?.[0] ?? "U"}</Avatar>
                </Tooltip>
              </Box>
            </Toolbar>
          ) : (
            <Toolbar className="mobile-header">
              <Box className="mobile-header-mark"><Sparkles size={20} /></Box>
              <Box className="mobile-header-title">
                <Typography variant="caption" color="text.secondary">JobPilot AI</Typography>
                <Typography fontWeight={750}>{currentPage?.label ?? "Workspace"}</Typography>
              </Box>
              <IconButton aria-label="Find jobs" onClick={() => navigate("/jobs")}><Search size={21} /></IconButton>
            </Toolbar>
          )}
        </AppBar>

        <main className={isDesktop ? undefined : "mobile-workspace"}>
          <Outlet />
        </main>
        {!isDesktop && (
          <Box component="nav" aria-label="Mobile navigation" className="mobile-navigation">
            {mobileTabs.map(({ path, icon: Icon }, index) => (
              <Button key={path} className="mobile-nav-button"
                aria-current={location.pathname === path ? "page" : undefined}
                onClick={() => navigate(path)}>
                <Icon size={19} />
                <span>{["Matches", "Jobs", "Applied", "Resume"][index]}</span>
              </Button>
            ))}
            <Button className="mobile-nav-button" aria-label="More navigation options"
              aria-expanded={mobileOpen} aria-current={moreSelected ? "page" : undefined}
              onClick={() => setMobileOpen(true)}>
              <Ellipsis size={19} />
              <span>More</span>
            </Button>
          </Box>
        )}
      </Box>
    </Box>
  );
}
