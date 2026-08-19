import React, { useState } from 'react';
import {
  X,
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User as UserIcon,
  Shield,
  Briefcase,
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
  deleteAccountByEmail,
  clearAuthError,
  AuthModalTab,
} from '../../redux/authSlice';
import './AuthModal.css';

const DEMO_ACCOUNTS = [
  {
    name: 'Dr. Jane Smith',
    role: 'Quality Assurance Lead',
    username: 'dr_smith',
    email: 'jane.smith@pharma-qms.io',
    password: 'password123',
    bio: 'Lead Quality & Compliance Specialist with 10+ years QMS experience.',
  },
  {
    name: 'Alex Rivera',
    role: 'Compliance Officer',
    username: 'alex_rivera',
    email: 'alex.rivera@audit-corp.com',
    password: 'password123',
    bio: 'Regulatory Affairs & Pharmacovigilance Auditor.',
  },
  {
    name: 'Sarah Connor',
    role: 'Operations Director',
    username: 'sarah_c',
    email: 'sarah.c@manufacturing.org',
    password: 'password123',
    bio: 'Plant Operations & Batch Intake Director.',
  },
];

export const AuthModal: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthModalOpen, authModalTab, loading, error, successMessage } = useAppSelector(
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
  const [regRole, setRegRole] = useState('Quality Assurance');
  const [regBio, setRegBio] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Password Reset fields
  const [resetLogin, setResetLogin] = useState('');
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetValidationErr, setResetValidationErr] = useState<string | null>(null);

  // Delete Account (Recovery) fields
  const [deleteEmail, setDeleteEmail] = useState('');
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  if (!isAuthModalOpen) return null;

  const handleClose = () => {
    dispatch(closeAuthModal());
  };

  const handleTabChange = (tab: AuthModalTab) => {
    dispatch(clearAuthError());
    setResetValidationErr(null);
    if (tab === 'reset-password') {
      // Auto-prefill reset identifier from login or register input if available
      setResetLogin((loginInput.trim() || regEmail.trim() || '').toLowerCase());
    } else if (tab === 'delete-account') {
      setDeleteEmail((regEmail.trim() || loginInput.trim() || '').toLowerCase());
    }
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
        role: regRole,
        bio: regBio.trim() || undefined,
      })
    );
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetValidationErr(null);

    if (!resetLogin.trim()) {
      setResetValidationErr('Please enter your email or username.');
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

    dispatch(
      resetPassword({
        login: resetLogin.trim(),
        new_password: resetNewPassword,
      })
    );
  };

  const handleDeleteRecoverySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deleteEmail.trim()) return;
    if (deleteConfirmText.trim().toUpperCase() !== 'DELETE') return;

    dispatch(
      deleteAccountByEmail({
        email: deleteEmail.trim(),
        confirm_text: 'DELETE',
      })
    );
  };

  const handleSelectDemoProfile = async (profile: typeof DEMO_ACCOUNTS[0]) => {
    dispatch(clearAuthError());
    try {
      const loginAction = await dispatch(
        loginUser({ login: profile.username, password: profile.password })
      );
      if (loginUser.rejected.match(loginAction)) {
        await dispatch(
          registerUser({
            email: profile.email,
            username: profile.username,
            full_name: profile.name,
            password: profile.password,
            role: profile.role,
            bio: profile.bio,
          })
        );
      }
    } catch {
      // Handled by Redux
    }
  };

  const getHeaderTitle = () => {
    switch (authModalTab) {
      case 'login':
        return 'Welcome Back';
      case 'register':
        return 'Create Your Account';
      case 'reset-password':
        return 'Reset Password';
      case 'delete-account':
        return 'Delete / Wipe Account';
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
        return 'Set a new password for your registered email or username';
      case 'delete-account':
        return 'Permanently remove an orphaned account to unblock registration';
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
                  placeholder="e.g. dr_smith or name@company.com"
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
                  placeholder="name@company.com"
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
              <label htmlFor="reg-role">Role / Department</label>
              <div className="auth-input-wrapper">
                <Briefcase size={14} className="auth-input-icon" />
                <select
                  id="reg-role"
                  className="auth-select"
                  value={regRole}
                  onChange={(e) => setRegRole(e.target.value)}
                >
                  <option value="Quality Assurance">Quality Assurance</option>
                  <option value="Compliance Officer">Compliance Officer</option>
                  <option value="Pharmacovigilance">Pharmacovigilance</option>
                  <option value="Medical & Health">Medical & Health</option>
                  <option value="Finance & Accounting">Finance & Accounting</option>
                  <option value="Operations">Operations</option>
                  <option value="General Auditor">General Auditor</option>
                </select>
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

        {/* Reset Password Form */}
        {authModalTab === 'reset-password' && (
          <form className="auth-form" onSubmit={handleResetSubmit}>
            {(error || resetValidationErr) && (
              <div className="auth-error-banner">
                <AlertCircle size={14} />
                <span>{resetValidationErr || error}</span>
              </div>
            )}

            <div className="auth-form-group">
              <label htmlFor="reset-login">Registered Email or Username *</label>
              <div className="auth-input-wrapper">
                <Mail size={14} className="auth-input-icon" />
                <input
                  id="reset-login"
                  type="text"
                  className="auth-input"
                  placeholder="e.g. dr_smith@pharma-qms.io or username"
                  value={resetLogin}
                  onChange={(e) => setResetLogin(e.target.value)}
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
                  required
                />
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              <KeyRound size={15} />
              <span>{loading ? 'Updating Password…' : 'Reset Password & Sign In'}</span>
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
              <button
                type="button"
                className="auth-link-btn danger"
                onClick={() => handleTabChange('delete-account')}
              >
                Wipe / Delete Account instead
              </button>
            </div>
          </form>
        )}

        {/* Delete Account (Recovery) Form */}
        {authModalTab === 'delete-account' && (
          <form className="auth-form" onSubmit={handleDeleteRecoverySubmit}>
            {error && (
              <div className="auth-error-banner">
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}

            <div className="auth-recovery-notice">
              <Trash2 size={16} className="auth-notice-icon" />
              <div>
                <strong>Account Purge & Recovery</strong>
                <p>
                  Permanently remove the registered account from the database. This allows you to recreate your account cleanly.
                </p>
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="del-email">Registered Email to Purge *</label>
              <div className="auth-input-wrapper">
                <Mail size={14} className="auth-input-icon" />
                <input
                  id="del-email"
                  type="email"
                  className="auth-input"
                  placeholder="e.g. dr_smith@pharma-qms.io"
                  value={deleteEmail}
                  onChange={(e) => setDeleteEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="auth-form-group">
              <label htmlFor="del-confirm">Type <strong>DELETE</strong> to confirm *</label>
              <div className="auth-input-wrapper">
                <input
                  id="del-confirm"
                  type="text"
                  className="auth-input"
                  placeholder="DELETE"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  required
                  style={{ paddingLeft: '0.75rem', letterSpacing: '0.05em' }}
                />
              </div>
            </div>

            <button
              type="submit"
              className="auth-submit-btn danger"
              disabled={loading || deleteConfirmText.trim().toUpperCase() !== 'DELETE'}
            >
              <Trash2 size={15} />
              <span>{loading ? 'Purging Account…' : 'Permanently Delete Account'}</span>
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

        {/* Demo Quick Switch Section */}
        <div className="auth-demo-section">
          <div className="auth-demo-title">
            <Sparkles size={12} />
            <span>Instant Demo Accounts</span>
          </div>
          <div className="auth-demo-pills">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.username}
                type="button"
                className="auth-demo-pill-btn"
                onClick={() => handleSelectDemoProfile(acc)}
                disabled={loading}
                title={`Sign in or register as ${acc.name}`}
              >
                <span className="auth-demo-pill-name">{acc.name}</span>
                <span className="auth-demo-pill-role">{acc.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
