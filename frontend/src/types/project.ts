import { SourceReference } from './analysis';

export interface Project {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface StoredAnalysisSummary {
  id: string;
  project_id: string;
  title: string;
  source_type?: string | null;
  source_name?: string | null;
  summary: string;
  created_at: string;
  key_points_count: number;
  actions_count: number;
  decisions_count: number;
  important_dates_count: number;
}

export interface SearchResultItem {
  id: string;
  analysis_id: string;
  analysis_title: string;
  item_type: "Key Point" | "Action" | "Decision" | "Date" | "Summary";
  content: string;
  details?: string | null;
  source_reference?: SourceReference | null;
  created_at: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResultItem[];
}
