import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  AlertCircle,
  ArrowDownWideNarrow,
  BrainCircuit,
  CheckCircle2,
  CircleHelp,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";

import {
  jobMatchesApi,
  type AnalyzeAllResponse,
  type JobMatch,
} from "../../api/jobMatchesApi";

import MatchJobCard from "../../components/matches/MatchJobCard";
import MatchDetailsDialog from "../../components/matches/MatchDetailsDialog";

type DecisionFilter = "all" | "matched" | "not_matched";

const PAGE_SIZE = 100;

function MatchMetric({
  title,
  value,
  description,
  icon: Icon,
  color,
}: {
  title: string;
  value: string | number;
  description: string;
  icon: typeof Target;
  color: string;
}) {
  return (
    <Card className="match-metric-card">
      <CardContent>
        <Box className="match-metric-top">
          <Box
            className="match-metric-icon"
            sx={{ color, backgroundColor: `${color}18` }}
          >
            <Icon size={20} />
          </Box>
        </Box>

        <Typography className="match-metric-value">{value}</Typography>

        <Typography className="match-metric-title">{title}</Typography>

        <Typography className="match-metric-description">
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function AIMatchesPage() {
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);

  const [search, setSearch] = useState("");
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>("all");
  const [minimumScore, setMinimumScore] = useState<number>(0);
  const [sortOrder, setSortOrder] = useState("highest");

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const [error, setError] = useState("");
  const [analysisSummary, setAnalysisSummary] =
    useState<AnalyzeAllResponse | null>(null);

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const loadMatches = useCallback(async (pageNumber = 1) => {
    try {
      if (pageNumber === 1) {
        setLoading(true);
      } else {
        setLoadingMore(true);
      }

      setError("");

      const data = await jobMatchesApi.getMatches({
        page: pageNumber,
        page_size: PAGE_SIZE,
      });

      if (pageNumber === 1) {
        setMatches(data);
      } else {
        setMatches((previous) => {
          const existingIds = new Set(previous.map((item) => item.id));

          return [
            ...previous,
            ...data.filter((item) => !existingIds.has(item.id)),
          ];
        });
      }

      setPage(pageNumber);
      setHasMore(data.length === PAGE_SIZE);
    } catch (err: unknown) {
      let message = "Unable to load AI matches.";

      if (typeof err === "object" && err !== null && "response" in err) {
        const response = (
          err as {
            response?: {
              data?: { detail?: string };
            };
          }
        ).response;

        message = response?.data?.detail ?? message;
      }

      setError(message);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    void loadMatches(1);
  }, [loadMatches]);

  const handleAnalyzeAll = async () => {
    try {
      setAnalyzing(true);
      setError("");
      setAnalysisSummary(null);

      const result = await jobMatchesApi.analyzeAll(100);

      setAnalysisSummary(result);

      // Refresh the first page after analysis.
      await loadMatches(1);
    } catch (err: unknown) {
      let message = "Unable to analyze jobs.";

      if (typeof err === "object" && err !== null && "response" in err) {
        const response = (
          err as {
            response?: {
              data?: { detail?: string };
            };
          }
        ).response;

        message = response?.data?.detail ?? message;
      }

      setError(message);
    } finally {
      setAnalyzing(false);
    }
  };

  const visibleMatches = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    let result = matches.filter((match) => {
      const matchesSearch =
        !normalizedSearch ||
        match.job.title.toLowerCase().includes(normalizedSearch) ||
        match.job.company_name.toLowerCase().includes(normalizedSearch) ||
        (match.job.location ?? "").toLowerCase().includes(normalizedSearch);

      const matchesDecision =
        decisionFilter === "all" || match.decision === decisionFilter;

      const matchesScore = match.match_score >= minimumScore;

      return matchesSearch && matchesDecision && matchesScore;
    });

    result = [...result].sort((a, b) => {
      return sortOrder === "highest"
        ? b.match_score - a.match_score
        : a.match_score - b.match_score;
    });

    return result;
  }, [matches, search, decisionFilter, minimumScore, sortOrder]);

  const matchedCount = matches.filter(
    (item) => item.decision === "matched",
  ).length;

  const notMatchedCount = matches.filter(
    (item) => item.decision === "not_matched",
  ).length;

  const averageScore = matches.length
    ? matches.reduce((total, item) => total + item.match_score, 0) /
      matches.length
    : 0;

  const highMatchCount = matches.filter(
    (item) => item.decision === "matched" && item.match_score >= 85,
  ).length;

  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      void loadMatches(page + 1);
    }
  };

  return (
    <Box className="ai-matches-page">
      {/* Page heading */}
      <Box className="matches-page-heading">
        <Box>
          <Typography className="matches-eyebrow">
            RESUME-POWERED JOB DISCOVERY
          </Typography>

          <Typography className="matches-page-title">AI Matches</Typography>

          <Typography className="matches-page-subtitle">
            Discover how well each opportunity aligns with your skills,
            experience, and professional profile.
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button
            variant="outlined"
            startIcon={<RefreshCw size={16} />}
            onClick={() => void loadMatches(1)}
            disabled={loading || analyzing}
          >
            Refresh
          </Button>

          <Button
            variant="contained"
            startIcon={
              analyzing ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <Sparkles size={16} />
              )
            }
            onClick={() => void handleAnalyzeAll()}
            disabled={analyzing || loading}
            className="analyze-all-button"
          >
            {analyzing ? "Analyzing jobs..." : "Analyze all jobs"}
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert
          severity="error"
          onClose={() => setError("")}
          className="matches-alert"
        >
          {error}
        </Alert>
      )}

      {analysisSummary && (
        <Alert
          severity={analysisSummary.failed > 0 ? "warning" : "success"}
          className="matches-alert"
        >
          <strong>{analysisSummary.message}</strong>
          <br />
          Processed: {analysisSummary.processed} / {analysisSummary.total_jobs}
          {" · "}
          Matched: {analysisSummary.matched}
          {" · "}
          Not matched: {analysisSummary.not_matched}
          {" · "}
          Failed: {analysisSummary.failed}
        </Alert>
      )}

      {/* Matching summary */}
      <Box className="matches-section">
        <Box className="matches-section-heading">
          <Box>
            <Typography className="matches-section-title">
              Matching overview
            </Typography>

            <Typography className="matches-section-description">
              Summary of the match records currently loaded.
            </Typography>
          </Box>
        </Box>

        <Box className="match-metrics-grid">
          <MatchMetric
            title="Analyzed jobs"
            value={matches.length}
            description="Loaded match records"
            icon={BrainCircuit}
            color="#a99aff"
          />

          <MatchMetric
            title="Strong matches"
            value={highMatchCount}
            description="Matched jobs scoring 85%+"
            icon={CheckCircle2}
            color="#65d6a5"
          />

          <MatchMetric
            title="Average score"
            value={`${averageScore.toFixed(1)}%`}
            description="Average of loaded results"
            icon={TrendingUp}
            color="#36cfc9"
          />

          <MatchMetric
            title="Not matched"
            value={notMatchedCount}
            description="Jobs below match criteria"
            icon={AlertCircle}
            color="#f5b95f"
          />
        </Box>
      </Box>

      {/* Results */}
      <Box className="matches-section">
        <Box className="matches-results-heading">
          <Box>
            <Typography className="matches-section-title">
              Matching opportunities
            </Typography>

            <Typography className="matches-section-description">
              {visibleMatches.length} results displayed from {matches.length}{" "}
              loaded records
            </Typography>
          </Box>

          <Box className="matches-result-count">
            <Target size={16} />
            <Typography>{matchedCount} recommended</Typography>
          </Box>
        </Box>

        {/* Filters */}
        <Card className="matches-filter-card">
          <CardContent className="matches-filter-content">
            <TextField
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search job title, company or location..."
              size="small"
              className="matches-search-field"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={17} />
                  </InputAdornment>
                ),
              }}
            />

            <FormControl size="small" className="matches-filter-select">
              <InputLabel>Match status</InputLabel>

              <Select
                value={decisionFilter}
                label="Match status"
                onChange={(event) =>
                  setDecisionFilter(event.target.value as DecisionFilter)
                }
              >
                <MenuItem value="all">All results</MenuItem>
                <MenuItem value="matched">Matched ({matchedCount})</MenuItem>
                <MenuItem value="not_matched">
                  Not matched ({notMatchedCount})
                </MenuItem>
              </Select>
            </FormControl>

            <FormControl size="small" className="matches-filter-select">
              <InputLabel>Minimum score</InputLabel>

              <Select
                value={minimumScore}
                label="Minimum score"
                onChange={(event) =>
                  setMinimumScore(Number(event.target.value))
                }
              >
                <MenuItem value={0}>Any score</MenuItem>
                <MenuItem value={50}>50% or higher</MenuItem>
                <MenuItem value={70}>70% or higher</MenuItem>
                <MenuItem value={85}>85% or higher</MenuItem>
                <MenuItem value={90}>90% or higher</MenuItem>
              </Select>
            </FormControl>

            <FormControl size="small" className="matches-filter-select">
              <InputLabel>Sort by score</InputLabel>

              <Select
                value={sortOrder}
                label="Sort by score"
                onChange={(event) => setSortOrder(event.target.value)}
                startAdornment={
                  <InputAdornment position="start">
                    <ArrowDownWideNarrow size={15} />
                  </InputAdornment>
                }
              >
                <MenuItem value="highest">Highest first</MenuItem>
                <MenuItem value="lowest">Lowest first</MenuItem>
              </Select>
            </FormControl>
          </CardContent>
        </Card>

        {/* Loading */}
        {loading && (
          <Box className="matches-loading">
            <CircularProgress />
            <Typography color="text.secondary">
              Loading your AI matches...
            </Typography>
          </Box>
        )}

        {/* Empty state */}
        {!loading && matches.length === 0 && !error && (
          <Card className="matches-empty-card">
            <CardContent className="matches-empty-content">
              <Box className="matches-empty-icon">
                <Sparkles size={29} />
              </Box>

              <Typography variant="h6" fontWeight={750}>
                Your matching opportunities are waiting
              </Typography>

              <Typography color="text.secondary" textAlign="center">
                Analyze your collected jobs against your parsed resume to
                discover compatible opportunities.
              </Typography>

              <Button
                variant="contained"
                startIcon={<Sparkles size={16} />}
                onClick={() => void handleAnalyzeAll()}
                disabled={analyzing}
              >
                {analyzing ? "Analyzing..." : "Start AI matching"}
              </Button>

              <Typography variant="caption" color="text.secondary">
                You need a parsed resume profile with technical skills before
                matching can begin.
              </Typography>
            </CardContent>
          </Card>
        )}

        {/* No filtered results */}
        {!loading && matches.length > 0 && visibleMatches.length === 0 && (
          <Card className="matches-empty-card">
            <CardContent className="matches-empty-content">
              <CircleHelp size={30} color="#9d8cff" />

              <Typography fontWeight={700}>
                No matching results found
              </Typography>

              <Typography color="text.secondary" variant="body2">
                Try changing your search or filters.
              </Typography>

              <Button
                variant="outlined"
                onClick={() => {
                  setSearch("");
                  setDecisionFilter("all");
                  setMinimumScore(0);
                }}
              >
                Clear filters
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Match cards */}
        {!loading && visibleMatches.length > 0 && (
          <Box className="matches-jobs-grid">
            {visibleMatches.map((match) => (
              <MatchJobCard
                key={match.id}
                match={match}
                onViewDetails={setSelectedMatch}
              />
            ))}
          </Box>
        )}

        {hasMore && !loading && (
          <Box className="matches-load-more">
            <Button
              variant="outlined"
              onClick={handleLoadMore}
              disabled={loadingMore}
              startIcon={
                loadingMore ? (
                  <CircularProgress size={15} />
                ) : (
                  <ArrowDownWideNarrow size={16} />
                )
              }
            >
              {loadingMore ? "Loading..." : "Load more matches"}
            </Button>
          </Box>
        )}

        {!hasMore && matches.length > 0 && (
          <Typography className="matches-end-message">
            You've reached the end of the loaded match results.
          </Typography>
        )}
      </Box>

      <MatchDetailsDialog
        match={selectedMatch}
        onClose={() => setSelectedMatch(null)}
      />
    </Box>
  );
}
