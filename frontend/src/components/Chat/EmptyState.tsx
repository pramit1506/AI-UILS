import React, { useRef } from 'react';
import { Upload, FileText } from 'lucide-react';
import './Chat.css';

interface EmptyStateProps {
  onFileUpload: (file: File) => void;
  onPasteText?: (text: string) => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onFileUpload, onPasteText }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleCardClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
    }
  };

  const handlePasteCardClick = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && onPasteText) {
        onPasteText(text);
      }
    } catch {
      const userInput = prompt('Please paste your document text here:');
      if (userInput && onPasteText) {
        onPasteText(userInput);
      }
    }
  };

  return (
    <div className="chat-empty-state-modern">
      <p className="empty-eyebrow">AI-Powered</p>
      <h3 className="empty-title">Document Intelligence</h3>
      <p className="empty-subtitle">
        Upload or paste any document — the AI extracts structured fields
        and populates the form automatically.
      </p>

      <div className="empty-cards-container">
        <div
          className="empty-card"
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={handleCardClick}
          title="Upload a PDF, Word, or text file"
        >
          <div className="card-icon-wrap">
            <Upload size={24} className="card-icon" />
          </div>
          <div className="card-text">
            Upload a document
          </div>
          <div className="card-hint">PDF · DOCX · TXT · EML</div>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileChange}
            accept=".pdf,.txt,.docx,.eml"
          />
        </div>

        <div
          className="empty-card"
          onClick={handlePasteCardClick}
          title="Paste text from clipboard"
        >
          <div className="card-icon-wrap">
            <FileText size={24} className="card-icon" />
          </div>
          <div className="card-text">
            Paste document text
          </div>
          <div className="card-hint">From clipboard</div>
        </div>
      </div>
    </div>
  );
};
