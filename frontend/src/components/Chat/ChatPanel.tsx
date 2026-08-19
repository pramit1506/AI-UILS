import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Sparkles, Save, Upload, Loader2 } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { sendMessage, addUserMessage } from '../../redux/chatSlice';
import { setExtractionStatus } from '../../redux/logSlice';
import { setDocument, updateDocumentText } from '../../redux/documentSlice';
import { uploadService } from '../../services/uploadService';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { EmptyState } from './EmptyState';
import { TypingIndicator } from './TypingIndicator';
import { ErrorBanner } from '../Common/ErrorBanner';
import './Chat.css';

export const ChatPanel: React.FC = () => {
  const dispatch = useAppDispatch();
  const { messages, loading, error } = useAppSelector((state) => state.chat);
  const { extractionStatus, currentLog } = useAppSelector((state) => state.log);
  const currentDocument = useAppSelector((state) => state.document.currentDocument);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, extractionStatus]);

  const handleSend = useCallback(
    (text: string) => {
      // If user pasted a sizable paragraph/document text and no document is active yet, store in documentSlice
      if (!currentDocument && text.length > 80 && !text.toLowerCase().startsWith('save')) {
        dispatch(updateDocumentText(text));
      }
      dispatch(addUserMessage(text));
      dispatch(sendMessage(text));
    },
    [dispatch, currentDocument]
  );

  const handleSaveLog = useCallback(() => {
    dispatch(addUserMessage('Save the log'));
    dispatch(sendMessage('Save the log'));
  }, [dispatch]);

  const handleFileUpload = useCallback(
    async (file: File) => {
      dispatch(setExtractionStatus('extracting'));
      try {
        const response = await uploadService.extractText(file);
        if (response.success && response.data) {
          const extension = file.name.split('.').pop()?.toLowerCase() || 'txt';
          const fileType = (['pdf', 'docx', 'txt', 'eml'].includes(extension)
            ? extension
            : 'txt') as any;
          const fileUrl =
            fileType === 'pdf' && typeof URL !== 'undefined' && URL.createObjectURL
              ? URL.createObjectURL(file)
              : null;

          // Dispatch original document into state so DocumentViewer renders immediately
          dispatch(
            setDocument({
              id: Date.now().toString(),
              name: response.data.filename || file.name,
              fileType,
              rawText: response.data.text,
              fileUrl,
              uploadedAt: new Date().toISOString(),
              fileSize: file.size,
            })
          );

          const textToProcess = `Process this uploaded document (${response.data.filename}):\n\n${response.data.text}`;
          dispatch(addUserMessage(textToProcess));
          dispatch(sendMessage(textToProcess));
          dispatch(setExtractionStatus('completed'));
        } else {
          throw new Error('Empty response from extraction service.');
        }
      } catch (err: any) {
        console.error('File upload failed:', err);
        dispatch(setExtractionStatus('error'));
        const errorMsg =
          err?.message || 'Could not read the uploaded file. Please try again.';
        dispatch(addUserMessage(`[Upload failed: ${file.name}]`));
        dispatch(
          sendMessage(
            `The user tried to upload a file but it failed with error: ${errorMsg}. Please let the user know politely.`
          )
        );
      }
    },
    [dispatch]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
        e.dataTransfer.clearData();
      }
    },
    [handleFileUpload]
  );

  const isExtracting = extractionStatus === 'extracting';
  const hasDraft = Boolean(
    currentLog &&
      ((currentLog.fields && Object.keys(currentLog.fields).length > 0) ||
        currentLog.schema_name)
  );

  return (
    <div
      className={`chat-panel ${isDragging ? 'chat-panel-dragging' : ''}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon-wrap">
            <Sparkles size={14} />
          </div>
          <h2>AI Copilot</h2>
        </div>

        <div className="chat-header-right">
          {isExtracting && (
            <div className="chat-extraction-pill">
              <Loader2 size={12} className="extraction-spinner-icon" />
              <span>Extracting…</span>
            </div>
          )}

          {hasDraft && (
            <button
              className="chat-header-save-btn"
              onClick={handleSaveLog}
              disabled={loading || isExtracting}
              title="Save and commit this log to database (Ctrl + Enter)"
            >
              <Save size={12} />
              <span>Save Log</span>
            </button>
          )}
        </div>
      </div>

      <div className="chat-messages-container">
        {messages.length === 0 ? (
          <EmptyState onFileUpload={handleFileUpload} onPasteText={handleSend} />
        ) : (
          <div className="chat-messages-list">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onSaveLog={handleSaveLog} />
            ))}
            {loading && (
              <div className="chat-loading-indicator">
                <TypingIndicator />
              </div>
            )}
            {error && <ErrorBanner message={error} />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="chat-input-container">
        <ChatInput
          onSend={handleSend}
          onFileUpload={handleFileUpload}
          onSave={handleSaveLog}
          hasDraft={hasDraft}
          disabled={loading || isExtracting}
        />
      </div>

      {isDragging && (
        <div className="chat-drop-overlay">
          <div className="chat-drop-zone">
            <div className="chat-drop-icon">
              <Upload size={32} />
            </div>
            <div className="chat-drop-message">Drop document here</div>
            <div className="chat-drop-hint">PDF · DOCX · TXT · EML</div>
          </div>
        </div>
      )}
    </div>
  );
};
