import React from 'react';
import { Keyboard, X, CheckCheck, Compass, Sparkles } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { setShortcutsModalOpen } from '../../redux/logSlice';
import './ShortcutsModal.css';

export const ShortcutsModal: React.FC = () => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((state) => state.log.isShortcutsModalOpen);

  if (!isOpen) return null;

  const handleClose = () => {
    dispatch(setShortcutsModalOpen(false));
  };

  const sections = [
    {
      title: 'Bulk Approval & Review',
      icon: <CheckCheck size={14} className="shortcuts-section-icon" />,
      shortcuts: [
        { keys: ['Shift', 'A'], description: 'Approve all extracted fields' },
        { keys: ['Shift', 'H'], description: 'Approve high-confidence fields (≥75%)' },
        { keys: ['Shift', 'R'], description: 'Reject / flag all extracted fields' },
        { keys: ['Shift', 'U'], description: 'Reject all unapproved fields' },
        { keys: ['Shift', 'X'], description: 'Reset all field review decisions' },
      ],
    },
    {
      title: 'Field Navigation & Actions',
      icon: <Compass size={14} className="shortcuts-section-icon" />,
      shortcuts: [
        { keys: ['J', 'or', '↓'], description: 'Navigate to next field' },
        { keys: ['K', 'or', '↑'], description: 'Navigate to previous field' },
        { keys: ['A'], description: 'Approve focused field & advance' },
        { keys: ['R'], description: 'Reject focused field & advance' },
        { keys: ['E'], description: 'Quick inline edit on focused field' },
        { keys: ['C'], description: 'Ask AI for conversational correction' },
      ],
    },
    {
      title: 'Workspace',
      icon: <Sparkles size={14} className="shortcuts-section-icon" />,
      shortcuts: [
        { keys: ['Ctrl / ⌘', 'Enter'], description: 'Save & Commit Log' },
        { keys: ['?'], description: 'Toggle this shortcuts cheatsheet' },
        { keys: ['Esc'], description: 'Close dialogs or cancel inline edit' },
      ],
    },
  ];

  return (
    <div className="shortcuts-modal-overlay" onClick={handleClose}>
      <div
        className="shortcuts-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Keyboard Shortcuts"
      >
        <div className="shortcuts-modal-header">
          <div className="shortcuts-modal-title">
            <div className="shortcuts-modal-icon-wrap">
              <Keyboard size={16} />
            </div>
            <div>
              <h3>Keyboard Shortcuts</h3>
              <p>Accelerate document verification with instant key commands</p>
            </div>
          </div>
          <button
            className="shortcuts-modal-close"
            onClick={handleClose}
            aria-label="Close shortcuts dialog"
          >
            <X size={16} />
          </button>
        </div>

        <div className="shortcuts-modal-body">
          {sections.map((section) => (
            <div key={section.title} className="shortcuts-section">
              <div className="shortcuts-section-title">
                {section.icon}
                <h4>{section.title}</h4>
              </div>
              <div className="shortcuts-list">
                {section.shortcuts.map((item, idx) => (
                  <div key={idx} className="shortcut-row">
                    <div className="shortcut-keys">
                      {item.keys.map((k, kIdx) =>
                        k === 'or' ? (
                          <span key={kIdx} className="shortcut-or">
                            or
                          </span>
                        ) : (
                          <kbd key={kIdx} className="shortcut-kbd">
                            {k}
                          </kbd>
                        )
                      )}
                    </div>
                    <span className="shortcut-desc">{item.description}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="shortcuts-modal-footer">
          <span>Shortcuts are active during review and pause when typing inside text inputs.</span>
          <button className="shortcuts-got-it-btn" onClick={handleClose}>
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};
