import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useStore } from 'react-redux';
import { Sparkles, Upload, Loader2 } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { sendMessage, addUserMessage } from '../../redux/chatSlice';
import { setExtractionStatus } from '../../redux/logSlice';
import { setDocument, updateDocumentText, setFileObjectUrl } from '../../redux/documentSlice';
import type { RootState } from '../../redux/store';
import { uploadService } from '../../services/uploadService';
import { openAuthModal } from '../../redux/authSlice';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { DocumentViewer } from '../DocumentViewer/DocumentViewer';
import { EmptyState } from './EmptyState';
import { TypingIndicator } from './TypingIndicator';
import { ErrorBanner } from '../Common/ErrorBanner';
import './Chat.css';

export const ChatPanel: React.FC = () => {
  const dispatch = useAppDispatch();
  const store = useStore<RootState>();
  const { messages, loading, error } = useAppSelector((state) => state.chat);
  const { extractionStatus, currentLog } = useAppSelector((state) => state.log);
  const currentDocument = useAppSelector((state) => state.document.currentDocument);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [uploadError, setUploadError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [showSamples, setShowSamples] = useState(false);
  const sampleTrigger = useRef<HTMLButtonElement>(null);
  const samplePanel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (showSamples) samplePanel.current?.focus();
  }, [showSamples]);
  const closeSamples = () => {
    setShowSamples(false);
    requestAnimationFrame(() => sampleTrigger.current?.focus());
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, extractionStatus]);

  const handleSend = useCallback(
    (text: string) => {
      // If user pasted a sizable paragraph/document text and no document is active yet, store in documentSlice
      const capture = !currentDocument && !currentLog && (text.length > 80 || /^[\p{L}][\p{L}\p{N} _-]{1,35}:\s*\S/u.test(text)) &&
        !/^(?:save|search|find|retrieve|look up|recall|summarize)\b/i.test(text);
      if (capture) {
        dispatch(updateDocumentText(text));
      }
      dispatch(addUserMessage(text));
      dispatch(sendMessage(capture ? { message: text, action: 'capture' } : text));
    },
    [dispatch, currentDocument, currentLog]
  );

  const handleFileUpload = useCallback(
    async (file: File) => {
      const workspaceRevision = store.getState().chat.workspaceRevision;
      if (!store.getState().auth?.isAuthenticated) {
        dispatch(openAuthModal('login'));
        return;
      }
      setUploadError('');
      dispatch(setExtractionStatus('extracting'));
      try {
        const response = await uploadService.extractText(file);
        if (store.getState().chat.workspaceRevision !== workspaceRevision) return;
        if (response.success && response.data) {
          const extension = file.name.split('.').pop()?.toLowerCase() || 'txt';
          const fileType = (['pdf', 'docx', 'txt', 'eml'].includes(extension)
            ? extension
            : 'txt') as 'pdf' | 'txt' | 'eml' | 'docx';
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
          // setDocument resets the URL slot; record the new blob URL afterwards.
          dispatch(setFileObjectUrl(fileUrl));

          const textToProcess = `Process this uploaded document (${response.data.filename}):\n\n${response.data.text}`;
          dispatch(addUserMessage(textToProcess));
          dispatch(sendMessage({ message: textToProcess, action: 'capture' }));
          dispatch(setExtractionStatus('completed'));
        } else {
          throw new Error('Empty response from extraction service.');
        }
      } catch (err) {
        if (store.getState().chat.workspaceRevision !== workspaceRevision) return;
        console.error('File upload failed:', err);
        dispatch(setExtractionStatus('error'));
        const errorMsg =
          err instanceof Error ? err.message : 'Could not read the uploaded file. Please try again.';
        setUploadError(errorMsg);
      }
    },
    [dispatch, store]
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
      if (!loading && extractionStatus !== 'extracting' && e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
        e.dataTransfer.clearData();
      }
    },
    [handleFileUpload, loading, extractionStatus]
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
      {(messages.length > 0 || isExtracting) && <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon-wrap">
            <Sparkles size={14} />
          </div>
          <h2>Conversation</h2>
        </div>

        <div className="chat-header-right">
          {isExtracting && (
            <div className="chat-extraction-pill">
              <Loader2 size={12} className="extraction-spinner-icon" />
              <span>Extracting…</span>
            </div>
          )}
        </div>
      </div>}

      {uploadError && <div role="alert"><ErrorBanner message={uploadError} /></div>}
      <div className="chat-messages-container">
        {messages.length === 0 ? (
          <div className={'intake-grid' + (showSamples ? ' with-samples' : '')}><div className="intake-main"><EmptyState busy={loading || isExtracting} onSignIn={() => dispatch(openAuthModal('login'))} onFileUpload={handleFileUpload} onPasteText={(text) => {
            dispatch(updateDocumentText(text));
            dispatch(addUserMessage(text));
            dispatch(sendMessage({ message: text, action: 'capture' }));
          }} />
          {!currentDocument && !loading && !isExtracting && <button type="button" className="sample-trigger"
            ref={sampleTrigger} aria-expanded={showSamples} aria-controls="sample-library" onClick={() => setShowSamples(!showSamples)}>
            {showSamples ? 'Hide samples' : 'Try a sample document'}</button>}</div>
          {showSamples && <aside id="sample-library" ref={samplePanel} tabIndex={-1} aria-label="Sample documents"
            onKeyDown={e => { if (e.key === 'Escape') closeSamples(); }}>
            <button type="button" className="sample-close" onClick={closeSamples} aria-label="Close sample documents">×</button>
            <DocumentViewer /></aside>}</div>
        ) : (
          <div className="chat-messages-list">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
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
