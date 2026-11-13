import { useNavigate } from "react-router-dom";
import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Typography,
} from "@mui/material";

import {
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  BriefcaseBusiness,
  CheckCircle2,
  Clock3,
  FileUser,
  Mail,
  RadioTower,
  Search,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";

const metrics = [
  {
    label: "Jobs collected",
    value: "—",
    note: "Across connected sources",
    icon: BriefcaseBusiness,
    color: "#9d8cff",
  },
  {
    label: "AI matches",
    value: "—",
    note: "Compatible opportunities",
    icon: Target,
    color: "#36cfc9",
  },
  {
    label: "Saved jobs",
    value: "—",
    note: "Your bookmarked jobs",
    icon: Bookmark,
    color: "#f5b95f",
  },
  {
    label: "HR contacts",
    value: "—",
    note: "Public contacts discovered",
    icon: Mail,
    color: "#65d6a5",
  },
];

const nextSteps = [
  {
    number: "01",
    title: "Review your resume",
    description: "Make sure your skills and experience are accurate.",
    icon: FileUser,
    path: "/resume",
  },
  {
    number: "02",
    title: "Connect job sources",
    description: "Discover opportunities from permitted sources.",
    icon: RadioTower,
    path: "/telegram",
  },
  {
    number: "03",
    title: "Explore AI matches",
    description: "Find opportunities compatible with your profile.",
    icon: Target,
    path: "/matches",
  },
];

export default function OverviewPage() {
  const navigate = useNavigate();

  return (
    <Box className="overview-page">
      {/* Welcome section */}

      {/* Premium dashboard hero header */}
      <Box className="overview-hero">
        <Box className="overview-hero-content">
          <Box className="overview-hero-badge">
            <Sparkles size={14} />
            <Typography component="span">
              YOUR AI JOB SEARCH ASSISTANT
            </Typography>
          </Box>

          <Typography className="overview-hero-title">
            Your next career move
            <br />
            starts <span>here.</span>
          </Typography>

          <Typography className="overview-hero-description">
            Discover relevant opportunities, match your skills with AI, and take
            control of your job search — all in one workspace.
          </Typography>

          <Box className="overview-hero-actions">
            <Button
              variant="contained"
              startIcon={<Search size={17} />}
              endIcon={<ArrowUpRight size={16} />}
              onClick={() => navigate("/jobs")}
              className="overview-hero-primary"
            >
              Explore opportunities
            </Button>

            <Button
              variant="outlined"
              startIcon={<Target size={17} />}
              onClick={() => navigate("/matches")}
              className="overview-hero-secondary"
            >
              View AI matches
            </Button>
          </Box>

          <Box className="overview-hero-footer">
            <Box className="hero-status-dot" />
            <Typography component="span">
              Your personal job search workspace is ready
            </Typography>
          </Box>
        </Box>

        <Box className="overview-hero-visual">
          <Box className="hero-orbit hero-orbit-one" />
          <Box className="hero-orbit hero-orbit-two" />

          <Box className="hero-main-icon">
            <Sparkles size={48} strokeWidth={1.4} />
          </Box>

          <Box className="hero-floating-card hero-floating-top">
            <Target size={17} />
            <Box>
              <Typography>AI MATCHING</Typography>
              <strong>Smart discovery</strong>
            </Box>
          </Box>

          <Box className="hero-floating-card hero-floating-bottom">
            <BriefcaseBusiness size={18} />
            <Box>
              <Typography>JOB DISCOVERY</Typography>
              <strong>New opportunities</strong>
            </Box>
          </Box>

          <Box className="hero-glow" />
        </Box>
      </Box>

      {/* Workspace status */}
      <Card className="overview-welcome-card">
        <CardContent className="overview-welcome-content">
          <Box className="overview-welcome-icon">
            <Sparkles size={24} />
          </Box>

          <Box className="overview-welcome-copy">
            <Typography fontWeight={750}>
              Your career journey starts here
            </Typography>

            <Typography variant="body2" color="text.secondary">
              JobPilot AI brings job discovery, resume analysis, and opportunity
              tracking into one workspace.
            </Typography>
          </Box>

          <Chip
            icon={<CheckCircle2 size={14} />}
            label="Workspace active"
            className="workspace-active-chip"
          />
        </CardContent>
      </Card>

      {/* Metrics */}
      <Box className="overview-section">
        <Box className="overview-section-heading">
          <Box>
            <Typography className="overview-section-title">
              Your job search at a glance
            </Typography>

            <Typography className="overview-section-description">
              An overview of your job search progress.
            </Typography>
          </Box>
        </Box>

        <Box className="overview-metrics-grid">
          {metrics.map(({ label, value, note, icon: Icon, color }) => (
            <Card className="overview-metric-card" key={label}>
              <CardContent>
                <Box className="overview-metric-top">
                  <Box
                    className="overview-metric-icon"
                    sx={{
                      color,
                      backgroundColor: `${color}18`,
                    }}
                  >
                    <Icon size={20} />
                  </Box>

                  <ArrowUpRight size={17} className="overview-muted-icon" />
                </Box>

                <Typography className="overview-metric-value">
                  {value}
                </Typography>

                <Typography className="overview-metric-label">
                  {label}
                </Typography>

                <Typography className="overview-metric-note">{note}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {/* Recent matches and activity */}
      <Box className="overview-main-grid">
        <Card className="overview-panel">
          <CardContent className="overview-panel-content">
            <Box className="overview-panel-heading">
              <Box className="overview-panel-title-group">
                <Box className="overview-panel-icon purple">
                  <Target size={19} />
                </Box>

                <Box>
                  <Typography className="overview-panel-title">
                    Recent AI matches
                  </Typography>

                  <Typography className="overview-panel-subtitle">
                    Opportunities compatible with your resume
                  </Typography>
                </Box>
              </Box>

              <Button
                size="small"
                endIcon={<ArrowRight size={15} />}
                onClick={() => navigate("/matches")}
              >
                View all
              </Button>
            </Box>

            <Box className="overview-empty-state">
              <Avatar className="overview-empty-icon">
                <Target size={23} />
              </Avatar>

              <Typography fontWeight={700}>
                Your matches will appear here
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                textAlign="center"
                maxWidth={340}
              >
                Analyze available jobs against your resume to discover relevant
                opportunities.
              </Typography>

              <Button
                variant="outlined"
                size="small"
                onClick={() => navigate("/matches")}
                endIcon={<ArrowRight size={15} />}
              >
                Explore AI matches
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Card className="overview-panel">
          <CardContent className="overview-panel-content">
            <Box className="overview-panel-heading">
              <Box className="overview-panel-title-group">
                <Box className="overview-panel-icon teal">
                  <TrendingUp size={19} />
                </Box>

                <Box>
                  <Typography className="overview-panel-title">
                    Job discovery activity
                  </Typography>

                  <Typography className="overview-panel-subtitle">
                    Your collection activity
                  </Typography>
                </Box>
              </Box>

              <Chip label="Activity" size="small" variant="outlined" />
            </Box>

            <Box className="overview-empty-state">
              <Avatar className="overview-empty-icon teal-bg">
                <Clock3 size={23} />
              </Avatar>

              <Typography fontWeight={700}>
                No activity to display yet
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                textAlign="center"
                maxWidth={320}
              >
                Job collection trends will appear here when your connected
                sources start collecting opportunities.
              </Typography>

              <Button
                variant="outlined"
                size="small"
                onClick={() => navigate("/jobs")}
                endIcon={<ArrowRight size={15} />}
              >
                Browse available jobs
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Getting started */}
      <Card className="overview-next-steps">
        <CardContent className="overview-panel-content">
          <Box className="overview-panel-heading">
            <Box>
              <Typography className="overview-panel-title">
                Continue your job search
              </Typography>

              <Typography className="overview-panel-subtitle">
                Complete these steps to get more from JobPilot AI.
              </Typography>
            </Box>

            <Chip label="Getting started" size="small" />
          </Box>

          <Box className="overview-steps-grid">
            {nextSteps.map(
              ({ number, title, description, icon: Icon, path }) => (
                <Box
                  className="overview-step"
                  key={number}
                  onClick={() => navigate(path)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(path);
                    }
                  }}
                >
                  <Box className="overview-step-top">
                    <Box className="overview-step-number">{number}</Box>
                    <Icon size={19} className="overview-step-icon" />
                  </Box>

                  <Typography className="overview-step-title">
                    {title}
                  </Typography>

                  <Typography className="overview-step-description">
                    {description}
                  </Typography>

                  <Box className="overview-step-action">
                    Get started <ArrowRight size={14} />
                  </Box>
                </Box>
              ),
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
