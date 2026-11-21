import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { FileUser, RefreshCw, Save, Sparkles } from "lucide-react";

import axios from "axios";

import { api } from "../../api/axios";
import ResumeUploadSection from "../../components/resume/ResumeUploadSection";

// --------------------------------------------------
// Interfaces
// --------------------------------------------------

interface Resume {
  id: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  parsing_status: string;
  is_primary: boolean;
  created_at: string;
}

interface CandidateProfile {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  professional_title: string | null;
  professional_summary: string | null;
  total_experience_years: number | null;

  technical_skills: string[];
  soft_skills: string[];

  work_experience: Record<string, unknown>[];
  education: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  certifications: Record<string, unknown>[];
}

interface ResumeProfileResponse {
  id: string;
  resume_id: string;
  profile_data: CandidateProfile;
  created_at: string;
  updated_at: string;
}

// --------------------------------------------------
// Utility
// --------------------------------------------------

const formatJson = (value: unknown): string => {
  return JSON.stringify(value ?? [], null, 2);
};

// --------------------------------------------------
// Component
// --------------------------------------------------

export default function ResumeProfilePage() {
  // Resume states
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState("");

  // Profile state
  const [profile, setProfile] = useState<CandidateProfile | null>(null);

  // JSON editor states
  const [workExperienceJson, setWorkExperienceJson] = useState("[]");

  const [educationJson, setEducationJson] = useState("[]");

  const [projectsJson, setProjectsJson] = useState("[]");

  const [certificationsJson, setCertificationsJson] = useState("[]");

  // Loading states
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Messages
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // --------------------------------------------------
  // Load Resumes
  // --------------------------------------------------

  const loadResumes = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get<Resume[]>("/resumes");

      setResumes(response.data);

      if (response.data.length > 0) {
        const currentExists = response.data.some(
          (resume) => resume.id === selectedResumeId,
        );

        if (!currentExists) {
          setSelectedResumeId(response.data[0].id);
        }
      } else {
        setSelectedResumeId("");
        setProfile(null);
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || "Unable to load resumes.");
      } else {
        setError("Unable to load resumes.");
      }
    } finally {
      setLoading(false);
    }
  }, [selectedResumeId]);

  // Initial resume loading
  useEffect(() => {
    void loadResumes();
  }, [loadResumes]);

  // --------------------------------------------------
  // Load Extracted Profile
  // --------------------------------------------------

  const loadProfile = useCallback(async (resumeId: string) => {
    try {
      setProfileLoading(true);
      setError("");
      setSuccess("");

      const response = await api.get<ResumeProfileResponse>(
        `/resumes/${resumeId}/profile`,
      );

      const data = response.data.profile_data;

      // Update profile
      setProfile(data);

      // Update JSON editors
      setWorkExperienceJson(formatJson(data.work_experience));

      setEducationJson(formatJson(data.education));

      setProjectsJson(formatJson(data.projects));

      setCertificationsJson(formatJson(data.certifications));
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        // Profile hasn't been generated yet.
        setProfile(null);

        setWorkExperienceJson("[]");
        setEducationJson("[]");
        setProjectsJson("[]");
        setCertificationsJson("[]");

        return;
      }

      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail || "Unable to load resume profile.",
        );
      } else {
        setError("Unable to load resume profile.");
      }

      setProfile(null);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  // Load profile when selected resume changes
  useEffect(() => {
    if (!selectedResumeId) {
      setProfile(null);
      return;
    }

    void loadProfile(selectedResumeId);
  }, [selectedResumeId, loadProfile]);

  // --------------------------------------------------
  // Listen for Resume Upload / Gemini Extraction
  // --------------------------------------------------

  useEffect(() => {
    const handleProfileUpdated = (event: Event) => {
      const customEvent = event as CustomEvent<{
        resumeId: string;
      }>;

      const resumeId = customEvent.detail?.resumeId;

      if (!resumeId) return;

      // Refresh resume list and select processed resume.
      void loadResumes();
      setSelectedResumeId(resumeId);
    };

    const handleResumeUploaded = (event: Event) => {
      const customEvent = event as CustomEvent<{
        resumeId: string;
      }>;

      const resumeId = customEvent.detail?.resumeId;

      if (!resumeId) return;

      void loadResumes();
      setSelectedResumeId(resumeId);
    };

    window.addEventListener("resume:profile-updated", handleProfileUpdated);

    window.addEventListener("resume:uploaded", handleResumeUploaded);
    const handleResumeDeleted = () => void loadResumes();
    window.addEventListener("resume:deleted", handleResumeDeleted);

    return () => {
      window.removeEventListener(
        "resume:profile-updated",
        handleProfileUpdated,
      );

      window.removeEventListener("resume:uploaded", handleResumeUploaded);
      window.removeEventListener("resume:deleted", handleResumeDeleted);
    };
  }, [loadResumes]);

  // --------------------------------------------------
  // Update Profile Fields
  // --------------------------------------------------

  const updateField = <K extends keyof CandidateProfile>(
    field: K,
    value: CandidateProfile[K],
  ) => {
    setProfile((previous) => {
      if (!previous) return previous;

      return {
        ...previous,
        [field]: value,
      };
    });
  };

  // --------------------------------------------------
  // Save Profile
  // --------------------------------------------------

  const saveProfile = async () => {
    if (!profile || !selectedResumeId) {
      setError("Please select a resume first.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const updatedProfile: CandidateProfile = {
        ...profile,

        work_experience: JSON.parse(workExperienceJson),
        education: JSON.parse(educationJson),
        projects: JSON.parse(projectsJson),
        certifications: JSON.parse(certificationsJson),
      };

      // Validate JSON arrays
      if (
        !Array.isArray(updatedProfile.work_experience) ||
        !Array.isArray(updatedProfile.education) ||
        !Array.isArray(updatedProfile.projects) ||
        !Array.isArray(updatedProfile.certifications)
      ) {
        throw new Error("Profile sections must contain JSON arrays.");
      }

      const response = await api.put<ResumeProfileResponse>(
        `/resumes/${selectedResumeId}/profile`,
        updatedProfile,
      );

      const savedProfile = response.data.profile_data;

      setProfile(savedProfile);

      setWorkExperienceJson(formatJson(savedProfile.work_experience));

      setEducationJson(formatJson(savedProfile.education));

      setProjectsJson(formatJson(savedProfile.projects));

      setCertificationsJson(formatJson(savedProfile.certifications));

      setSuccess("Your candidate profile was saved successfully.");
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || "Unable to save your profile.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to save your profile.");
      }
    } finally {
      setSaving(false);
    }
  };

  // --------------------------------------------------
  // Loading Screen
  // --------------------------------------------------

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="300px"
      >
        <CircularProgress />
      </Box>
    );
  }

  // --------------------------------------------------
  // Main UI
  // --------------------------------------------------

  return (
    <Stack spacing={{ xs: 1.5, md: 3 }} className="dashboard-content resume-profile-page">
      {/* Resume Upload Component */}

      <ResumeUploadSection />

      {/* Page Header */}

      <Box
        display="flex"
        alignItems={{ xs: "flex-start", md: "center" }}
        justifyContent="space-between"
        flexWrap="wrap"
        gap={2}
      >
        <Box>
          <Typography variant="h4" fontWeight={800}>
            Resume Profile
          </Typography>

          <Typography color="text.secondary" mt={0.5}>
            Review and manage your AI-extracted candidate information.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={<RefreshCw size={16} />}
          onClick={() => void loadResumes()}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {/* Alerts */}

      {error && <Alert severity="error">{error}</Alert>}

      {success && <Alert severity="success">{success}</Alert>}

      {/* Empty Resume State */}

      {resumes.length === 0 ? (
        <Card>
          <CardContent>
            <Stack alignItems="center" spacing={2} py={5}>
              <Avatar sx={{ width: 64, height: 64 }}>
                <FileUser size={30} />
              </Avatar>

              <Typography variant="h6">No resumes uploaded yet</Typography>

              <Typography color="text.secondary" textAlign="center">
                Upload your resume to get started with AI-powered profile
                extraction.
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Resume Selector */}

          <Card>
            <CardContent>
              <FormControl fullWidth>
                <InputLabel>Select Resume</InputLabel>

                <Select
                  value={selectedResumeId}
                  label="Select Resume"
                  onChange={(event) => {
                    setSelectedResumeId(event.target.value);
                  }}
                >
                  {resumes.map((resume) => (
                    <MenuItem key={resume.id} value={resume.id}>
                      {resume.original_filename} — {resume.parsing_status}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </CardContent>
          </Card>

          {/* Profile Loading */}

          {profileLoading ? (
            <Card>
              <CardContent>
                <Stack alignItems="center" spacing={2} py={5}>
                  <CircularProgress />

                  <Typography color="text.secondary">
                    Loading candidate profile...
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          ) : !profile ? (
            /* No Profile State */

            <Card>
              <CardContent>
                <Stack alignItems="center" spacing={2} py={5}>
                  <Avatar
                    sx={{
                      width: 64,
                      height: 64,
                      bgcolor: "primary.main",
                    }}
                  >
                    <Sparkles size={30} />
                  </Avatar>

                  <Typography variant="h6">
                    No AI Profile Generated Yet
                  </Typography>

                  <Typography color="text.secondary" textAlign="center">
                    Your resume has been uploaded, but the candidate profile has
                    not been generated. Use the Extract Profile button above to
                    analyze your resume with Gemini.
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Personal Information */}

              <Card>
                <CardContent>
                  <Stack direction="row" alignItems="center" spacing={2}>
                    <Avatar
                      sx={{
                        width: 52,
                        height: 52,
                      }}
                    >
                      <FileUser />
                    </Avatar>

                    <Box flex={1}>
                      <Typography variant="h6" fontWeight={750}>
                        {profile.full_name || "Candidate Profile"}
                      </Typography>

                      <Typography color="text.secondary" variant="body2">
                        {profile.professional_title ||
                          "Add your professional title"}
                      </Typography>
                    </Box>

                    <Sparkles size={22} />
                  </Stack>

                  <Divider sx={{ my: 3 }} />

                  <Typography variant="h6" mb={2}>
                    Personal Information
                  </Typography>

                  <Box
                    display="grid"
                    gridTemplateColumns={{
                      xs: "1fr",
                      md: "1fr 1fr",
                    }}
                    gap={2}
                  >
                    <TextField
                      label="Full name"
                      value={profile.full_name ?? ""}
                      onChange={(e) => updateField("full_name", e.target.value)}
                      fullWidth
                    />

                    <TextField
                      label="Email"
                      value={profile.email ?? ""}
                      onChange={(e) => updateField("email", e.target.value)}
                      fullWidth
                    />

                    <TextField
                      label="Phone"
                      value={profile.phone ?? ""}
                      onChange={(e) => updateField("phone", e.target.value)}
                      fullWidth
                    />

                    <TextField
                      label="Location"
                      value={profile.location ?? ""}
                      onChange={(e) => updateField("location", e.target.value)}
                      fullWidth
                    />

                    <TextField
                      label="Professional title"
                      value={profile.professional_title ?? ""}
                      onChange={(e) =>
                        updateField("professional_title", e.target.value)
                      }
                      fullWidth
                    />

                    <TextField
                      label="Total experience (years)"
                      type="number"
                      slotProps={{
                        htmlInput: {
                          min: 0,
                          step: 0.5,
                        },
                      }}
                      value={profile.total_experience_years ?? ""}
                      onChange={(e) =>
                        updateField(
                          "total_experience_years",
                          e.target.value === "" ? null : Number(e.target.value),
                        )
                      }
                      fullWidth
                    />
                  </Box>

                  <TextField
                    label="Professional summary"
                    value={profile.professional_summary ?? ""}
                    onChange={(e) =>
                      updateField("professional_summary", e.target.value)
                    }
                    multiline
                    minRows={4}
                    fullWidth
                    sx={{ mt: 2 }}
                  />
                </CardContent>
              </Card>

              {/* Skills */}

              <Card>
                <CardContent>
                  <Typography variant="h6" mb={2}>
                    Skills
                  </Typography>

                  <TextField
                    label="Technical skills"
                    helperText="Separate skills with commas."
                    value={profile.technical_skills.join(", ")}
                    onChange={(e) =>
                      updateField(
                        "technical_skills",
                        e.target.value
                          .split(",")
                          .map((skill) => skill.trim())
                          .filter(Boolean),
                      )
                    }
                    fullWidth
                    multiline
                    minRows={2}
                  />

                  <TextField
                    label="Soft skills"
                    helperText="Separate skills with commas."
                    value={profile.soft_skills.join(", ")}
                    onChange={(e) =>
                      updateField(
                        "soft_skills",
                        e.target.value
                          .split(",")
                          .map((skill) => skill.trim())
                          .filter(Boolean),
                      )
                    }
                    fullWidth
                    multiline
                    minRows={2}
                    sx={{ mt: 2 }}
                  />
                </CardContent>
              </Card>

              {/* Work Experience */}

              <Card>
                <CardContent>
                  <Typography variant="h6" mb={1}>
                    Work Experience
                  </Typography>

                  <Typography variant="caption" color="text.secondary">
                    Edit as a JSON array. Each item should contain company,
                    designation, start_date, end_date and responsibilities.
                  </Typography>

                  <TextField
                    value={workExperienceJson}
                    onChange={(e) => setWorkExperienceJson(e.target.value)}
                    multiline
                    minRows={7}
                    fullWidth
                    sx={{ mt: 2 }}
                  />
                </CardContent>
              </Card>

              {/* Education */}

              <Card>
                <CardContent>
                  <Typography variant="h6" mb={1}>
                    Education
                  </Typography>

                  <TextField
                    value={educationJson}
                    onChange={(e) => setEducationJson(e.target.value)}
                    multiline
                    minRows={5}
                    fullWidth
                  />
                </CardContent>
              </Card>

              {/* Projects */}

              <Card>
                <CardContent>
                  <Typography variant="h6" mb={1}>
                    Projects
                  </Typography>

                  <TextField
                    value={projectsJson}
                    onChange={(e) => setProjectsJson(e.target.value)}
                    multiline
                    minRows={6}
                    fullWidth
                  />
                </CardContent>
              </Card>

              {/* Certifications */}

              <Card>
                <CardContent>
                  <Typography variant="h6" mb={1}>
                    Certifications
                  </Typography>

                  <TextField
                    value={certificationsJson}
                    onChange={(e) => setCertificationsJson(e.target.value)}
                    multiline
                    minRows={4}
                    fullWidth
                  />
                </CardContent>
              </Card>

              {/* Save Profile */}

              <Box display="flex" justifyContent="flex-end">
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<Save size={17} />}
                  onClick={() => void saveProfile()}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Profile"}
                </Button>
              </Box>
            </>
          )}
        </>
      )}
    </Stack>
  );
}
