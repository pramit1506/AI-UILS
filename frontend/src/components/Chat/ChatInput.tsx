import React, { useState, useRef } from 'react';
import { Send, Paperclip, Save, FileText } from 'lucide-react';
import './Chat.css';

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload: (file: File) => void;
  onSave?: () => void;
  hasDraft?: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onFileUpload,
  onSave,
  hasDraft,
  disabled,
}) => {
  const [input, setInput] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && !disabled) {
      onFileUpload(file);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="chat-input-wrapper">
      {/* Quick Action Suggestion Bar when a draft exists */}
      {hasDraft && (
        <div className="chat-quick-actions-bar">
          <button
            type="button"
            className="chat-quick-btn save-pill"
            onClick={onSave}
            title="Save and commit this log to database (Ctrl + Enter)"
          >
            <Save size={12} />
            <span>Save Log</span>
            <kbd>Ctrl+↵</kbd>
          </button>
          <button
            type="button"
            className="chat-quick-btn"
            onClick={() => onSend('Summarize the current draft')}
            disabled={disabled}
            title="Ask AI to summarize extracted fields"
          >
            <FileText size={12} />
            <span>Summarize Draft</span>
          </button>
        </div>
      )}

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <button
          type="button"
          className="chat-attach-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          title="Upload PDF, DOCX, TXT or EML"
        >
          <Paperclip size={16} />
        </button>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileChange}
          accept=".pdf,.docx,.txt,.eml"
        />
        <input
          type="text"
          className="chat-input-field"
          placeholder={
            hasDraft
              ? "Type a correction, 'save the log', or drop a file…"
              : 'Message the AI or drop a file…'
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
        />

        {hasDraft && (
          <button
            type="button"
            className="chat-input-inline-save"
            onClick={onSave}
            title="Save current log record"
            disabled={disabled}
          >
            <Save size={12} />
            <span>Save</span>
          </button>
        )}

        <button
          type="submit"
          className="chat-send-btn"
          disabled={!input.trim() || disabled}
          title="Send"
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
};
