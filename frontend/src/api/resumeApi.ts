import { api } from "./axios";

export const deleteResume = async (resumeId: string): Promise<void> => {
  await api.delete(`/resumes/${resumeId}`);
};

export interface Resume {
  id: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  parsing_status: "uploaded" | "processing" | "parsed" | "failed";
  is_primary: boolean;
  created_at: string;
}

export const getResumes = async (): Promise<Resume[]> => {
  const response = await api.get<Resume[]>("/resumes");
  return response.data;
};

export const uploadResume = async (file: File): Promise<Resume> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<Resume>("/resumes/upload", formData);

  return response.data;
};

export const parseResume = async (resumeId: string) => {
  const response = await api.post(`/resumes/${resumeId}/parse`);

  return response.data;
};

export const selectPrimaryResume = async (resumeId: string): Promise<Resume> => {
  const response = await api.put<Resume>(`/resumes/${resumeId}/primary`);
  return response.data;
};

export const extractResumeProfile = async (resumeId: string) => {
  const response = await api.post(`/resumes/${resumeId}/extract-profile`);

  return response.data;
};
