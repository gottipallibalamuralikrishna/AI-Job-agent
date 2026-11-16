import MarkAppliedButton from "../../components/MarkAppliedButton";
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  InputAdornment,
  Pagination,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  Search,
  MapPin,
  BriefcaseBusiness,
  ExternalLink,
  Clock3,
  Building2,
  SlidersHorizontal,
} from "lucide-react";

import { jobsApi, type Job } from "../../api/jobsApi";

const PAGE_SIZE = 12;

function stripHtml(value: string | null): string {
  if (!value) return "";

  return value
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function formatDate(value: string | null): string {
  if (!value) return "Recently added";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Recently added";
  }

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatSalary(job: Job): string | null {
  if (job.salary_min == null && job.salary_max == null) {
    return null;
  }

  const currency = job.salary_currency || "USD";
  const period = job.salary_period ? ` / ${job.salary_period}` : "";

  const format = (amount: number) =>
    new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 0,
    }).format(amount);

  if (job.salary_min != null && job.salary_max != null) {
    return `${currency} ${format(job.salary_min)} - ${format(job.salary_max)}${period}`;
  }

  const amount = job.salary_min ?? job.salary_max;

  return `${currency} ${format(amount!)}${period}`;
}

function JobDetailsDialog({
  job,
  onClose,
}: {
  job: Job | null;
  onClose: () => void;
}) {
  if (!job) return null;

  const description = stripHtml(job.description);

  return (
    <Dialog
      open={Boolean(job)}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      PaperProps={{
        sx: {
          bgcolor: "#111827",
          border: "1px solid #273149",
          borderRadius: 3,
        },
      }}
    >
      <DialogTitle>
        <Typography variant="h5" fontWeight={800}>
          {job.title}
        </Typography>

        <Typography color="text.secondary" mt={1}>
          {job.company_name}
        </Typography>
      </DialogTitle>

      <DialogContent dividers sx={{ borderColor: "#273149" }}>
        <Stack direction="row" flexWrap="wrap" gap={1} mb={3}>
          {job.location && (
            <Chip icon={<MapPin size={14} />} label={job.location} />
          )}

          <MarkAppliedButton jobId={job.id} />
          {job.work_mode && <Chip label={job.work_mode} />}
          {job.remote_eligible_locations?.length > 0 && <Chip label={`Applicant locations: ${job.remote_eligible_locations.join(", ")}`} />}

          {job.employment_type && <Chip label={job.employment_type} />}
        </Stack>

        <Typography fontWeight={750} mb={1}>
          Job description
        </Typography>

        <Typography
          color="text.secondary"
          sx={{
            whiteSpace: "pre-line",
            lineHeight: 1.8,
            overflowWrap: "anywhere",
          }}
        >
          {description || "No job description available."}
        </Typography>

        {job.required_skills?.length > 0 && (
          <>
            <Divider sx={{ my: 3, borderColor: "#273149" }} />

            <Typography fontWeight={750} mb={1.5}>
              Required skills
            </Typography>

            <Stack direction="row" flexWrap="wrap" gap={1}>
              {job.required_skills.map((skill) => (
                <Chip key={skill} label={skill} color="primary" />
              ))}
            </Stack>
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2.5 }}>
        <Button onClick={onClose} color="inherit">
          Close
        </Button>

        {job.application_url && (
          <Button
            variant="contained"
            endIcon={<ExternalLink size={16} />}
            onClick={() =>
              window.open(job.application_url!, "_blank", "noopener,noreferrer")
            }
          >
            Apply Now
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

export default function AllJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Debounce search input.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
      setPage(1);
    }, 400);

    return () => window.clearTimeout(timer);
  }, [search]);

  // Fetch jobs whenever the page or search changes.
  useEffect(() => {
    let cancelled = false;

    const fetchJobs = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await jobsApi.getJobs({
          page,
          page_size: PAGE_SIZE,
          search: debouncedSearch,
          is_active: true,
        });

        if (cancelled) return;

        setJobs(response.items ?? []);
        setTotalJobs(response.total ?? 0);
        setTotalPages(Math.max(response.total_pages ?? 1, 1));
      } catch (err: any) {
        if (cancelled) return;

        setError(
          err.response?.data?.detail ||
            "Unable to load jobs. Please try again.",
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchJobs();

    return () => {
      cancelled = true;
    };
  }, [page, debouncedSearch]);

  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    value: number,
  ) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <Box className="dashboard-content all-jobs-page">
      {/* Page header */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        gap={2}
        mb={3}
      >
        <Box>
          <Typography variant="h4" fontWeight={800}>
            Explore Jobs
          </Typography>

          <Typography color="text.secondary" mt={0.7}>
            Discover opportunities collected from your job sources.
          </Typography>
        </Box>

        <Chip
          icon={<BriefcaseBusiness size={15} />}
          label={`${totalJobs.toLocaleString()} active jobs`}
          color="primary"
          variant="outlined"
        />
      </Stack>

      {/* Search */}
      <Card className="panel-card job-search-panel">
        <CardContent>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems="center"
            gap={2}
          >
            <TextField
              fullWidth
              placeholder="Search job title, company or keywords..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={19} />
                  </InputAdornment>
                ),
              }}
            />

            <Button
              variant="outlined"
              color="inherit"
              startIcon={<SlidersHorizontal size={17} />}
              onClick={() => {
                setSearch("");
                setPage(1);
              }}
              sx={{ minWidth: 125, height: 54 }}
            >
              Clear
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Results heading */}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        mt={3}
        mb={2}
      >
        <Typography fontWeight={750}>Available opportunities</Typography>

        <Typography variant="caption" color="text.secondary">
          Page {page} of {totalPages}
        </Typography>
      </Stack>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Loading */}
      {loading && (
        <Box className="jobs-loading">
          <CircularProgress color="primary" />
          <Typography color="text.secondary" mt={2}>
            Loading opportunities...
          </Typography>
        </Box>
      )}

      {/* Empty state */}
      {!loading && !error && jobs.length === 0 && (
        <Card className="panel-card">
          <CardContent className="empty-panel">
            <BriefcaseBusiness size={35} color="#8b7cff" />

            <Typography fontWeight={750}>No jobs found</Typography>

            <Typography color="text.secondary" variant="body2">
              Try another search term.
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Job cards */}
      {!loading && jobs.length > 0 && (
        <Box className="jobs-grid">
          {jobs.map((job) => {
            const salary = formatSalary(job);

            return (
              <Card key={job.id} className="job-card panel-card">
                <CardContent className="job-card-content">
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="flex-start"
                    gap={1}
                  >
                    <Box className="company-logo">
                      {job.company_logo ? (
                        <img
                          src={job.company_logo}
                          alt={`${job.company_name} logo`}
                        />
                      ) : (
                        <Building2 size={22} />
                      )}
                    </Box>

                    <Chip
                      size="small"
                      label={job.work_mode || "Not specified"}
                      variant="outlined"
                    />
                  </Stack>

                  <Box mt={2}>
                    <Typography
                      variant="h6"
                      fontWeight={750}
                      className="job-title"
                    >
                      {job.title}
                    </Typography>

                    <Typography color="text.secondary" variant="body2" mt={0.5}>
                      {job.company_name}
                    </Typography>
                  </Box>

                  <Stack direction="row" flexWrap="wrap" gap={1.5} mt={2}>
                    {job.location && (
                      <Stack direction="row" alignItems="center" gap={0.5}>
                        <MapPin size={14} />
                        <Typography variant="caption" color="text.secondary">
                          {job.location}
                        </Typography>
                      </Stack>
                    )}

                    {job.employment_type && (
                      <Stack direction="row" alignItems="center" gap={0.5}>
                        <BriefcaseBusiness size={14} />
                        <Typography variant="caption" color="text.secondary">
                          {job.employment_type}
                        </Typography>
                      </Stack>
                    )}
                  </Stack>

                  {salary && (
                    <Typography
                      color="success.main"
                      variant="body2"
                      fontWeight={700}
                      mt={1.5}
                    >
                      {salary}
                    </Typography>
                  )}

                  <Typography
                    color="text.secondary"
                    variant="body2"
                    className="job-description"
                    mt={2}
                  >
                    {stripHtml(job.description) || "No description available."}
                  </Typography>

                  {job.required_skills?.length > 0 && (
                    <Stack direction="row" flexWrap="wrap" gap={0.7} mt={2}>
                      {job.required_skills.slice(0, 4).map((skill) => (
                        <Chip
                          key={skill}
                          label={skill}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                    </Stack>
                  )}

                  <Box flex={1} />

                  <Divider sx={{ my: 2, borderColor: "#273149" }} />

                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    gap={1}
                  >
                    <Stack direction="row" alignItems="center" gap={0.6}>
                      <Clock3 size={14} />
                      <Typography variant="caption" color="text.secondary">
                        {formatDate(job.posted_at || job.created_at)}
                      </Typography>
                    </Stack>

                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => setSelectedJob(job)}
                    >
                      View Details
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <Stack alignItems="center" mt={4}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            shape="rounded"
          />
        </Stack>
      )}

      <JobDetailsDialog
        job={selectedJob}
        onClose={() => setSelectedJob(null)}
      />
    </Box>
  );
}
