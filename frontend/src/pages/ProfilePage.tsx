import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../services/api';
import { GripVertical, Save, CheckCircle, ArrowUp, ArrowDown, User, Mail, Shield, ListOrdered, Pencil, X, Check } from 'lucide-react';
import { CATEGORIES } from '../constants/sources';
import usePageTitle from '../hooks/usePageTitle';

const ProfilePage = () => {
  usePageTitle('Profile');
  const { user, updateUser } = useAuth();
  const [orderedCategories, setOrderedCategories] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  // Username change state
  const [editingUsername, setEditingUsername] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [usernameError, setUsernameError] = useState('');
  const [usernameSaving, setUsernameSaving] = useState(false);
  const [usernameSaved, setUsernameSaved] = useState(false);

  const fetchPreferences = useCallback(async () => {
    try {
      const prefs = await authApi.getCategoryPreferences();
      if (prefs.categories && prefs.categories.length > 0) {
        // Merge: user preferences first, then remaining categories
        const remaining = CATEGORIES.map(c => c.key).filter(k => !prefs.categories.includes(k));
        setOrderedCategories([...prefs.categories, ...remaining]);
      } else {
        setOrderedCategories(CATEGORIES.map(c => c.key));
      }
    } catch {
      setOrderedCategories(CATEGORIES.map(c => c.key));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  const moveUp = (idx: number) => {
    if (idx === 0) return;
    const newOrder = [...orderedCategories];
    [newOrder[idx - 1], newOrder[idx]] = [newOrder[idx], newOrder[idx - 1]];
    setOrderedCategories(newOrder);
    setSaved(false);
  };

  const moveDown = (idx: number) => {
    if (idx === orderedCategories.length - 1) return;
    const newOrder = [...orderedCategories];
    [newOrder[idx], newOrder[idx + 1]] = [newOrder[idx + 1], newOrder[idx]];
    setOrderedCategories(newOrder);
    setSaved(false);
  };

  const handleDragStart = (idx: number) => {
    setDraggedIdx(idx);
  };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    setDragOverIdx(idx);
    if (draggedIdx === null || draggedIdx === idx) return;
    const newOrder = [...orderedCategories];
    const [dragged] = newOrder.splice(draggedIdx, 1);
    newOrder.splice(idx, 0, dragged);
    setOrderedCategories(newOrder);
    setDraggedIdx(idx);
    setSaved(false);
  };

  const handleDragEnd = () => {
    setDraggedIdx(null);
    setDragOverIdx(null);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await authApi.updateCategoryPreferences(orderedCategories);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save preferences:', error);
    } finally {
      setSaving(false);
    }
  };

  const startEditUsername = () => {
    setNewUsername(user?.username || '');
    setUsernameError('');
    setUsernameSaved(false);
    setEditingUsername(true);
  };

  const cancelEditUsername = () => {
    setEditingUsername(false);
    setUsernameError('');
    setNewUsername('');
  };

  const handleUsernameSave = async () => {
    const trimmed = newUsername.trim();
    if (!trimmed) { setUsernameError('Username cannot be empty.'); return; }
    if (trimmed.length < 3) { setUsernameError('Username must be at least 3 characters.'); return; }
    if (trimmed === user?.username) { setUsernameError('This is already your username.'); return; }

    setUsernameSaving(true);
    setUsernameError('');
    try {
      const updated = await authApi.updateUsername(trimmed);
      updateUser(updated);
      setEditingUsername(false);
      setUsernameSaved(true);
      setTimeout(() => setUsernameSaved(false), 3000);
    } catch (err: any) {
      setUsernameError(err.response?.data?.detail || 'Failed to update username.');
    } finally {
      setUsernameSaving(false);
    }
  };

  const getCategoryMeta = (key: string) => CATEGORIES.find(c => c.key === key);

  if (loading) {
    return (
      <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-48 rounded bg-gray-800" />
            <div className="h-40 rounded-2xl bg-gray-800/40" />
            <div className="h-64 rounded-2xl bg-gray-800/40" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">

        {/* ── Header ── */}
        <div className="relative mb-8">
          <div className="absolute -top-8 -left-8 w-64 h-64 bg-primary-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="relative flex items-start gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-primary-500/20 mt-1">
              <User className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                প্রোফাইল
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">Profile Settings</p>
            </div>
          </div>
        </div>

        {/* ── User Info Card ── */}
        <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6 mb-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary-400" />
            Account Information
          </h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary-500 to-emerald-500 flex items-center justify-center text-2xl shadow-md shrink-0">
                👤
              </div>
              <div className="flex-1 min-w-0">
                {/* Username row */}
                {editingUsername ? (
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={newUsername}
                        onChange={(e) => { setNewUsername(e.target.value); setUsernameError(''); }}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleUsernameSave(); if (e.key === 'Escape') cancelEditUsername(); }}
                        maxLength={50}
                        autoFocus
                        className="flex-1 bg-gray-800/80 border border-gray-700 focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/20 rounded-lg px-3 py-1.5 text-sm text-white outline-none transition-all"
                        placeholder="New username"
                      />
                      <button
                        onClick={handleUsernameSave}
                        disabled={usernameSaving}
                        className="p-1.5 rounded-lg bg-primary-500/20 border border-primary-500/40 text-primary-400 hover:bg-primary-500/30 disabled:opacity-50 transition-all"
                        title="Save"
                      >
                        {usernameSaving
                          ? <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                          : <Check className="w-3.5 h-3.5" />
                        }
                      </button>
                      <button
                        onClick={cancelEditUsername}
                        className="p-1.5 rounded-lg bg-gray-800/80 border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-all"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {usernameError && (
                      <p className="text-[11px] text-red-400">{usernameError}</p>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-semibold text-white truncate">{user?.username}</p>
                    {usernameSaved && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                        <CheckCircle className="w-3 h-3" /> Saved
                      </span>
                    )}
                    <button
                      onClick={startEditUsername}
                      className="ml-1 p-1 rounded-md text-gray-600 hover:text-gray-300 hover:bg-gray-800 transition-all"
                      title="Change username"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
                <div className="flex items-center gap-2 mt-0.5">
                  <Mail className="w-3.5 h-3.5 text-gray-500 shrink-0" />
                  <p className="text-sm text-gray-400 truncate">{user?.email}</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-gray-800/50">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium ${
                user?.role === 'admin'
                  ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                  : 'bg-primary-500/10 text-primary-400 border border-primary-500/20'
              }`}>
                <Shield className="w-3 h-3" />
                {user?.role === 'admin' ? 'Administrator' : 'User'}
              </span>
            </div>
          </div>
        </div>

        {/* ── Category Priority ── */}
        <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <ListOrdered className="w-4 h-4 text-primary-400" />
              ক্যাটাগরি অগ্রাধিকার
            </h3>
            <button
              onClick={handleSave}
              disabled={saving}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-300 ${
                saved
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-primary-500 text-white hover:bg-primary-600 shadow-md shadow-primary-500/20'
              } disabled:opacity-50`}
            >
              {saving ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                  Saving…
                </>
              ) : saved ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5" />
                  Saved!
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  Save
                </>
              )}
            </button>
          </div>
          <p className="text-[11px] text-gray-500 mb-5">
            Category Priority — Drag or use arrows to reorder. Articles page will show categories in this order.
          </p>

          <div className="space-y-2.5">
            {orderedCategories.map((catKey, idx) => {
              const meta = getCategoryMeta(catKey);
              if (!meta) return null;
              return (
                <div
                  key={catKey}
                  draggable
                  onDragStart={() => handleDragStart(idx)}
                  onDragOver={(e) => handleDragOver(e, idx)}
                  onDragEnd={handleDragEnd}
                  className={`flex items-center gap-3 p-3.5 rounded-xl border transition-all duration-200 cursor-grab active:cursor-grabbing ${
                    draggedIdx === idx
                      ? 'border-primary-500/50 bg-primary-500/5 scale-[1.02] shadow-lg shadow-primary-500/10 opacity-60'
                      : dragOverIdx === idx && draggedIdx !== null
                      ? 'border-primary-400/60 bg-primary-500/10 ring-2 ring-primary-500/20'
                      : 'border-gray-800/60 bg-gray-900/60 hover:border-gray-700 hover:bg-gray-900/80'
                  }`}
                >
                  {/* Drag handle */}
                  <GripVertical className="w-4 h-4 text-gray-600 shrink-0" />

                  {/* Priority number */}
                  <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${meta.gradient} flex items-center justify-center text-white font-bold text-sm shadow-md shrink-0`}>
                    {idx + 1}
                  </div>

                  {/* Category info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{meta.icon}</span>
                      <span className="text-sm font-semibold text-white">{meta.label}</span>
                      <span className="text-[10px] text-gray-500 font-medium">{meta.sublabel}</span>
                    </div>
                  </div>

                  {/* Up/Down buttons */}
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => moveUp(idx)}
                      disabled={idx === 0}
                      className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                      title="Move up"
                    >
                      <ArrowUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => moveDown(idx)}
                      disabled={idx === orderedCategories.length - 1}
                      className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                      title="Move down"
                    >
                      <ArrowDown className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-[10px] text-gray-600 mt-4 text-center">
            🔢 #1 = সর্বোচ্চ অগ্রাধিকার · Highest priority category appears first in Articles page
          </p>
        </div>

      </div>
    </div>
  );
};

export default ProfilePage;
