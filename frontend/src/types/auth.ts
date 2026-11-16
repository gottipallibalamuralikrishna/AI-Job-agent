export interface User {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  preferred_job_country: string | null;
  include_international_remote: boolean;
  created_at: string;
}
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
export interface LoginPayload { email: string; password: string }
export interface RegisterPayload extends LoginPayload { full_name: string }
