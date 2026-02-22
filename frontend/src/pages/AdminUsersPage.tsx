import { useState, useEffect, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { adminApi, type AdminUser } from '../services/api';
import { Users, Trash2, ShieldCheck, User as UserIcon, Search, RefreshCw } from 'lucide-react';

const AdminUsersPage = () => {
  const { isAdmin, isAuthenticated } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  if (!isAuthenticated || !isAdmin) {
    return <Navigate to="/" replace />;
  }

  const showToast = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.listUsers({ limit: 200 });
      setUsers(res.users);
      setTotal(res.total);
    } catch (e: any) {
      showToast('Failed to load users', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleDelete = async (userId: number) => {
    setDeletingId(userId);
    try {
      const res = await adminApi.deleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setTotal((prev) => prev - 1);
      showToast(res.message, 'success');
    } catch (e: any) {
      showToast(e?.response?.data?.detail || 'Failed to delete user', 'error');
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  };

  const filtered = users.filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
  );

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return '—';
    }
  };

  return (
    <div className="admin-users-page min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl text-sm font-medium transition-all ${
            toast.type === 'success'
              ? 'bg-emerald-500 text-white'
              : 'bg-red-500 text-white'
          }`}
        >
          <span>{toast.type === 'success' ? '✓' : '✕'}</span>
          {toast.msg}
        </div>
      )}

      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-start gap-4 mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/30 shrink-0 mt-0.5">
            <Users className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold page-title">User Management</h1>
            <p className="text-sm page-subtitle mt-0.5">
              {total > 0 ? `${total} registered user${total !== 1 ? 's' : ''}` : 'Manage platform users'}
            </p>
          </div>
        </div>

        {/* Search + Refresh bar */}
        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 search-icon" />
            <input
              type="text"
              placeholder="Search by username or email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="admin-search-input w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none"
            />
          </div>
          <button
            onClick={fetchUsers}
            disabled={loading}
            className="p-2.5 rounded-xl admin-refresh-btn transition-all"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Table */}
        <div className="admin-table-container rounded-2xl overflow-hidden">
          {/* Table Header */}
          <div className="admin-table-header grid grid-cols-[1fr_1.4fr_90px_80px_80px_60px] gap-4 px-5 py-3 text-[11px] font-semibold uppercase tracking-wider">
            <span>Username</span>
            <span>Email</span>
            <span>Role</span>
            <span>Verified</span>
            <span>Joined</span>
            <span></span>
          </div>

          {/* Body */}
          {loading ? (
            <div className="px-5 py-12 flex justify-center">
              <svg className="animate-spin w-7 h-7 text-violet-500" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          ) : filtered.length === 0 ? (
            <div className="px-5 py-12 text-center admin-empty-text text-sm">
              {search ? 'No users match your search.' : 'No users found.'}
            </div>
          ) : (
            <div className="divide-y admin-table-divider">
              {filtered.map((u) => (
                <div
                  key={u.id}
                  className="admin-table-row grid grid-cols-[1fr_1.4fr_90px_80px_80px_60px] gap-4 items-center px-5 py-4 transition-colors"
                >
                  {/* Username */}
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${u.role === 'admin' ? 'bg-yellow-500/20' : 'bg-violet-500/15'}`}>
                      {u.role === 'admin' ? (
                        <ShieldCheck className="w-4 h-4 text-yellow-400" />
                      ) : (
                        <UserIcon className="w-4 h-4 text-violet-400" />
                      )}
                    </div>
                    <span className="admin-username font-semibold text-sm truncate">{u.username}</span>
                  </div>

                  {/* Email */}
                  <span className="admin-email text-sm truncate">{u.email}</span>

                  {/* Role badge */}
                  <span>
                    {u.role === 'admin' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-yellow-500/15 text-yellow-400 border border-yellow-500/25">
                        Admin
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/20">
                        User
                      </span>
                    )}
                  </span>

                  {/* Verified */}
                  <span>
                    {u.is_verified ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        Yes
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        No
                      </span>
                    )}
                  </span>

                  {/* Joined date */}
                  <span className="admin-date text-[11px]">{formatDate(u.created_at)}</span>

                  {/* Delete */}
                  <div className="flex justify-end">
                    {u.role === 'admin' ? (
                      <span className="text-[10px] admin-protected-label">protected</span>
                    ) : confirmDeleteId === u.id ? (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleDelete(u.id)}
                          disabled={deletingId === u.id}
                          className="px-2 py-1 rounded-lg text-[11px] font-bold bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
                        >
                          {deletingId === u.id ? '…' : 'Yes'}
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          className="px-2 py-1 rounded-lg text-[11px] font-semibold admin-cancel-btn transition-colors"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(u.id)}
                        className="p-1.5 rounded-lg admin-delete-btn transition-all"
                        title={`Remove ${u.username}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {filtered.length > 0 && (
          <p className="admin-footer-note text-[11px] text-center mt-4">
            Showing {filtered.length} of {total} user{total !== 1 ? 's' : ''}.
            Deleted users must sign up again to access the platform.
          </p>
        )}
      </div>
    </div>
  );
};

export default AdminUsersPage;
