import React from 'react';
import { Sparkles, LogIn, UserPlus, X, ArrowRight } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { dismissEntryPrompt } from '../../redux/uiSlice';
import { openAuthModal } from '../../redux/authSlice';
import './EntryPrompt.css';

/**
 * EntryPrompt — a one-per-session landing nudge asking visitors to log in.
 * Guests can still explore the workspace (backend guest mode), so the cross
 * button and "Try it first" both dismiss the prompt rather than blocking.
 */
export const EntryPrompt: React.FC = () => {
  const dispatch = useAppDispatch();
  const isVisible = useAppSelector((state) => state.ui.isEntryPromptVisible);
  const isAuthModalOpen = useAppSelector((state) => state.auth.isAuthModalOpen);

  if (!isVisible || isAuthModalOpen) return null;

  const dismiss = () => dispatch(dismissEntryPrompt());

  const handleLogin = () => {
    dismiss();
    dispatch(openAuthModal('login'));
  };

  const handleRegister = () => {
    dismiss();
    dispatch(openAuthModal('register'));
  };

  return (
    <div className="entry-overlay" onClick={dismiss}>
      <div
        className="entry-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="entry-title"
      >
        <button className="entry-close-btn" onClick={dismiss} title="Close — continue as a guest">
          <X size={16} />
        </button>

        <div className="entry-header">
          <img className="entry-logo-badge" src="/brand/nikarsh-ai-192.png" alt="" width="46" height="46" />
          <div>
            <h2 id="entry-title" className="entry-title">Welcome to Nikarsh AI</h2>
            <p className="entry-tagline">Paste anything — the AI turns it into a verified, structured record.</p>
          </div>
        </div>

        <ul className="entry-benefits">
          <li>
            <Sparkles size={13} className="entry-benefit-icon" />
            <span>AI detects the document type and extracts every field</span>
          </li>
          <li>
            <Sparkles size={13} className="entry-benefit-icon" />
            <span>You approve, correct, and commit it to your private database</span>
          </li>
          <li>
            <Sparkles size={13} className="entry-benefit-icon" />
            <span>Invoices, contracts, medical forms, receipts — any domain</span>
          </li>
        </ul>

        <div className="entry-actions">
          <button className="entry-cta-btn" onClick={handleRegister}>
            <UserPlus size={15} />
            <span>Create an account</span>
          </button>
          <button className="entry-login-btn" onClick={handleLogin}>
            <LogIn size={15} />
            <span>Sign in</span>
          </button>
        </div>

        <button className="entry-guest-btn" onClick={dismiss}>
          Try it first, without an account
          <ArrowRight size={12} />
        </button>

        <p className="entry-footnote">
          Guest mode is fully functional — but records only persist to a signed-in account.
        </p>
      </div>
    </div>
  );
};
