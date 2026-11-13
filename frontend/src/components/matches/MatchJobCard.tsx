import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Typography,
} from "@mui/material";

import {
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  MapPin,
  Clock3,
  ExternalLink,
} from "lucide-react";

import type { JobMatch } from "../../api/jobMatchesApi";
import MatchScoreBreakdown from "./MatchScoreBreakdown";

interface MatchJobCardProps {
  match: JobMatch;
  onViewDetails: (match: JobMatch) => void;
}

function getScoreColor(score: number) {
  if (score >= 85) return "#65d6a5";
  if (score >= 70) return "#a99aff";
  if (score >= 50) return "#f5b95f";
  return "#ef858e";
}

function formatExperience(match: JobMatch) {
  const { experience_min, experience_max } = match.job;

  if (experience_min == null && experience_max == null) {
    return "Experience not specified";
  }

  if (experience_min != null && experience_max != null) {
    return `${experience_min}–${experience_max} years`;
  }

  return experience_min != null
    ? `${experience_min}+ years`
    : `Up to ${experience_max} years`;
}

function formatWorkMode(value: string | null) {
  if (!value) return null;

  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatPostedDate(value: string | null) {
  if (!value) return "Date unavailable";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "Date unavailable";

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function MatchJobCard({
  match,
  onViewDetails,
}: MatchJobCardProps) {
  const job = match.job;
  const scoreColor = getScoreColor(match.match_score);

  return (
    <Card className="match-job-card">
      <CardContent className="match-job-card-content">
        <Box className="match-card-header">
          <Box className="match-company-info">
            <Box className="match-company-logo">
              {job.company_logo ? (
                <img src={job.company_logo} alt={`${job.company_name} logo`} />
              ) : (
                <Building2 size={22} />
              )}
            </Box>

            <Box minWidth={0}>
              <Typography className="match-job-title">{job.title}</Typography>

              <Typography className="match-company-name">
                {job.company_name}
              </Typography>
            </Box>
          </Box>

          <Box className="match-score-badge">
            <Typography
              className="match-score-value"
              sx={{ color: scoreColor }}
            >
              {match.match_score.toFixed(0)}%
            </Typography>
            <Typography className="match-score-caption">MATCH</Typography>
          </Box>
        </Box>

        <Box className="match-job-metadata">
          {job.location && (
            <Box>
              <MapPin size={13} />
              <Typography>{job.location}</Typography>
            </Box>
          )}

          <Box>
            <BriefcaseBusiness size={13} />
            <Typography>{formatExperience(match)}</Typography>
          </Box>

          {job.work_mode && (
            <Box>
              <Clock3 size={13} />
              <Typography>{formatWorkMode(job.work_mode)}</Typography>
            </Box>
          )}
        </Box>

        <Box className="match-status-row">
          <Chip
            size="small"
            label={
              match.decision === "matched"
                ? "Recommended match"
                : "Below match criteria"
            }
            color={match.decision === "matched" ? "success" : "default"}
            variant="outlined"
          />

          {job.posted_at && (
            <Typography className="match-posted-date">
              Posted {formatPostedDate(job.posted_at)}
            </Typography>
          )}
        </Box>

        <Divider className="match-card-divider" />

        <Typography className="match-section-label">
          COMPATIBILITY BREAKDOWN
        </Typography>

        <MatchScoreBreakdown
          roleScore={match.role_match_score}
          skillScore={match.skill_match_score}
          experienceScore={match.experience_match_score}
          responsibilityScore={match.responsibility_match_score}
        />

        <Divider className="match-card-divider" />

        <Box className="match-skills-section">
          <Typography className="match-section-label">
            MATCHED SKILLS ({match.matched_skills.length})
          </Typography>

          <Box className="match-skill-list">
            {match.matched_skills.length > 0 ? (
              match.matched_skills
                .slice(0, 6)
                .map((skill) => (
                  <Chip
                    key={skill}
                    label={skill}
                    size="small"
                    className="matched-skill-chip"
                  />
                ))
            ) : (
              <Typography className="match-muted-text">
                No matched skills identified.
              </Typography>
            )}
          </Box>

          {match.missing_skills.length > 0 && (
            <>
              <Typography className="match-section-label missing-label">
                MISSING SKILLS
              </Typography>

              <Box className="match-skill-list">
                {match.missing_skills.slice(0, 4).map((skill) => (
                  <Chip
                    key={skill}
                    label={skill}
                    size="small"
                    className="missing-skill-chip"
                  />
                ))}
              </Box>
            </>
          )}
        </Box>

        {match.match_explanation && (
          <Box className="match-explanation">
            <Typography className="match-section-label">
              MATCH INSIGHT
            </Typography>

            <Typography>{match.match_explanation}</Typography>
          </Box>
        )}

        <Box className="match-card-actions">
          <Button
            variant="outlined"
            onClick={() => onViewDetails(match)}
            endIcon={<ArrowUpRight size={15} />}
          >
            View analysis
          </Button>

          {job.application_url && (
            <Button
              variant="contained"
              component="a"
              href={job.application_url}
              target="_blank"
              rel="noopener noreferrer"
              endIcon={<ExternalLink size={14} />}
            >
              Apply now
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
