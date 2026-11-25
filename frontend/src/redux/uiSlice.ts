import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from './store';
import { loginUser, registerUser, logoutUser } from './authSlice';

export type ThemeMode = 'light' | 'dark';
export type Palette = 'sand' | 'slate' | 'sage';
export type SearchMode = 'related' | 'exact';

interface UiState {
  palette: Palette;
  searchMode: SearchMode;
  /** Light (pastel grey / powder blue / black) or dark variant of the brand palette */
  theme: ThemeMode;
  /** Landing-page login nudge — shown once per browser session for guests */
  isEntryPromptVisible: boolean;
  /** "Log in to save" wall for guest users */
  isGuestSaveWallOpen: boolean;
}

const THEME_KEY = 'uils_theme';
const ENTRY_PROMPT_KEY = 'uils_entry_prompt_dismissed';

function getStoredTheme(): ThemeMode {
  try {
    const raw = window.localStorage.getItem(THEME_KEY);
    return raw === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

function shouldShowEntryPrompt(): boolean {
  try {
    if (window.sessionStorage.getItem(ENTRY_PROMPT_KEY)) return false;
    return true;
  } catch {
    return true;
  }
}

function dismissEntryPromptStorage() {
  try {
    window.sessionStorage.setItem(ENTRY_PROMPT_KEY, '1');
  } catch {
    // ignore — dismiss is per-visit only
  }
}

const initialState: UiState = {
  palette: readChoice('uils_palette', ['sand', 'slate', 'sage'] as const),
  searchMode: readChoice('uils_search_mode', ['related', 'exact'] as const),
  theme: getStoredTheme(),
  isEntryPromptVisible: shouldShowEntryPrompt(),
  isGuestSaveWallOpen: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setPalette(state, action: PayloadAction<Palette>) { state.palette = action.payload; },
    setSearchMode(state, action: PayloadAction<SearchMode>) { state.searchMode = action.payload; },
    setTheme: (state, action: PayloadAction<ThemeMode>) => {
      state.theme = action.payload;
      try {
        window.localStorage.setItem(THEME_KEY, action.payload);
      } catch {
        // ignore — theme preference falls back to default next visit
      }
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      try {
        window.localStorage.setItem(THEME_KEY, state.theme);
      } catch {
        // ignore
      }
    },
    dismissEntryPrompt: (state) => {
      state.isEntryPromptVisible = false;
      dismissEntryPromptStorage();
    },
    reopenEntryPrompt: (state) => {
      state.isEntryPromptVisible = true;
    },
    openGuestSaveWall: (state) => {
      state.isGuestSaveWallOpen = true;
    },
    closeGuestSaveWall: (state) => {
      state.isGuestSaveWallOpen = false;
    },},
  extraReducers: (builder) => {
    // Signing in or registering resolves the guest state: the save wall and
    // the entry prompt both close because the visitor now HAS an account.
    builder
      .addCase(loginUser.fulfilled, (state) => {
        state.isGuestSaveWallOpen = false;
        state.isEntryPromptVisible = false;
      })
      .addCase(registerUser.fulfilled, (state) => {
        state.isGuestSaveWallOpen = false;
        state.isEntryPromptVisible = false;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        // Back to guest status — invite the visitor to sign in again.
        state.isEntryPromptVisible = true;
      });
  },
});

export const {
  setPalette,
  setSearchMode,
  setTheme,
  toggleTheme,
  dismissEntryPrompt,
  reopenEntryPrompt,
  openGuestSaveWall,
  closeGuestSaveWall,
} = uiSlice.actions;

// Convenience selectors
export const selectTheme = (state: RootState): ThemeMode => state.ui.theme;
export const selectIsEntryPromptVisible = (state: RootState): boolean =>
  state.ui.isEntryPromptVisible;
export const selectIsGuestSaveWallOpen = (state: RootState): boolean =>
  state.ui.isGuestSaveWallOpen;

export default uiSlice.reducer;

function readChoice<T extends string>(key: string, values: readonly T[]): T {
  try {
    return values.find(value => value === window.localStorage.getItem(key)) ?? values[0];
  } catch {
    return values[0];
  }
}
