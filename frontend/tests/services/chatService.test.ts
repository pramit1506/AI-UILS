import { describe, it, expect, vi } from 'vitest';
import { chatService } from '../../src/services/chatService';
import { apiClient } from '../../src/services/api';

vi.mock('../../src/services/api', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe('chatService', () => {
  it('sendMessage should call api post', async () => {
    const mockResponse = { data: { response: 'Hello User', conversation_id: '123' } };
    (apiClient.post as any).mockResolvedValue(mockResponse);

    const request = {
      user_message: 'Hi',
      message_history: [],
    };

    const result = await chatService.sendMessage(request);
    
    expect(apiClient.post).toHaveBeenCalledWith('/chat/', request);
    expect(result).toEqual(mockResponse.data);
  });
});
