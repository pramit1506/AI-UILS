import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../redux/hooks';
import { addUserMessage, sendMessage } from '../redux/chatSlice';
import { openGuestSaveWall } from '../redux/uiSlice';
import { RootState } from '../redux/store';

/**
 * Shared save-log UX logic: triggers the "Save the log" chat command and
 * exposes the saved state (`savedLogReference` from logSlice) so every Save
 * button can switch to a disabled "Saved ✓ LOG-XXXX" state and can never
 * duplicate the record.
 *
 * Guest wall: records are user-scoped DB rows, so WITHOUT an account a save
 * is impossible by design — every Save surface raises the "log in to save"
 * modal instead of firing a chat call the backend would refuse anyway.
 */
export function useSaveLog() {
  const dispatch = useAppDispatch();
  const savedReference = useAppSelector(
    (state: RootState) => state.log.savedLogReference
  );
  const savedAt = useAppSelector((state: RootState) => state.log.savedAt);
  const chatLoading = useAppSelector((state: RootState) => state.chat.loading);
  const isAuthenticated = useAppSelector((state: RootState) => state.auth?.isAuthenticated ?? false);

  const triggerSave = useCallback(() => {
    if (chatLoading || savedReference) return;
    if (!isAuthenticated) {
      dispatch(openGuestSaveWall());
      return;
    }
    dispatch(addUserMessage('Save the log'));
    dispatch(sendMessage({ message: 'Save the log', action: 'save_reviewed' }));
  }, [dispatch, isAuthenticated, chatLoading, savedReference]);

  return {
    /** LOG-XXXX reference of the last successful save, null when unsaved */
    savedReference,
    savedAt,
    saved: Boolean(savedReference),
    chatLoading,
    triggerSave,
  };
}
