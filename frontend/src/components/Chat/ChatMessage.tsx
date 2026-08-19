import React, { useState, useMemo } from 'react';
import { User, Save, Copy, Check, Sparkles, ArrowRight, Brain, ChevronDown, ChevronRight } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { addUserMessage, sendMessage } from '../../redux/chatSlice';
import { ChatMessage as IChatMessage } from '../../types/chat';
import { ToolExecutionCard } from './ToolExecutionCard';
import { ClarificationCard } from './ClarificationCard';
import './Chat.css';

interface ChatMessageProps {
  message: IChatMessage;
  onSaveLog?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onSaveLog }) => {
  const dispatch = useAppDispatch();
  const currentLog = useAppSelector((state) => state.log.currentLog);
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
    navigator.clipboard.writeText(cleanContent || message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTriggerSave = () => {
    if (onSaveLog) {
      onSaveLog();
    } else {
      dispatch(addUserMessage('Save the log'));
      dispatch(sendMessage('Save the log') as any);
    }
  };

  const timeStr = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const hasFields = Boolean(
    currentLog &&
      currentLog.fields &&
      Object.keys(currentLog.fields).filter((k) => !k.startsWith('_')).length > 0
  );

  // Check if message suggests saving or contains captured draft info
  const showInlineSavePrompt =
    !isUser &&
    hasFields &&
    (cleanContent.toLowerCase().includes('save the log') ||
      cleanContent.toLowerCase().includes('draft is ready') ||
      cleanContent.toLowerCase().includes('captured') ||
      cleanContent.toLowerCase().includes('extracted') ||
      cleanContent.toLowerCase().includes('review the') ||
      Boolean(message.tool_executions && message.tool_executions.length > 0));

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

          {cleanContent && (
            <div className="chat-message-bubble">{cleanContent}</div>
          )}

          {/* Direct Save Action inside Message Card */}
          {showInlineSavePrompt && (
            <div className="chat-inline-save-card">
              <div className="chat-inline-save-info">
                <div className="chat-inline-save-icon-wrap">
                  <Save size={14} />
                </div>
                <span className="chat-inline-save-text">
                  Ready to commit this {currentLog?.schema_name || 'record'}?
                </span>
              </div>
              <button
                className="chat-inline-save-btn"
                onClick={handleTriggerSave}
                title="Save and commit this log to database"
              >
                <span>Save Now</span>
                <ArrowRight size={12} />
              </button>
            </div>
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
          {!isUser && hasFields && (
            <button
              className="chat-message-save-link"
              onClick={handleTriggerSave}
              title="Save this log"
            >
              <Save size={11} />
              <span>Save Log</span>
            </button>
          )}
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
