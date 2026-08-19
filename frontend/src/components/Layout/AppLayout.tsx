import React from 'react';
import { Columns, ScanText, ListOrdered, MessageSquare, Keyboard } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { setViewLayoutMode, toggleShortcutsModal } from '../../redux/logSlice';
import { Header } from './Header';
import DynamicLogForm from '../LogForm/DynamicLogForm';
import { DocumentViewer } from '../DocumentViewer/DocumentViewer';
import { ChatPanel } from '../Chat/ChatPanel';
import { ShortcutsModal } from '../Common/ShortcutsModal';
import { ViewLayoutMode } from '../../types/log';
import './Layout.css';

export const AppLayout: React.FC = () => {
  const dispatch = useAppDispatch();
  const viewLayoutMode = useAppSelector((state) => state.log.viewLayoutMode);

  const handleModeChange = (mode: ViewLayoutMode) => {
    dispatch(setViewLayoutMode(mode));
  };

  const showDocViewer = viewLayoutMode === 'side-by-side' || viewLayoutMode === 'review-focus';
  const showLogForm =
    viewLayoutMode === 'side-by-side' ||
    viewLayoutMode === 'review-focus' ||
    viewLayoutMode === 'fields-only';
  const showChatPanel = viewLayoutMode === 'side-by-side' || viewLayoutMode === 'chat-focus';

  return (
    <div className="app-layout">
      <Header />

      {/* ── Subheader View Mode Switcher ─────────────────────── */}
      <div className="app-view-bar">
        <div className="view-mode-selector">
          <button
            className={`view-mode-pill ${viewLayoutMode === 'side-by-side' ? 'active' : ''}`}
            onClick={() => handleModeChange('side-by-side')}
            title="Side-by-side original document, extracted fields, and chat (Key 1)"
          >
            <Columns size={13} className="view-mode-icon" />
            <span>Side-by-Side</span>
            <kbd className="view-kbd">1</kbd>
          </button>

          <button
            className={`view-mode-pill ${viewLayoutMode === 'review-focus' ? 'active' : ''}`}
            onClick={() => handleModeChange('review-focus')}
            title="Focus on Document and Field Verification (Key 2)"
          >
            <ScanText size={13} className="view-mode-icon" />
            <span>Review Focus</span>
            <kbd className="view-kbd">2</kbd>
          </button>

          <button
            className={`view-mode-pill ${viewLayoutMode === 'fields-only' ? 'active' : ''}`}
            onClick={() => handleModeChange('fields-only')}
            title="Extracted Fields only (Key 3)"
          >
            <ListOrdered size={13} className="view-mode-icon" />
            <span>Fields Only</span>
            <kbd className="view-kbd">3</kbd>
          </button>

          <button
            className={`view-mode-pill ${viewLayoutMode === 'chat-focus' ? 'active' : ''}`}
            onClick={() => handleModeChange('chat-focus')}
            title="Chat and Corrections only (Key 4)"
          >
            <MessageSquare size={13} className="view-mode-icon" />
            <span>Chat Focus</span>
            <kbd className="view-kbd">4</kbd>
          </button>
        </div>

        <div className="view-bar-right">
          <button
            className="view-shortcuts-hint-btn"
            onClick={() => dispatch(toggleShortcutsModal())}
            title="Keyboard shortcuts cheat sheet (?)"
          >
            <Keyboard size={13} />
            <span>Shortcuts</span>
            <kbd className="view-kbd">?</kbd>
          </button>
        </div>
      </div>

      {/* ── Main Workspace Panels ─────────────────────────────── */}
      <main className={`app-main layout-${viewLayoutMode}`}>
        {showDocViewer && (
          <section className="workspace-panel doc-panel">
            <DocumentViewer />
          </section>
        )}

        {showLogForm && (
          <section className="workspace-panel fields-panel">
            <DynamicLogForm />
          </section>
        )}

        {showChatPanel && (
          <section className="workspace-panel chat-panel-col">
            <ChatPanel />
          </section>
        )}
      </main>

      {/* Global Keyboard Shortcuts Reference Modal */}
      <ShortcutsModal />
    </div>
  );
};
