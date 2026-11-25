import React, { useState } from 'react';
import {
  X,
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User as UserIcon,
  Shield,
  AlertCircle,
  Eye,
  EyeOff,
  Sparkles,
  KeyRound,
  Trash2,
  CheckCircle2,
  ArrowLeft,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import {
  closeAuthModal,
  setAuthModalTab,
  loginUser,
  registerUser,
  resetPassword,
  clearAuthError,
  AuthModalTab,
} from '../../redux/authSlice';
import './AuthModal.css';
import { RecoveryForm } from './RecoveryForm';

/*
// Demo accounts contain publicly-known credentials — never include them in
// production builds. (Previously hardcoded plaintext passwords shipped in the
// production bundle.)
//
// Presentation label: "Trial account and data" — these seeded accounts ship
// with sample data so visitors can explore the product without signing up.
*/
const DEMO_ACCOUNTS = import.meta.env.DEV
  ? [
      {
        name: 'Dr. Jane Smith',
        kind: 'Trial account with sample data',
        role: 'Quality Assurance Lead',
        username: 'dr_smith',
        email: 'jane.smith@example.com',
        password: 'password123',
        bio: 'Sample account for guided product tours.',
      },
      {
        name: 'Alex Rivera',
        kind: 'Trial account with sample data',
        role: 'Compliance Officer',
        username: 'alex_rivera',
        email: 'alex.rivera@example.com',
        password: 'password123',
        bio: 'Sample account showing role-based profile fields.',
      },
      {
        name: 'Sarah Connor',
        kind: 'Trial account with sample data',
        role: 'Operations Director',
        username: 'sarah_c',
        email: 'sarah.c@example.com',
        password: 'password123',
        bio: 'Sample account for multi-user tour scenarios.',
      },
    ]
  : [];

export const AuthModal: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthModalOpen, authModalTab, loading, error, successMessage, isAuthenticated } = useAppSelector(
    (state) => state.auth
  );

  // Login fields
  const [loginInput, setLoginInput] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);

  // Register fields
  const [regEmail, setRegEmail] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regFullName, setRegFullName] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regBio, setRegBio] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Password change fields (requires an authenticated session)
  const [resetCurrentPassword, setResetCurrentPassword] = useState('');
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetValidationErr, setResetValidationErr] = useState<string | null>(null);

  if (!isAuthModalOpen) return null;

  const handleClose = () => {
    dispatch(closeAuthModal());
  };

  const handleTabChange = (tab: AuthModalTab) => {
    dispatch(clearAuthError());
    setResetValidationErr(null);
    dispatch(setAuthModalTab(tab));
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginInput.trim() || !loginPassword) return;
    dispatch(loginUser({ login: loginInput.trim(), password: loginPassword }));
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regEmail.trim() || !regUsername.trim() || !regPassword) return;
    dispatch(
      registerUser({
        email: regEmail.trim(),
        username: regUsername.trim(),
        full_name: regFullName.trim() || undefined,
        password: regPassword,
        bio: regBio.trim() || undefined,
      })
    );
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetValidationErr(null);

    if (!isAuthenticated) return; // Form is not rendered in this state
    if (!resetCurrentPassword) {
      setResetValidationErr('Please enter your current password.');
      return;
    }
    if (resetNewPassword.length < 6) {
      setResetValidationErr('Password must be at least 6 characters long.');
      return;
    }
    if (resetNewPassword !== resetConfirmPassword) {
      setResetValidationErr('Passwords do not match. Please verify.');
      return;
    }

    // Security: the backend requires a valid session + the current password.
    // The old flow ("email + new password" with no verification) allowed
    // anyone who knew a username to take over the account.
    dispatch(
      resetPassword({
        current_password: resetCurrentPassword,
        new_password: resetNewPassword,
      })
    );
  };

  const handleSelectDemoProfile = async (profile: typeof DEMO_ACCOUNTS[0]) => {
    dispatch(clearAuthError());
    // Dev helper only: sign in with the pre-seeded demo account. The previous
    // auto-register fallback silently created real database rows from the
    // bundled credentials — removed to prevent unintended account creation.
    dispatch(loginUser({ login: profile.username, password: profile.password }));
  };

  const getHeaderTitle = () => {
    switch (authModalTab) {
      case 'login':
        return 'Welcome Back';
      case 'register':
        return 'Create Your Account';
      case 'reset-password':
        return isAuthenticated ? 'Change Password' : 'Reset your password';
      case 'delete-account':
        return 'Delete Account';
      default:
        return 'Authentication';
    }
  };

  const getHeaderSubtitle = () => {
    switch (authModalTab) {
      case 'login':
        return 'Sign in to access your personal logs & sessions';
      case 'register':
        return 'Start capturing and verifying logs with your private profile';
      case 'reset-password':
        return isAuthenticated
          ? 'Verify your current password, then choose a new one'
          : 'Use the email address associated with your account';
      case 'delete-account':
        return 'Account deletion requires signing in — it is done from your profile';
      default:
        return '';
    }
  };

  const isEmailConflict =
    error && (error.toLowerCase().includes('already exists') || error.toLowerCase().includes('already taken'));

  return (
    <div className="auth-modal-overlay" onClick={handleClose}>
      <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div className="auth-modal-title-group">
            <div className={`auth-modal-icon-badge ${authModalTab === 'delete-account' ? 'danger' : ''}`}>
              {authModalTab === 'reset-password' && <KeyRound size={18} />}
              {authModalTab === 'delete-account' && <Trash2 size={18} />}
              {authModalTab !== 'reset-password' && authModalTab !== 'delete-account' && <Shield size={18} />}
            </div>
            <div>
              <h2>{getHeaderTitle()}</h2>
              <p>{getHeaderSubtitle()}</p>
            </div>
          </div>
          <button className="auth-modal-close-btn" onClick={handleClose} title="Close">
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="auth-tabs">
          <button
            className={`auth-tab-btn ${authModalTab === 'login' ? 'active' : ''}`}
            onClick={() => handleTabChange('login')}
          >
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
          <button
            className={`auth-tab-btn ${authModalTab === 'register' ? 'active' : ''}`}
            onClick={() => handleTabChange('register')}
          >
            <UserPlus size={14} />
            <span>Create Account</span>
          </button>
          {authModalTab === 'reset-password' && (
            <button className="auth-tab-btn active" onClick={() => handleTabChange('reset-password')}>
              <KeyRound size={14} />
              <span>Reset</span>
            </button>
          )}
          {authModalTab === 'delete-account' && (
            <button className="auth-tab-btn active danger-tab" onClick={() => handleTabChange('delete-account')}>
              <Trash2 size={14} />
              <span>Delete</span>
            </button>
          )}
        </div>

        {/* Success Banner */}
        {successMessage && (
          <div className="auth-success-banner">
            <CheckCircle2 size={14} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Login Form */}
        {authModalTab === 'login' && (
          <form className="auth-form" onSubmit={handleLoginSubmit}>
            {error && (
              <div className="auth-error-banner">
                <AlertCircle size={14} />
                <div className="auth-error-content">
                  <span>{error}</span>
                  {error.toLowerCase().includes('invalid') && (
                    <button
                      type="button"
                      className="auth-error-action-btn"
                      onClick={() => handleTabChange('reset-password')}
                    >
                      Forgot password? Reset it here
                    </button>
                  )}
                </div>
              </div>
            )}

            <div className="auth-form-group">
              <label htmlFor="login-username">Username or Email</label>
              <div className="auth-input-wrapper">
                <UserIcon size={14} className="auth-input-icon" />
                <input
                  id="login-username"
                  type="text"
                  className="auth-input"
                  placeholder="e.g. dr_smith or name@example.com"
                  value={loginInput}
                  onChange={(e) => setLoginInput(e.target.value)}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="auth-form-group">
              <div className="auth-form-header-row">
                <label htmlFor="login-password">Password</label>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => handleTabChange('reset-password')}
                >
                  Forgot password?
                </button>
              </div>
              <div className="auth-input-wrapper">
                <Lock size={14} className="auth-input-icon" />
                <input
                  id="login-password"
                  type={showLoginPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Enter your password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="auth-input-toggle-pw"
                  onClick={() => setShowLoginPassword(!showLoginPassword)}
                  title={showLoginPassword ? 'Hide password' : 'Show password'}
                >
                  {showLoginPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              <LogIn size={15} />
              <span>{loading ? 'Authenticating…' : 'Sign In'}</span>
            </button>
          </form>
        )}

        {/* Register Form */}
        {authModalTab === 'register' && (
          <form className="auth-form" onSubmit={handleRegisterSubmit}>
            {error && (
              <div className="auth-error-banner">
                <AlertCircle size={14} />
                <div className="auth-error-content">
                  <span>{error}</span>
                  {isEmailConflict && (
                    <div className="auth-conflict-actions">
                      <button
                        type="button"
                        className="auth-error-action-btn"
                        onClick={() => handleTabChange('reset-password')}
                      >
                        Reset password for this email
                      </button>
                      <span className="auth-action-divider">•</span>
                      <button
                        type="button"
                        className="auth-error-action-btn danger"
                        onClick={() => handleTabChange('delete-account')}
                      >
                        Purge & delete old account
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="auth-form-group">
              <label htmlFor="reg-email">Email Address *</label>
              <div className="auth-input-wrapper">
                <Mail size={14} className="auth-input-icon" />
                <input
                  id="reg-email"
                  type="email"
                  className="auth-input"
                  placeholder="name@example.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="reg-username">Username *</label>
              <div className="auth-input-wrapper">
                <UserIcon size={14} className="auth-input-icon" />
                <input
                  id="reg-username"
                  type="text"
                  className="auth-input"
                  placeholder="username (letters, numbers, underscores)"
                  value={regUsername}
                  onChange={(e) => setRegUsername(e.target.value)}
                  pattern="^[a-zA-Z0-9_\-\.]+$"
                  required
                />
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="reg-fullname">Full Name</label>
              <div className="auth-input-wrapper">
                <UserIcon size={14} className="auth-input-icon" />
                <input
                  id="reg-fullname"
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Dr. Jane Smith"
                  value={regFullName}
                  onChange={(e) => setRegFullName(e.target.value)}
                />
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="reg-password">Password (min 6 characters) *</label>
              <div className="auth-input-wrapper">
                <Lock size={14} className="auth-input-icon" />
                <input
                  id="reg-password"
                  type={showRegPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Choose a secure password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  minLength={6}
                  required
                />
                <button
                  type="button"
                  className="auth-input-toggle-pw"
                  onClick={() => setShowRegPassword(!showRegPassword)}
                  title={showRegPassword ? 'Hide password' : 'Show password'}
                >
                  {showRegPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="reg-bio">Bio & Department Notes</label>
              <div className="auth-input-wrapper">
                <input
                  id="reg-bio"
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Lead QMS Auditor, Pharmacovigilance Team"
                  value={regBio}
                  onChange={(e) => setRegBio(e.target.value)}
                  style={{ paddingLeft: '0.75rem' }}
                />
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              <UserPlus size={15} />
              <span>{loading ? 'Creating Profile…' : 'Create Account'}</span>
            </button>
          </form>
        )}

        {/* Change Password Form — authenticated users only */}
        {authModalTab === 'reset-password' && !isAuthenticated && <RecoveryForm onLogin={() => handleTabChange('login')} />}
        {authModalTab === 'reset-password' && isAuthenticated && (
          <form className="auth-form" onSubmit={handleResetSubmit}>
            {(error || resetValidationErr) && (
              <div className="auth-error-banner">
                <AlertCircle size={14} />
                <span>{resetValidationErr || error}</span>
              </div>
            )}

            <div className="auth-form-group">
              <label htmlFor="reset-current-password">Current Password *</label>
              <div className="auth-input-wrapper">
                <Lock size={14} className="auth-input-icon" />
                <input
                  id="reset-current-password"
                  type="password"
                  className="auth-input"
                  placeholder="Enter your current password"
                  value={resetCurrentPassword}
                  onChange={(e) => setResetCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="reset-new-password">New Password (min 6 chars) *</label>
              <div className="auth-input-wrapper">
                <Lock size={14} className="auth-input-icon" />
                <input
                  id="reset-new-password"
                  type={showResetPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Enter your new password"
                  value={resetNewPassword}
                  onChange={(e) => setResetNewPassword(e.target.value)}
                  minLength={6}
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="auth-input-toggle-pw"
                  onClick={() => setShowResetPassword(!showResetPassword)}
                  title={showResetPassword ? 'Hide password' : 'Show password'}
                >
                  {showResetPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="reset-confirm-password">Confirm New Password *</label>
              <div className="auth-input-wrapper">
                <Lock size={14} className="auth-input-icon" />
                <input
                  id="reset-confirm-password"
                  type={showResetPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Re-enter your new password"
                  value={resetConfirmPassword}
                  onChange={(e) => setResetConfirmPassword(e.target.value)}
                  minLength={6}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              <KeyRound size={15} />
              <span>{loading ? 'Updating Password…' : 'Update Password'}</span>
            </button>

            <div className="auth-form-footer">
              <button
                type="button"
                className="auth-link-btn"
                onClick={() => handleTabChange('login')}
              >
                <ArrowLeft size={12} style={{ display: 'inline', marginRight: 4 }} />
                Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* Delete Account — notice only (deletion requires an authenticated
            DELETE /auth/account call; the old unauthenticated by-email form was
            a critical vulnerability and was removed) */}
        {authModalTab === 'delete-account' && (
          <div className="auth-form">
            {error && (
              <div className="auth-error-banner">
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}

            <div className="auth-recovery-notice">
              <Trash2 size={16} className="auth-notice-icon" />
              <div>
                <strong>Sign in required</strong>
                <p>
                  Accounts can only be deleted by their owner while signed in.
                  Once authenticated, use <strong>Profile → Delete Account</strong> to
                  permanently remove your account and all of its logs.
                </p>
              </div>
            </div>

            <div className="auth-form-footer">
              <button
                type="button"
                className="auth-link-btn"
                onClick={() => handleTabChange('login')}
              >
                <ArrowLeft size={12} style={{ display: 'inline', marginRight: 4 }} />
                Back to Sign In
              </button>
            </div>
          </div>
        )}

        {/* Trial account and data — seeded accounts with sample data */}
        {DEMO_ACCOUNTS.length > 0 && (
          <div className="auth-demo-section">
            <div className="auth-demo-title">
              <Sparkles size={12} />
              <span>Trial account and data</span>
            </div>
            <p className="auth-demo-subtitle">One-click sign-in · pre-seeded with sample records for exploring</p>
            <div className="auth-demo-pills">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  className="auth-demo-pill-btn"
                  onClick={() => handleSelectDemoProfile(acc)}
                  disabled={loading}
                  title={`Sign in as ${acc.name}`}
                >
                  <span className="auth-demo-pill-name">{acc.name}</span>
                  <span className="auth-demo-pill-role">{acc.role}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
