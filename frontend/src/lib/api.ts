import { ShiftlyAnalysisResult } from '@/types/analysis';
import {
  Project,
  ProjectCreate,
  StoredAnalysisSummary,
  SearchResponse,
} from '@/types/project';
import { supabase } from './supabaseClient';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  public status: number;
  public requestId?: string;

  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.requestId = requestId;
  }
}

async function parseErrorResponse(res: Response): Promise<never> {
  const reqId = res.headers.get('X-Request-ID') || undefined;
  let detail = `Error ${res.status}: ${res.statusText}`;
  try {
    const errJson = await res.json();
    if (errJson.detail) {
      detail = errJson.detail;
    }
  } catch {
    // fallback to status text
  }
  throw new ApiError(detail, res.status, reqId);
}

/**
 * Retrieves the current user's Supabase access token for the Authorization header.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function fetchProjects(): Promise<Project[]> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function createProject(data: ProjectCreate): Promise<Project> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function fetchProject(projectId: string): Promise<Project> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function fetchAnalyses(projectId: string): Promise<StoredAnalysisSummary[]> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/analyses`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function fetchAnalysis(
  projectId: string,
  analysisId: string
): Promise<ShiftlyAnalysisResult> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/analyses/${analysisId}`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function saveAnalysisToProject(
  projectId: string,
  analysis: ShiftlyAnalysisResult
): Promise<{ id: string; message: string }> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/analyses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
    },
    body: JSON.stringify(analysis),
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function searchProjectIntelligence(
  projectId: string,
  query: string
): Promise<SearchResponse> {
  const authHeaders = await getAuthHeaders();
  const params = new URLSearchParams({ q: query });
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/search?${params.toString()}`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`, {
    method: 'DELETE',
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
}

export async function deleteAnalysis(projectId: string, analysisId: string): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/analyses/${analysisId}`, {
    method: 'DELETE',
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
}

export async function analyzeText(text: string): Promise<ShiftlyAnalysisResult> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function analyzeFile(file: File): Promise<ShiftlyAnalysisResult> {
  const authHeaders = await getAuthHeaders();
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/analyze/file`, {
    method: 'POST',
    headers: {
      ...authHeaders,
    },
    body: formData,
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export interface VerifyRecoveryResponse {
  recovery_token: string;
  message: string;
}

export interface ResetPasswordResponse {
  success: boolean;
  message: string;
}

export async function verifyRecoveryAccount(
  username: string,
  email: string
): Promise<VerifyRecoveryResponse> {
  const res = await fetch(`${API_BASE}/api/password-recovery/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: username.trim(),
      email: email.trim().toLowerCase(),
    }),
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

export async function resetRecoveryPassword(
  recoveryToken: string,
  newPassword: string,
  confirmPassword: string
): Promise<ResetPasswordResponse> {
  const res = await fetch(`${API_BASE}/api/password-recovery/reset`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      recovery_token: recoveryToken,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  });
  if (!res.ok) {
    return parseErrorResponse(res);
  }
  return res.json();
}

