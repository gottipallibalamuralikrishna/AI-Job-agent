import {
  Box,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";

import { X, Sparkles, AlertCircle, CheckCircle2 } from "lucide-react";

import type { JobMatch } from "../../api/jobMatchesApi";
import MatchScoreBreakdown from "./MatchScoreBreakdown";

interface MatchDetailsDialogProps {
  match: JobMatch | null;
  onClose: () => void;
}

function SkillGroup({
  title,
  skills,
  type,
}: {
  title: string;
  skills: string[];
  type: "matched" | "missing" | "preferred";
}) {
  const className =
    type === "matched"
      ? "matched-skill-chip"
      : type === "missing"
        ? "missing-skill-chip"
        : "preferred-skill-chip";

  return (
    <Box className="match-dialog-section">
      <Typography className="match-dialog-section-title">
        {title} ({skills.length})
      </Typography>

      <Box className="match-skill-list">
        {skills.length > 0 ? (
          skills.map((skill) => (
            <Chip
              key={skill}
              label={skill}
              size="small"
              className={className}
            />
          ))
        ) : (
          <Typography color="text.secondary" variant="body2">
            None identified.
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export default function MatchDetailsDialog({
  match,
  onClose,
}: MatchDetailsDialogProps) {
  if (!match) return null;

  return (
    <Dialog
      open={Boolean(match)}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      PaperProps={{ className: "match-details-dialog" }}
    >
      <DialogTitle className="match-dialog-header">
        <Box>
          <Typography variant="h6" fontWeight={800}>
            Match analysis
          </Typography>

          <Typography color="text.secondary" variant="body2">
            {match.job.title} · {match.job.company_name}
          </Typography>
        </Box>

        <IconButton onClick={onClose} aria-label="Close analysis">
          <X size={19} />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3}>
          <Box className="match-dialog-score">
            <Box>
              <Typography color="text.secondary" variant="caption">
                OVERALL COMPATIBILITY
              </Typography>

              <Typography className="match-dialog-score-value">
                {match.match_score.toFixed(1)}%
              </Typography>
            </Box>

            <Chip
              label={
                match.decision === "matched"
                  ? "Recommended match"
                  : "Not recommended"
              }
              color={match.decision === "matched" ? "success" : "default"}
              variant="outlined"
            />
          </Box>

          <Divider />

          <Box>
            <Typography className="match-dialog-section-title" mb={2}>
              Scoring breakdown
            </Typography>

            <MatchScoreBreakdown
              roleScore={match.role_match_score}
              skillScore={match.skill_match_score}
              experienceScore={match.experience_match_score}
              responsibilityScore={match.responsibility_match_score}
            />
          </Box>

          <Divider />

          <Box>
            <Typography className="match-dialog-section-title" mb={1}>
              Role compatibility
            </Typography>

            <Typography variant="body2" color="text.secondary">
              Candidate role: {match.candidate_role_family ?? "Not identified"}
            </Typography>

            <Typography variant="body2" color="text.secondary">
              Job role: {match.role_family ?? "Not identified"}
            </Typography>
          </Box>

          <Divider />

          <SkillGroup
            title="Matched skills"
            skills={match.matched_skills}
            type="matched"
          />

          <SkillGroup
            title="Missing required skills"
            skills={match.missing_skills}
            type="missing"
          />

          <SkillGroup
            title="Preferred skills"
            skills={match.preferred_skills}
            type="preferred"
          />

          <SkillGroup
            title="Missing preferred skills"
            skills={match.missing_preferred_skills}
            type="missing"
          />

          <Divider />

          <Box>
            <Typography className="match-dialog-section-title" mb={1}>
              Experience comparison
            </Typography>

            <Typography variant="body2" color="text.secondary">
              Your experience: {match.candidate_experience_years} years
            </Typography>

            <Typography variant="body2" color="text.secondary">
              Required experience:{" "}
              {match.required_experience_years == null
                ? "Not specified"
                : `${match.required_experience_years} years`}
            </Typography>
          </Box>

          <Divider />

          <Box>
            <Typography className="match-dialog-section-title" mb={1}>
              Matched responsibilities
            </Typography>

            {match.matched_responsibility_categories.length > 0 ? (
              <Box className="match-skill-list">
                {match.matched_responsibility_categories.map((item) => (
                  <Chip
                    key={item}
                    label={item.replace(/_/g, " ")}
                    size="small"
                    className="matched-skill-chip"
                  />
                ))}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No matching responsibility categories identified.
              </Typography>
            )}
          </Box>

          {match.match_explanation && (
            <>
              <Divider />

              <Box className="match-dialog-explanation">
                <Sparkles size={17} />

                <Box>
                  <Typography fontWeight={700} mb={0.5}>
                    Why this score?
                  </Typography>

                  <Typography variant="body2" color="text.secondary">
                    {match.match_explanation}
                  </Typography>
                </Box>
              </Box>
            </>
          )}

          {match.rejection_reasons.length > 0 && (
            <>
              <Divider />

              <Box>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <AlertCircle size={16} color="#ef858e" />
                  <Typography className="match-dialog-section-title">
                    Areas affecting this match
                  </Typography>
                </Box>

                <Stack spacing={1}>
                  {match.rejection_reasons.map((reason) => (
                    <Box
                      key={reason}
                      display="flex"
                      alignItems="center"
                      gap={1}
                    >
                      <AlertCircle size={14} color="#ef858e" />

                      <Typography variant="body2" color="text.secondary">
                        {reason.replace(/_/g, " ")}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            </>
          )}

          <Box display="flex" alignItems="center" gap={1}>
            <CheckCircle2 size={15} color="#65d6a5" />
            <Typography variant="caption" color="text.secondary">
              Analysis generated from your selected resume and this job posting.
            </Typography>
          </Box>
        </Stack>
      </DialogContent>
    </Dialog>
  );
}
