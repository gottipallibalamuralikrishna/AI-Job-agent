import { api } from "./axios";

export interface Job {
  id: string;
  source_id: string | null;
  external_id: string | null;
  title: string;
  company_name: string;
  company_logo: string | null;
  location: string | null;
  employment_type: string | null;
  work_mode: string | null;
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
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  source_message_url: string | null;
  raw_source_text: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GetJobsParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  source_type?:
    | "telegram"
    | "whatsapp"
    | "career_page"
    | "greenhouse"
    | "lever"
    | "rss"
    | "api"
    | "manual";
}

export const jobsApi = {
  getJobs: async (params: GetJobsParams = {}): Promise<JobListResponse> => {
    const response = await api.get<JobListResponse>("/jobs", {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 12,
        is_active: params.is_active ?? true,
        ...(params.search?.trim() ? { search: params.search.trim() } : {}),
        ...(params.source_type ? { source_type: params.source_type } : {}),
      },
    });

    return response.data;
  },

  getJobById: async (jobId: string): Promise<Job> => {
    const response = await api.get<Job>(`/jobs/${jobId}`);
    return response.data;
  },
};
