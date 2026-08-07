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
}

export const logService = {
  getLogs: async (schema_name?: string, skip = 0, limit = 50): Promise<LogRecord[]> => {
    const params: Record<string, any> = { skip, limit };
    if (schema_name) {
      params.schema_name = schema_name;
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
  }
};
