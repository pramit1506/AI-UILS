import { useEffect, useState } from 'react';
import { apiClient } from '../../services/api';

export function RecoveryForm({ onLogin }: { onLogin: () => void }) {
  const [step, setStep] = useState<'email' | 'code' | 'done'>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [cooldown, setCooldown] = useState(false);
  const [configured, setConfigured] = useState<boolean | undefined>();
  useEffect(() => {
    const controller = new AbortController();
    void apiClient.get('/auth/recovery/status', { signal: controller.signal })
      .then(response => setConfigured(response.data.email_recovery_configured))
      .catch(() => { /* The recovery request reports service errors independently. */ });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!cooldown) return;
    const timer = window.setTimeout(() => setCooldown(false), 60000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  async function submit(requestCode: boolean) {
    if (busy) return;
    setError('');
    if (!requestCode && password !== confirmation) {
      setError('The passwords must match.');
      return;
    }
    setBusy(true);
    try {
      if (requestCode) {
        const response = await apiClient.post('/auth/recovery/request', { email: email.trim() });
        setNotice(response.data.message);
        setCooldown(true);
        setStep('code');
      } else {
        await apiClient.post('/auth/recovery/confirm', { email: email.trim(), code, new_password: password });
        setPassword('');
        setConfirmation('');
        setCode('');
        setStep('done');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password recovery failed. Please try again.');
    } finally {
      setBusy(false);
    }
  }
  if (step === 'done') return <div className="auth-form"><p role="status">Your password has been updated.</p>
    <button className="auth-submit-btn" onClick={onLogin}>Sign in with your new password</button></div>;
  return <form className="auth-form" onSubmit={e => { e.preventDefault(); void submit(step === 'email'); }}>
    {configured === false && <p className="auth-error-banner" role="status">
      Email recovery is unavailable here. Contact your administrator to recover your account.
    </p>}
    <label className="auth-form-group">Account email<input className="auth-input" type="email" autoComplete="email"
      required value={email} readOnly={step === 'code'} disabled={configured === false}
      onChange={e => setEmail(e.target.value)} /></label>
    {step === 'code' && <>
      <p role="status">{notice} Codes expire after 10 minutes.</p>
      <p id="recovery-code-hint">Look for “Your Nikarsh AI password reset code” in your inbox. If you don’t see it, check your <strong>Spam or Junk</strong> folder.</p>
      <label className="auth-form-group">Six-digit code<input className="auth-input" autoComplete="one-time-code"
        aria-describedby="recovery-code-hint"
        inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={e => setCode(e.target.value)} /></label>
      <label className="auth-form-group">New password<input className="auth-input" type="password" autoComplete="new-password"
        minLength={6} required value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label className="auth-form-group">Confirm new password<input className="auth-input" type="password" autoComplete="new-password"
        required value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
    </>}
    {error && <p className="auth-error-banner" role="alert">{error}</p>}
    <button className="auth-submit-btn" disabled={busy || configured === false}>{busy ? 'Please wait…' : step === 'email' ? 'Email me a code' : 'Reset password'}</button>
    {step === 'code' && <div><button type="button" className="auth-link-btn" disabled={busy || cooldown} onClick={() => void submit(true)}>{cooldown ? 'Resend available in one minute' : 'Resend code'}</button>
      {' · '}<button type="button" className="auth-link-btn" disabled={busy} onClick={() => { setStep('email'); setCode(''); setError(''); }}>Change email</button></div>}
    <button type="button" className="auth-link-btn" onClick={onLogin}>Back to sign in</button>
  </form>;
}
