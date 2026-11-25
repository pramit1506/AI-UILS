import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { setTheme, setPalette, setSearchMode, type ThemeMode, type Palette, type SearchMode } from '../../redux/uiSlice';
import { openAuthModal } from '../../redux/authSlice';

export function SettingsPage() {
  const { theme, palette, searchMode } = useAppSelector(state => state.ui);
  const { user, isAuthenticated } = useAppSelector(state => state.auth);
  const dispatch = useAppDispatch();
  return <main className="settings-page"><h2>Settings</h2>
    <section><h3>Appearance</h3>
      <label>Color palette<select value={palette} onChange={e => dispatch(setPalette(e.target.value as Palette))}>
        <option value="sand">Sand &amp; Indigo</option><option value="slate">Slate &amp; Blue</option><option value="sage">Sage &amp; Forest</option>
      </select></label>
      <label>Display mode<select value={theme} onChange={e => dispatch(setTheme(e.target.value as ThemeMode))}>
        <option value="light">Light</option><option value="dark">Dark</option>
      </select></label>
    </section>
    <section><h3>Search preferences</h3>
      <label>Match saved records<select value={searchMode} onChange={e => dispatch(setSearchMode(e.target.value as SearchMode))}>
        <option value="related">Include related words and prefixes</option><option value="exact">Exact words only</option>
      </select></label><p>Appearance and search preferences are saved on this browser.</p>
    </section>
    <section><h3>Account security</h3><p>{isAuthenticated ? user?.email : 'Recover access using your account email.'}</p>
      <button className="record-primary" onClick={() => dispatch(openAuthModal('reset-password'))}>
        {isAuthenticated ? 'Change password' : 'Recover password'}</button>
    </section>
  </main>;
}
