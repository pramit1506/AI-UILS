import { apiClient } from './api';

export interface LogRecord {
  id: string;
  log_reference: string;
  schema_name: string;
  domain: string;
  source: string;
  version: number;
  data: Record<string, any>;
  field_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  requires_review: boolean;
  overall_confidence: number | null;
}

export const logService = {
  getLogs: async (schema_name?: string, skip = 0, limit = 50, needs_review?: boolean): Promise<LogRecord[]> => {
    const params: Record<string, any> = { skip, limit };
    if (schema_name) {
      params.schema_name = schema_name;
    }
    if (needs_review !== undefined) {
      params.needs_review = needs_review;
    }
    const response = await apiClient.get('/logs/', { params });
    return response.data.data;
  },

  searchLogs: async (query: string, schema_name?: string, limit = 50): Promise<LogRecord[]> => {
    const params: Record<string, any> = { q: query, limit };
    if (schema_name) {
      params.schema_name = schema_name;
    }
    const response = await apiClient.get('/logs/search', { params });
    return response.data.data;
  },
  
  getLog: async (logReference: string): Promise<LogRecord> => {
    const response = await apiClient.get(`/logs/${logReference}`);
    return response.data.data;
  },

  markAsReviewed: async (logReference: string): Promise<LogRecord> => {
    const response = await apiClient.patch(`/logs/${logReference}/review`);
    return response.data.data;
  },

  deleteLog: async (logReference: string): Promise<void> => {
    const response = await apiClient.delete(`/logs/${logReference}`);
    return response.data;
  }
};
