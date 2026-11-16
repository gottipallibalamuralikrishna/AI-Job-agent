import { api } from "./axios";

export interface MatchedJob {
  id: string;
  title: string;
  company_name: string;
  company_logo: string | null;
  location: string | null;
  employment_type: string | null;
  work_mode: string | null;
  remote_eligible_locations: string[];
  experience_min: number | null;
  experience_max: number | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  salary_period: string | null;
  description: string | null;
  required_skills: string[];
  application_url: string | null;
  posted_at: string | null;
  is_active: boolean;
}

export interface JobMatch {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string;

  job: MatchedJob;

  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  candidate_skills: string[];
  job_skills: string[];

  matched_skill_count: number;
  total_job_skills: number;

  decision: "matched" | "not_matched";

  role_family: string | null;
  candidate_role_family: string | null;

  role_match_score: number;
  skill_match_score: number;
  experience_match_score: number;
  responsibility_match_score: number;

  required_skills: string[];
  preferred_skills: string[];
  missing_preferred_skills: string[];

  required_experience_years: number | null;
  candidate_experience_years: number;

  matched_responsibility_categories: string[];
  rejection_reasons: string[];
  match_explanation: string | null;

  created_at: string;
  updated_at: string;
}

export interface AnalyzeAllResponse {
  resume_id: string;
  total_jobs: number;
  processed: number;
  matched: number;
  not_matched: number;
  failed: number;
  batch_size: number;
  message: string;
}

export interface GetMatchesParams {
  page?: number;
  page_size?: number;
  matched_only?: boolean;
}

export const jobMatchesApi = {
  getMatches: async (params: GetMatchesParams = {}): Promise<JobMatch[]> => {
    const response = await api.get<JobMatch[]>("/job-matches", {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 100,
        ...(params.matched_only !== undefined
          ? { matched_only: params.matched_only }
          : {}),
      },
    });

    return response.data;
  },

  getMatchById: async (matchId: string): Promise<JobMatch> => {
    const response = await api.get<JobMatch>(`/job-matches/${matchId}`);

    return response.data;
  },

  analyzeAll: async (batchSize = 100): Promise<AnalyzeAllResponse> => {
    const response = await api.post<AnalyzeAllResponse>(
      "/job-matches/analyze-all",
      null,
      {
        params: { batch_size: batchSize },
      },
    );

    return response.data;
  },

  analyzeJob: async (jobId: string): Promise<JobMatch> => {
    const response = await api.post<JobMatch>(`/job-matches/analyze/${jobId}`);

    return response.data;
  },
};
