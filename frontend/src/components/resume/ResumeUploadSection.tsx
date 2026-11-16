import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import { CloudUpload, FileText, RefreshCw, Sparkles } from "lucide-react";
import CollectionStatus from "./CollectionStatus";

import {
  extractResumeProfile,
  getResumes,
  parseResume,
  uploadResume,
  selectPrimaryResume,
  type Resume,
} from "../../api/resumeApi";

export default function ResumeUploadSection() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadResumes = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getResumes();
      setResumes(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to load your resumes.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadResumes();
  }, []);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setError("");
    setMessage("");

    const extension = file.name.split(".").pop()?.toLowerCase();

    if (!["pdf", "docx"].includes(extension ?? "")) {
      setError("Only PDF and DOCX files are supported.");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("File size must not exceed 5 MB.");
      event.target.value = "";
      return;
    }

    try {
      setUploading(true);

      const uploadedResume = await uploadResume(file);

      window.dispatchEvent(
        new CustomEvent("resume:uploaded", {
          detail: {
            resumeId: uploadedResume.id,
          },
        }),
      );

      setMessage("Resume uploaded successfully.");
      await loadResumes();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Resume upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const handleProcess = async (resume: Resume) => {
    try {
      setError("");
      setSuccess("");

      setProcessingId(resume.id);

      // Step 1: Extract text from PDF/DOCX
      await parseResume(resume.id);

      // Step 2: Extract candidate profile using Gemini
      await extractResumeProfile(resume.id);

      // Step 3: Notify ResumeProfilePage
      window.dispatchEvent(
        new CustomEvent("resume:profile-updated", {
          detail: {
            resumeId: resume.id,
          },
        }),
      );

      setSuccess("Profile generated. Job collection is queued for your primary resume; only scores above 80 are saved.");
      await loadResumes();
    } catch (error: unknown) {
      console.error("Resume processing failed:", error);

      setError("Unable to process resume. Please try again.");
    } finally {
      setProcessingId(null);
    }
  };

  const getStatusColor = (
    status: Resume["parsing_status"],
  ): "success" | "warning" | "error" | "default" => {
    switch (status) {
      case "parsed":
        return "success";
      case "processing":
        return "warning";
      case "failed":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <Stack spacing={3}>
      <CollectionStatus />
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <CloudUpload size={22} />
              <Typography variant="h6" fontWeight={700}>
                Upload Resume
              </Typography>
            </Stack>

            <Typography variant="body2" color="text.secondary">
              Upload your resume to extract your professional details and match
              your skills with relevant jobs.
            </Typography>

            <Box
              sx={{
                border: "1px dashed",
                borderColor: "divider",
                borderRadius: 2,
                p: 4,
                textAlign: "center",
              }}
            >
              <FileText size={36} />

              <Typography sx={{ mt: 1 }}>Select your resume file</Typography>

              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                sx={{ mb: 2 }}
              >
                PDF or DOCX · Maximum file size 5 MB
              </Typography>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                hidden
                onChange={handleUpload}
              />

              <Button
                variant="contained"
                startIcon={
                  uploading ? (
                    <CircularProgress size={18} color="inherit" />
                  ) : (
                    <CloudUpload size={18} />
                  )
                }
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? "Uploading..." : "Choose Resume"}
              </Button>
            </Box>

            {message && <Alert severity="success">{message}</Alert>}
            {error && <Alert severity="error">{error}</Alert>}
            {success && (
              <Alert severity="success" sx={{ mb: 2 }}>
                {success}
              </Alert>
            )}
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: 2 }}
          >
            <Typography variant="h6" fontWeight={700}>
              Your Resumes
            </Typography>

            <Button
              size="small"
              startIcon={<RefreshCw size={16} />}
              onClick={loadResumes}
              disabled={loading}
            >
              Refresh
            </Button>
          </Stack>

          <Divider sx={{ mb: 2 }} />

          {loading ? (
            <Box display="flex" justifyContent="center" py={3}>
              <CircularProgress />
            </Box>
          ) : resumes.length === 0 ? (
            <Typography color="text.secondary">
              No resumes uploaded yet. Upload your first resume above.
            </Typography>
          ) : (
            <Stack spacing={2}>
              {resumes.map((resume) => (
                <Box
                  key={resume.id}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 2,
                    flexWrap: "wrap",
                    p: 2,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                  }}
                >
                  <Box>
                    <Typography fontWeight={600}>
                      {resume.original_filename}
                    </Typography>

                    <Typography variant="caption" color="text.secondary">
                      {(resume.file_size_bytes / 1024).toFixed(1)} KB
                    </Typography>

                    <Box sx={{ mt: 1 }}>
                      <Chip
                        size="small"
                        label={resume.parsing_status}
                        color={getStatusColor(resume.parsing_status)}
                      />
                    </Box>
                  </Box>

                  <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    disabled={resume.is_primary || processingId !== null}
                    onClick={async () => {
                      try {
                        await selectPrimaryResume(resume.id);
                        await loadResumes();
                      } catch {
                        setError("Unable to select primary resume.");
                      }
                    }}
                  >
                    {resume.is_primary ? "Primary resume" : "Use as primary"}
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<Sparkles size={16} />}
                    disabled={
                      processingId === resume.id ||
                      resume.parsing_status === "processing"
                    }
                    onClick={() => handleProcess(resume)}
                  >
                    {processingId === resume.id
                      ? "Processing..."
                      : "Extract Profile"}
                  </Button>
                  </Stack>
                </Box>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
