import { useEffect, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../redux/hooks';
import {
  bulkApproveAll,
  bulkApproveHighConfidence,
  bulkRejectAll,
  bulkRejectUnapproved,
  resetFieldStatuses,
  selectNextField,
  selectPrevField,
  setFieldStatus,
  toggleShortcutsModal,
  setViewLayoutMode,
} from '../redux/logSlice';
import { setActiveHighlightField } from '../redux/documentSlice';

interface UseReviewShortcutsOptions {
  onSave?: () => void;
  onEditActiveField?: (fieldKey: string) => void;
  onConversationalCorrect?: (fieldKey: string) => void;
  enabled?: boolean;
}

export function useReviewShortcuts(options: UseReviewShortcutsOptions = {}) {
  const { onSave, onEditActiveField, onConversationalCorrect, enabled = true } = options;
  const dispatch = useAppDispatch();
  const activeFieldKey = useAppSelector((state) => state.log.activeFieldKey);
  const currentLog = useAppSelector((state) => state.log.currentLog);
  const isShortcutsModalOpen = useAppSelector((state) => state.log.isShortcutsModalOpen);

  // Sync active highlight field in document viewer whenever activeFieldKey changes
  useEffect(() => {
    dispatch(setActiveHighlightField(activeFieldKey));
  }, [activeFieldKey, dispatch]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      const target = e.target as HTMLElement | null;
      const isInput =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable);

      // ── Handle Ctrl/Cmd+Enter (Commit / Save) even in input fields ──
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        onSave?.();
        return;
      }

      // ── Close shortcuts modal on Escape ──
      if (e.key === 'Escape') {
        if (isShortcutsModalOpen) {
          dispatch(toggleShortcutsModal());
          return;
        }
      }

      // If user is currently typing in an input/textarea, do not intercept regular typing
      if (isInput) {
        return;
      }

      // ── Bulk Shortcuts (with Shift or Alt) ──
      if (e.shiftKey || e.altKey) {
        const key = e.key.toUpperCase();
        if (key === 'A') {
          e.preventDefault();
          dispatch(bulkApproveAll());
          return;
        }
        if (key === 'H') {
          e.preventDefault();
          dispatch(bulkApproveHighConfidence(0.75));
          return;
        }
        if (key === 'R') {
          e.preventDefault();
          dispatch(bulkRejectAll());
          return;
        }
        if (key === 'U') {
          e.preventDefault();
          dispatch(bulkRejectUnapproved());
          return;
        }
        if (key === 'X') {
          e.preventDefault();
          dispatch(resetFieldStatuses());
          return;
        }
      }

      // ── View Layout Switches (1, 2, 3, 4) ──
      if (e.key === '1') {
        e.preventDefault();
        dispatch(setViewLayoutMode('side-by-side'));
        return;
      }
      if (e.key === '2') {
        e.preventDefault();
        dispatch(setViewLayoutMode('review-focus'));
        return;
      }
      if (e.key === '3') {
        e.preventDefault();
        dispatch(setViewLayoutMode('fields-only'));
        return;
      }
      if (e.key === '4') {
        e.preventDefault();
        dispatch(setViewLayoutMode('chat-focus'));
        return;
      }

      // ── Help Modal Shortcut (?) ──
      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault();
        dispatch(toggleShortcutsModal());
        return;
      }

      // ── Field Navigation & Actions (Only if log has fields) ──
      if (!currentLog?.fields || Object.keys(currentLog.fields).length === 0) {
        return;
      }

      // Navigation: J / Down, K / Up
      if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowDown') {
        e.preventDefault();
        dispatch(selectNextField());
        return;
      }
      if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowUp') {
        e.preventDefault();
        dispatch(selectPrevField());
        return;
      }

      // Field level actions on active field
      if (activeFieldKey) {
        if (e.key === 'a' || e.key === 'A') {
          e.preventDefault();
          dispatch(setFieldStatus({ fieldKey: activeFieldKey, status: 'approved' }));
          dispatch(selectNextField());
          return;
        }
        if (e.key === 'r' || e.key === 'R') {
          e.preventDefault();
          dispatch(setFieldStatus({ fieldKey: activeFieldKey, status: 'rejected' }));
          dispatch(selectNextField());
          return;
        }
        if (e.key === 'e' || e.key === 'E') {
          e.preventDefault();
          onEditActiveField?.(activeFieldKey);
          return;
        }
        if (e.key === 'c' || e.key === 'C') {
          e.preventDefault();
          onConversationalCorrect?.(activeFieldKey);
          return;
        }
      }
    },
    [
      enabled,
      isShortcutsModalOpen,
      currentLog,
      activeFieldKey,
      dispatch,
      onSave,
      onEditActiveField,
      onConversationalCorrect,
    ]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
