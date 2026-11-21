import InfiniteScroll from "../../components/InfiniteScroll";
import usePagedFeed from "../../api/usePagedFeed";
import MarkAppliedButton from "../../components/MarkAppliedButton";
import { useCallback, useEffect, useState } from "react";
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
  InputAdornment,
  IconButton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  Search,
  MapPin,
  BriefcaseBusiness,
  ExternalLink,
  Building2,
  X,
} from "lucide-react";

import { jobsApi, type Job } from "../../api/jobsApi";

const PAGE_SIZE = 12;

function displayCompany(value: string) {
  const name = value?.trim();
  return name && !/^(?:not specified|unknown|n\/a)$/i.test(name) ? name : "Company not listed";
}

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
          {displayCompany(job.company_name)}
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

        {job.source_message_url === "https://himalayas.app/" && (
          <Button href={job.source_message_url} target="_blank" rel="noopener noreferrer" size="small">
            Himalayas
          </Button>
        )}
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
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 400);
    return () => window.clearTimeout(timer);
  }, [search]);
  const fetchPage = useCallback(async (page: number) => {
    const { items, total, total_pages } = await jobsApi.getJobs({
      page, page_size: PAGE_SIZE, search: debouncedSearch, is_active: true,
    });
    return { items, total, hasMore: page < total_pages };
  }, [debouncedSearch]);
  const { items: jobs, total: totalJobs, loading: fetching, error, hasMore, loadMore } = usePagedFeed(fetchPage);
  const loading = fetching && jobs.length === 0;

  return (
    <Box className="dashboard-content all-jobs-page">
      {/* Page header */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        gap={{ xs: 1, sm: 2 }}
        mb={{ xs: 1.5, sm: 3 }}
      >
        <Box>
          <Typography variant="h4" fontWeight={800}>
            Explore Jobs
          </Typography>

          <Typography color="text.secondary" mt={0.7} sx={{ display: { xs: "none", sm: "block" } }}>
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
      <TextField
        fullWidth
        size="small"
        inputProps={{ "aria-label": "Search jobs" }}
        placeholder="Search job title, company or keywords..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search size={19} />
            </InputAdornment>
          ),
          endAdornment: search ? (
            <InputAdornment position="end">
              <IconButton size="small" aria-label="Clear search" onClick={() => setSearch("")}>
                <X size={17} />
              </IconButton>
            </InputAdornment>
          ) : undefined,
        }}
      />

      {/* Results heading */}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        flexWrap="wrap"
        mt={{ xs: 2, sm: 3 }}
        mb={{ xs: 1, sm: 2 }}
      >
        <Typography fontWeight={750}>Available opportunities</Typography>

        <Typography variant="caption" color="text.secondary">
          {jobs.length} jobs loaded
        </Typography>
      </Stack>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Unable to load jobs.
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
              <Card key={job.id} variant="outlined" className="job-listing-card">
                <CardContent className="job-listing-content">
                  <Stack direction="row" alignItems="flex-start" gap={1.5}>
                    <Box className="company-logo">
                      {job.company_logo ? <img src={job.company_logo} alt="" /> : <Building2 size={19} aria-hidden="true" />}
                    </Box>
                    <Box minWidth={0}>
                      <Typography variant="h6" component="h3" className="job-title">{job.title}</Typography>
                      <Typography variant="body2" color="text.secondary">{displayCompany(job.company_name)}</Typography>
                    </Box>
                  </Stack>
                  <Stack direction="row" gap={1.25} flexWrap="wrap" color="text.secondary">
                    {job.location && <Stack direction="row" gap={0.5} alignItems="center">
                      <MapPin size={14} aria-hidden="true" /><Typography variant="caption">{job.location}</Typography>
                    </Stack>}
                    {[job.work_mode, job.employment_type?.replaceAll("_", " ")].filter(Boolean).map((value) => (
                      <Typography key={value} variant="caption" sx={{ textTransform: "capitalize" }}>{value}</Typography>
                    ))}
                  </Stack>
                  {salary && <Typography variant="body2" color="success.main">{salary}</Typography>}
                  {job.description && <Typography variant="body2" color="text.secondary" className="job-listing-description">
                    {stripHtml(job.description)}
                  </Typography>}
                  {job.required_skills?.length > 0 && <Stack direction="row" gap={0.75} flexWrap="wrap">
                    {job.required_skills.slice(0, 3).map((skill) => <Chip key={skill} label={skill} size="small" variant="outlined" />)}
                  </Stack>}
                  <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1} sx={{ mt: "auto" }}>
                    <Typography variant="caption" color="text.secondary">{formatDate(job.posted_at || job.created_at)}</Typography>
                    <Button size="small" onClick={() => setSelectedJob(job)}>View details</Button>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}

      <InfiniteScroll hasMore={hasMore} loading={fetching && !loading} error={error} onLoad={loadMore} />

      <JobDetailsDialog
        job={selectedJob}
        onClose={() => setSelectedJob(null)}
      />
    </Box>
  );
}
