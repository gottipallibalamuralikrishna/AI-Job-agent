import { api } from "./axios";

export type ContactType =
  | "email"
  | "phone"
  | "application_url"
  | "linkedin"
  | "telegram"
  | "website";

export type SourceType =
  | "telegram"
  | "whatsapp"
  | "career_page"
  | "greenhouse"
  | "lever"
  | "rss"
  | "api"
  | "manual";

export interface ContactJobSummary {
  id: string;
  title: string;
  company_name: string;
  location: string | null;
  application_url: string | null;
  source_id: string;
}

export interface RecruiterContact {
  id: string;
  job_id: string;
  contact_type: ContactType;
  contact_value: string;
  contact_name: string | null;
  is_primary: boolean;
  is_verified: boolean;
  created_at: string;
  job: ContactJobSummary;
}

export interface RecruiterContactListResponse {
  items: RecruiterContact[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RecruiterContactStats {
  total_contacts: number;
  total_emails: number;
  total_phones: number;
  total_linkedin: number;
  total_telegram: number;
  total_websites: number;
  total_application_urls: number;
  jobs_with_contacts: number;
}

export interface GetRecruiterContactsParams {
  page?: number;
  page_size?: number;
  search?: string;
  contact_type?: ContactType | "";
  source_type?: SourceType | "";
  job_id?: string;
}

export const recruiterContactsApi = {
  getContacts: async (
    params: GetRecruiterContactsParams = {},
  ): Promise<RecruiterContactListResponse> => {
    const response = await api.get<RecruiterContactListResponse>(
      "/recruiter-contacts",
      {
        params: {
          page: params.page ?? 1,
          page_size: params.page_size ?? 10,
          ...(params.search ? { search: params.search } : {}),
          ...(params.contact_type ? { contact_type: params.contact_type } : {}),
          ...(params.source_type ? { source_type: params.source_type } : {}),
          ...(params.job_id ? { job_id: params.job_id } : {}),
        },
      },
    );

    return response.data;
  },

  getContactById: async (contactId: string): Promise<RecruiterContact> => {
    const response = await api.get<RecruiterContact>(
      `/recruiter-contacts/${contactId}`,
    );

    return response.data;
  },

  getStats: async (): Promise<RecruiterContactStats> => {
    const response = await api.get<RecruiterContactStats>(
      "/recruiter-contacts/stats",
    );

    return response.data;
  },
};
