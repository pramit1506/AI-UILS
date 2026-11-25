import { apiClient } from './api';

export interface LogRecord {
  id: string;
  log_reference: string;
  schema_name: string;
  domain: string | null;
  source: string | null;
  summary?: string | null;
  source_filename?: string | null;
  has_source_text?: boolean;
  // The backend's LogRecordRead does NOT return `version` or `field_metadata`;
  // the previous required fields were always `undefined` at runtime while
  // pretending to exist.
  data: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  requires_review: boolean;
  overall_confidence: number | null;
  conversation_id?: string | null;
  user_id?: string | null;
}

export const logService = {
  getLogs: async (schema_name?: string, skip = 0, limit = 50, needs_review?: boolean, signal?: AbortSignal): Promise<LogRecord[]> => {
    const params: Record<string, unknown> = { skip, limit };
    if (schema_name) {
      params.schema_name = schema_name;
    }
    if (needs_review !== undefined) {
      params.needs_review = needs_review;
    }
    const response = await apiClient.get('/logs/', { params, signal });
    return response.data.data;
  },

  searchPage: async (
    query: string,
    options: { limit: number; schemaName?: string; needsReview?: boolean; cursor?: string; signal?: AbortSignal; related?: boolean }
  ) => {
    const { limit, schemaName, needsReview, cursor, signal } = options;
    const response = await apiClient.get<{ data: LogRecord[]; next_cursor: string | null }>(
      '/logs/search',
      { params: { q: query, limit, schema_name: schemaName, needs_review: needsReview, cursor, related: options.related }, signal }
    );
    return { records: response.data.data, nextCursor: response.data.next_cursor };
  },

  searchLogs: async (query: string, schema_name?: string, limit = 50): Promise<LogRecord[]> => {
    const page = await logService.searchPage(query, { schemaName: schema_name, limit });
    return page.records;
  },
  
  getLog: async (logReference: string, signal?: AbortSignal): Promise<LogRecord> => {
    const response = await apiClient.get(`/logs/${encodeURIComponent(logReference)}`, { signal });
    return response.data.data;
  },

  getSourceText: async (logReference: string, signal: AbortSignal): Promise<string> => {
    const response = await apiClient.get<{ data: { text: string } }>(
      `/logs/${encodeURIComponent(logReference)}/source`,
      { signal }
    );
    return response.data.data.text;
  },

  markAsReviewed: async (logReference: string): Promise<LogRecord> => {
    const response = await apiClient.patch(`/logs/${logReference}/review`);
    return response.data.data;
  },

  editLog: async (
    logReference: string,
    updates: Partial<{ data: Record<string, unknown>; summary: string; requires_review: boolean }>
  ): Promise<LogRecord> => {
    const response = await apiClient.patch(`/logs/${logReference}`, updates);
    return response.data.data;
  },

  deleteLog: async (logReference: string): Promise<void> => {
    const response = await apiClient.delete(`/logs/${logReference}`);
    return response.data;
  }
};
