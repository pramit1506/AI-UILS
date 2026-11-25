import React, { useEffect, useRef } from 'react';
import { Lock, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { closeGuestSaveWall } from '../../redux/uiSlice';
import { openAuthModal } from '../../redux/authSlice';
import './GuestSaveWall.css';

/**
 * GuestSaveWall — shown whenever a signed-out visitor tries to persist data.
 * The backend refuses unauthenticated saves by design (records are user-
 * scoped DB rows), so this modal is the only honest response: explain that
 * the draft is temporary, and offer account creation to keep it. The cross
 * button dismisses without losing the draft the user already built.
 */
export const GuestSaveWall: React.FC = () => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((state) => state.ui.isGuestSaveWallOpen);
  const primary = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.activeElement;
    primary.current?.focus();
    return () => { if (previous instanceof HTMLElement) previous.focus(); };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSignIn = () => {
    dispatch(closeGuestSaveWall());
    dispatch(openAuthModal('login'));
  };

  const handleClose = () => dispatch(closeGuestSaveWall());

  return (
    <div className="gsw-overlay" onClick={handleClose}>
      <div
        className="gsw-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gsw-title"
        aria-describedby="gsw-description"
        onKeyDown={event => {
          if (event.key === 'Escape') handleClose();
          if (event.key !== 'Tab') return;
          const buttons = event.currentTarget.querySelectorAll('button');
          const first = buttons[0];
          const last = buttons[buttons.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }}
      >
        <button className="gsw-close-btn" onClick={handleClose} title="Close — keep drafting as a guest">
          <X size={16} />
        </button>

        <div className="gsw-icon-badge">
          <Lock size={20} />
        </div>

        <h2 id="gsw-title" className="gsw-title">Log in to save your record</h2>
        <p id="gsw-description" className="gsw-subtitle">
          Your draft stays open while you log in. Closing or refreshing this tab clears an unsaved draft.
        </p>

        <button className="gsw-signin-btn" onClick={handleSignIn} ref={primary}>
          <Lock size={15} />
          <span>Log in</span>
        </button>

        <button className="gsw-guest-btn" onClick={handleClose}>
          Keep editing
        </button>
      </div>
    </div>
  );
};
