import React, { useState, useMemo } from 'react';
import { User, Copy, Check, Sparkles, Brain, ChevronDown, ChevronRight } from 'lucide-react';
import { ChatMessage as IChatMessage } from '../../types/chat';
import { ToolExecutionCard } from './ToolExecutionCard';
import { ClarificationCard } from './ClarificationCard';
import './Chat.css';

interface ChatMessageProps {
  message: IChatMessage;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [showThinking, setShowThinking] = useState(false);

  // Extract thinking tags if present
  const { thoughtContent, cleanContent } = useMemo(() => {
    const raw = message.content || '';
    const match = raw.match(/<think>([\s\S]*?)<\/think>/i);
    if (match) {
      return {
        thoughtContent: match[1].trim(),
        cleanContent: raw.replace(/<think>[\s\S]*?<\/think>/gi, '').trim(),
      };
    }
    return {
      thoughtContent: null,
      cleanContent: raw,
    };
  }, [message.content]);

  const handleCopy = () => {
    // Clipboard API rejects in non-secure contexts (plain HTTP deployments) —
    // swallow instead of surfacing an unhandled rejection.
    navigator.clipboard?.writeText(cleanContent || message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => setCopied(false));
  };

  const timeStr = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`chat-message-wrapper ${isUser ? 'user' : 'assistant'}`}>
      <div className="chat-message-row">
        <div className={`chat-avatar ${isUser ? 'user' : 'assistant'}`}>
          {isUser ? <User size={13} /> : <Sparkles size={13} />}
        </div>

        <div className="chat-message-content">
          {!isUser && message.tool_executions && message.tool_executions.length > 0 && (
            <ToolExecutionCard executions={message.tool_executions} />
          )}

          {/* Collapsible Reasoning Process Accordion */}
          {!isUser && thoughtContent && (
            <div className="chat-thinking-accordion">
              <button
                type="button"
                className="chat-thinking-toggle"
                onClick={() => setShowThinking(!showThinking)}
              >
                <Brain size={12} className="chat-thinking-icon" />
                <span>Reasoning Process</span>
                {showThinking ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
              {showThinking && (
                <div className="chat-thinking-content">
                  {thoughtContent}
                </div>
              )}
            </div>
          )}

          {cleanContent && !(message.clarification_request?.required && message.clarification_request.question?.trim() === cleanContent.trim()) && (
            <div className="chat-message-bubble">{cleanContent}</div>
          )}

          {!isUser &&
            message.clarification_request &&
            message.clarification_request.required && (
              <ClarificationCard payload={message.clarification_request} />
            )}
        </div>
      </div>

      <div className="chat-message-footer">
        <span className="chat-message-time">{timeStr}</span>
        <div className="chat-message-footer-actions">
          {!isUser && (
            <button
              className="chat-message-copy"
              onClick={handleCopy}
              title="Copy to clipboard"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
