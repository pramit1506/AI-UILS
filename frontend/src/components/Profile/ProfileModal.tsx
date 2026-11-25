import React, { useState, useEffect } from 'react';
import {
  X,
  User as UserIcon,
  CheckCircle2,
  AlertCircle,
  Save,
  LogOut,
  Sparkles,
  ShieldCheck,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import {
  closeProfileModal,
  updateUserProfile,
  deleteAccount,
  logoutUser,
  openAuthModal,
} from '../../redux/authSlice';
import { clearChat } from '../../redux/chatSlice';
import { clearLog } from '../../redux/logSlice';
import { clearAgentState } from '../../redux/agentSlice';
import { clearDocument } from '../../redux/documentSlice';
import './ProfileModal.css';

export const ProfileModal: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user, isProfileModalOpen, loading, error } = useAppSelector(
    (state) => state.auth
  );

  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [bio, setBio] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmUsername, setDeleteConfirmUsername] = useState('');

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setUsername(user.username || '');
      setBio(user.bio || '');
      setSaveSuccess(false);
      setShowDeleteConfirm(false);
      setDeleteConfirmUsername('');
    }
  }, [user, isProfileModalOpen]);

  if (!isProfileModalOpen || !user) return null;

  const handleClose = () => {
    setShowDeleteConfirm(false);
    dispatch(closeProfileModal());
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(false);
    const resultAction = await dispatch(
      updateUserProfile({
        full_name: fullName.trim() || undefined,
        username: username.trim() || undefined,
        bio: bio.trim() || undefined,
      })
    );
    if (updateUserProfile.fulfilled.match(resultAction)) {
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }
  };

  const handleLogout = () => {
    dispatch(logoutUser());
    dispatch(clearChat());
    dispatch(clearLog());
    dispatch(clearAgentState());
    dispatch(clearDocument());
    dispatch(closeProfileModal());
  };

  const handleSwitchAccount = () => {
    dispatch(closeProfileModal());
    dispatch(openAuthModal('login'));
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmUsername.trim() !== user.username) return;
    const result = await dispatch(deleteAccount());
    if (deleteAccount.fulfilled.match(result)) {
      dispatch(clearChat());
      dispatch(clearLog());
      dispatch(clearAgentState());
      dispatch(clearDocument());
      dispatch(closeProfileModal());
      dispatch(openAuthModal('register'));
    }
  };

  const initials = (user.full_name || user.username || 'U')
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="profile-modal-overlay" onClick={handleClose}>
      <div className="profile-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="profile-modal-header">
          <div className="profile-modal-title-group">
            <div className="profile-modal-icon-badge">
              <UserIcon size={18} />
            </div>
            <div>
              <h2>User Profile Settings</h2>
              <p>Manage your account identity & profile preferences</p>
            </div>
          </div>
          <button className="profile-modal-close-btn" onClick={handleClose} title="Close">
            <X size={18} />
          </button>
        </div>

        {/* Profile Card Banner */}
        <div className="profile-banner">
          <div className="profile-avatar-circle">{initials}</div>
          <div className="profile-banner-info">
            <h3 className="profile-banner-name">{user.full_name || user.username}</h3>
            <div className="profile-banner-sub">
              <span className="profile-banner-handle">@{user.username}</span>
              <span className="profile-badge-role">
                <ShieldCheck size={10} style={{ display: 'inline', marginRight: 3 }} />
                {user.role}
              </span>
            </div>
          </div>
        </div>

        {/* Edit Form */}
        <form className="profile-form" onSubmit={handleSave}>
          {saveSuccess && (
            <div className="profile-success-banner">
              <CheckCircle2 size={14} />
              <span>Profile details updated successfully!</span>
            </div>
          )}

          {error && (
            <div className="auth-error-banner">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <div className="profile-form-group">
            <label htmlFor="prof-email">Email Address (Read-only)</label>
            <input
              id="prof-email"
              type="text"
              className="profile-input profile-input-readonly"
              value={user.email}
              readOnly
            />
          </div>

          <div className="profile-form-group">
            <label htmlFor="prof-name">Display Name</label>
            <input
              id="prof-name"
              type="text"
              className="profile-input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Dr. Jane Smith"
            />
          </div>

          <div className="profile-form-group">
            <label htmlFor="prof-username">Username</label>
            <input
              id="prof-username"
              type="text"
              className="profile-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="profile-form-group">
            <label htmlFor="prof-bio">Bio & Department Notes</label>
            <textarea
              id="prof-bio"
              className="profile-input profile-textarea"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Add your title, responsibilities, or role details..."
              rows={3}
            />
          </div>

          <div className="profile-modal-actions">
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                className="profile-btn-logout"
                onClick={handleLogout}
                title="Log out of this session"
              >
                <LogOut size={13} />
                <span>Log Out</span>
              </button>
              <button
                type="button"
                className="new-session-btn"
                onClick={handleSwitchAccount}
                title="Switch to another user profile"
              >
                <Sparkles size={13} />
                <span>Switch User</span>
              </button>
            </div>

            <button type="submit" className="profile-btn-save" disabled={loading}>
              <Save size={13} />
              <span>{loading ? 'Saving…' : 'Save Changes'}</span>
            </button>
          </div>
        </form>

        {/* Danger Zone Section */}
        <div className="profile-danger-zone">
          {!showDeleteConfirm ? (
            <div className="profile-danger-collapsed">
              <div>
                <span className="profile-danger-title">Delete Account</span>
                <span className="profile-danger-desc">
                  Permanently remove this account and all associated logs.
                </span>
              </div>
              <button
                type="button"
                className="profile-btn-danger"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 size={13} />
                <span>Delete Account</span>
              </button>
            </div>
          ) : (
            <div className="profile-danger-expanded">
              <div className="profile-danger-warning-header">
                <AlertTriangle size={16} className="profile-warning-icon" />
                <strong>Permanent Deletion Confirmation</strong>
              </div>
              <p className="profile-danger-warning-text">
                This action is irreversible. All of your personal audit logs and sessions will be permanently erased.
                To confirm, type your username <code>{user.username}</code> below:
              </p>
              <input
                type="text"
                className="profile-input profile-danger-input"
                placeholder={user.username}
                value={deleteConfirmUsername}
                onChange={(e) => setDeleteConfirmUsername(e.target.value)}
              />
              <div className="profile-danger-actions">
                <button
                  type="button"
                  className="profile-btn-cancel-danger"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="profile-btn-confirm-delete"
                  disabled={loading || deleteConfirmUsername.trim() !== user.username}
                  onClick={handleDeleteAccount}
                >
                  <Trash2 size={13} />
                  <span>{loading ? 'Deleting…' : 'Permanently Delete Account'}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
