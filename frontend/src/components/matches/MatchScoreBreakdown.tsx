import { Box, Typography } from "@mui/material";
import { BriefcaseBusiness, Code2, Layers3, Users } from "lucide-react";

interface MatchScoreBreakdownProps {
  roleScore: number;
  skillScore: number;
  experienceScore: number;
  responsibilityScore: number;
}

const scoreItems = [
  {
    key: "skills",
    label: "Technical skills",
    icon: Code2,
    color: "#9d8cff",
    getValue: (props: MatchScoreBreakdownProps) => props.skillScore,
  },
  {
    key: "role",
    label: "Role compatibility",
    icon: BriefcaseBusiness,
    color: "#36cfc9",
    getValue: (props: MatchScoreBreakdownProps) => props.roleScore,
  },
  {
    key: "experience",
    label: "Experience",
    icon: Layers3,
    color: "#f5b95f",
    getValue: (props: MatchScoreBreakdownProps) => props.experienceScore,
  },
  {
    key: "responsibilities",
    label: "Responsibilities",
    icon: Users,
    color: "#65d6a5",
    getValue: (props: MatchScoreBreakdownProps) => props.responsibilityScore,
  },
];

export default function MatchScoreBreakdown(props: MatchScoreBreakdownProps) {
  return (
    <Box className="match-breakdown">
      {scoreItems.map(({ key, label, icon: Icon, color, getValue }) => {
        const score = Math.max(0, Math.min(100, Number(getValue(props)) || 0));

        return (
          <Box className="match-score-row" key={key}>
            <Box className="match-score-label">
              <Box display="flex" alignItems="center" gap={1}>
                <Icon size={14} color={color} />
                <Typography>{label}</Typography>
              </Box>

              <Typography className="match-score-number">
                {score.toFixed(0)}%
              </Typography>
            </Box>

            <Box className="match-progress-track">
              <Box
                className="match-progress-fill"
                sx={{
                  width: `${score}%`,
                  backgroundColor: color,
                }}
              />
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
