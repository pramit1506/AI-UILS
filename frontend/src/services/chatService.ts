import { apiClient } from './api';
import { ChatRequest, ConversationResponse } from '../types/chat';
import { APIResponse } from '../types/api';

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<APIResponse<ConversationResponse>> {
    // A chat turn can run several provider calls. Leave room for the API's own deadline.
    const response = await apiClient.post<APIResponse<ConversationResponse>>('/chat/', request, { timeout: 130_000 });
    return response.data;
  }
};
