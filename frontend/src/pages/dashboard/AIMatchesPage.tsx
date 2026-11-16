import InfiniteScroll from "../../components/InfiniteScroll";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";

import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  RefreshCw,
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
import CollectionSummary from "../../components/matches/CollectionSummary";
import MatchDetailsDialog from "../../components/matches/MatchDetailsDialog";


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


  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const [error, setError] = useState("");
  const [analysisSummary, setAnalysisSummary] =
    useState<AnalyzeAllResponse | null>(null);

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const latestMatchesRequest = useRef(0);

  const loadMatches = useCallback(async (pageNumber = 1) => {
    const requestId = ++latestMatchesRequest.current;
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
      if (requestId !== latestMatchesRequest.current) return;

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
      if (requestId !== latestMatchesRequest.current) return;
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
      if (requestId === latestMatchesRequest.current) {
        setLoading(false);
        setLoadingMore(false);
      }
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

      <CollectionSummary />

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
              {matches.length} results loaded
            </Typography>
          </Box>

          <Box className="matches-result-count">
            <Target size={16} />
            <Typography>{matchedCount} recommended</Typography>
          </Box>
        </Box>

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

        {/* Match cards */}
        {!loading && matches.length > 0 && (
          <Box className="matches-jobs-grid">
            {matches.map((match) => (
              <MatchJobCard
                key={match.id}
                match={match}
                onViewDetails={setSelectedMatch}
                onApplied={(jobId) => {
                  setMatches((items) => items.filter((item) => item.job.id !== jobId));
                  void loadMatches(1);
                }}
              />
            ))}
          </Box>
        )}

        <InfiniteScroll hasMore={hasMore && !loading} loading={loadingMore}
          error={Boolean(error) && hasMore} onLoad={handleLoadMore} />

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
