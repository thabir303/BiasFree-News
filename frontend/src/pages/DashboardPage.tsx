import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { authApi, api, type UserAnalysis, type SchedulerStatus, type BookmarkWithArticle } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { ChevronRight, Trash2, FileText, Clock, Play, Pause, Settings, RefreshCw, ChevronLeft, Zap, Bookmark } from 'lucide-react';
import { SOURCE_LABELS, SOURCE_COLORS } from '../constants/sources';
import ConfirmDialog from '../components/ConfirmDialog';
import usePageTitle from '../hooks/usePageTitle';

const DashboardPage = () => {
  usePageTitle('Dashboard');
  const { isAdmin } = useAuth();
  const [loading, setLoading] = useState(true);
  const [analyses, setAnalyses] = useState<UserAnalysis[]>([]);
  const [total, setTotal] = useState(0);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);

  // Scheduler state (admin only)
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [scheduleHour, setScheduleHour] = useState(6);
  const [scheduleMinute, setScheduleMinute] = useState(0);
  const [schedulerMessage, setSchedulerMessage] = useState('');
  const [schedulerError, setSchedulerError] = useState('');
  const [toggleLoading, setToggleLoading] = useState(false);
  const [reprocessLoading, setReprocessLoading] = useState(false);
  const [reprocessMessage, setReprocessMessage] = useState('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  // Bookmarks state
  const [bookmarks, setBookmarks] = useState<BookmarkWithArticle[]>([]);
  const [bookmarksTotal, setBookmarksTotal] = useState(0);
  const [bookmarksLoading, setBookmarksLoading] = useState(true);
  const [removingBookmark, setRemovingBookmark] = useState<number | null>(null);

  useEffect(() => {
    fetchAnalyses();
    fetchBookmarks();
    if (isAdmin) {
      fetchSchedulerStatus();
    }
  }, [isAdmin, currentPage]);

  const fetchBookmarks = async () => {
    setBookmarksLoading(true);
    try {
      const result = await authApi.getBookmarks();
      setBookmarks(result.bookmarks);
      setBookmarksTotal(result.total);
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error);
    } finally {
      setBookmarksLoading(false);
    }
  };

  const handleRemoveBookmark = async (articleId: number) => {
    setRemovingBookmark(articleId);
    try {
      await authApi.removeBookmark(articleId);
      setBookmarks(prev => prev.filter(b => b.article_id !== articleId));
      setBookmarksTotal(prev => prev - 1);
      toast.success('Bookmark removed');
    } catch (error) {
      console.error('Failed to remove bookmark:', error);
      toast.error('Failed to remove bookmark');
    } finally {
      setRemovingBookmark(null);
    }
  };

  const fetchAnalyses = async () => {
    setLoading(true);
    try {
      const result = await authApi.getMyAnalyses({ limit: pageSize, skip: (currentPage - 1) * pageSize });
      setAnalyses(result.analyses || []);
      setTotal(result.total || 0);
    } catch (error) {
      console.error('Failed to fetch user analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedulerStatus = async () => {
    try {
      const status = await api.getSchedulerStatus();
      setSchedulerStatus(status);
      // Parse hour/minute from schedule string like "Daily at 06:00 BDT"
      const match = status.schedule?.match(/(\d{2}):(\d{2})/);
      if (match) {
        setScheduleHour(parseInt(match[1]));
        setScheduleMinute(parseInt(match[2]));
      }
    } catch (error) {
      console.error('Failed to fetch scheduler status:', error);
    }
  };

  const handleUpdateScheduler = async () => {
    setSchedulerLoading(true);
    setSchedulerMessage('');
    setSchedulerError('');
    try {
      const result = await api.updateScheduler(scheduleHour, scheduleMinute);
      setSchedulerMessage(result.message || 'Scheduler updated successfully!');
      fetchSchedulerStatus();
    } catch (error: any) {
      setSchedulerError(error.response?.data?.detail || 'Failed to update scheduler');
    } finally {
      setSchedulerLoading(false);
    }
  };

  const handleToggleScheduler = async () => {
    setToggleLoading(true);
    setSchedulerMessage('');
    setSchedulerError('');
    try {
      const result = await api.toggleScheduler();
      setSchedulerMessage(result.message);
      fetchSchedulerStatus();
    } catch (error: any) {
      setSchedulerError(error.response?.data?.detail || 'Failed to toggle scheduler');
    } finally {
      setToggleLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await authApi.deleteAnalysis(id);
      setAnalyses(prev => prev.filter(a => a.id !== id));
      setTotal(prev => prev - 1);
      setDeleteTarget(null);
      toast.success('Analysis deleted');
    } catch (error) {
      console.error('Failed to delete analysis:', error);
      toast.error('Failed to delete analysis');
      setDeleteTarget(null);
    }
  };

  const handleReprocessAll = async () => {
    setReprocessLoading(true);
    setReprocessMessage('');
    try {
      const result = await api.reprocessAllBiased(50);
      setReprocessMessage(result.message || 'Reprocessing complete!');
    } catch (error: any) {
      setReprocessMessage(error.response?.data?.detail || 'Failed to reprocess articles');
    } finally {
      setReprocessLoading(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">📊 Dashboard</h1>
          <p className="text-gray-400">Your personal analysis history</p>
        </div>

        {/* Admin Scheduler Control */}
        {isAdmin && (
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-md">
                <Settings className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Scheduler Control</h2>
                <p className="text-xs text-gray-500">Manage automated daily scraping schedule</p>
              </div>
            </div>

            {/* Current Status */}
            {schedulerStatus && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
                  <p className="text-xs text-gray-500 mb-1">Status</p>
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${schedulerStatus.running ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                    <span className={`text-sm font-semibold ${schedulerStatus.running ? 'text-green-400' : 'text-red-400'}`}>
                      {schedulerStatus.running ? 'Running' : 'Paused'}
                    </span>
                  </div>
                  <button
                    onClick={handleToggleScheduler}
                    disabled={toggleLoading}
                    className={`mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 ${
                      schedulerStatus.running
                        ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30'
                        : 'bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30'
                    }`}
                  >
                    {toggleLoading ? (
                      <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : schedulerStatus.running ? (
                      <Pause className="w-3 h-3" />
                    ) : (
                      <Play className="w-3 h-3" />
                    )}
                    {schedulerStatus.running ? 'Pause' : 'Resume'}
                  </button>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
                  <p className="text-xs text-gray-500 mb-1">Current Schedule</p>
                  <p className="text-sm font-semibold text-white flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-amber-400" />
                    {schedulerStatus.schedule || 'Not set'}
                  </p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
                  <p className="text-xs text-gray-500 mb-1">Next Run</p>
                  <p className="text-sm font-semibold text-white">
                    {schedulerStatus.next_run
                      ? new Date(schedulerStatus.next_run).toLocaleString('en-US', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        })
                      : 'N/A'}
                  </p>
                </div>
              </div>
            )}

            {/* Last Run Info */}
            {schedulerStatus?.last_run && (
              <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/30 mb-6">
                <p className="text-xs text-gray-500 mb-2 font-medium">Last Run</p>
                <div className="flex items-center gap-4 text-sm">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                    schedulerStatus.last_run.status === 'success' ? 'bg-green-500/20 text-green-400' :
                    schedulerStatus.last_run.status === 'partial' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {schedulerStatus.last_run.status?.toUpperCase()}
                  </span>
                  <span className="text-gray-400">
                    {schedulerStatus.last_run.articles_scraped} articles scraped
                  </span>
                  {schedulerStatus.last_run.started_at && (
                    <span className="text-gray-500 text-xs">
                      {new Date(schedulerStatus.last_run.started_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Update Schedule Form */}
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1.5 font-medium">Hour (BDT, 0-23)</label>
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={scheduleHour}
                  onChange={(e) => setScheduleHour(Math.min(23, Math.max(0, parseInt(e.target.value) || 0)))}
                  className="w-20 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5 font-medium">Minute (0-59)</label>
                <input
                  type="number"
                  min={0}
                  max={59}
                  value={scheduleMinute}
                  onChange={(e) => setScheduleMinute(Math.min(59, Math.max(0, parseInt(e.target.value) || 0)))}
                  className="w-20 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                />
              </div>
              <button
                onClick={handleUpdateScheduler}
                disabled={schedulerLoading}
                className="inline-flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg font-semibold text-sm hover:from-amber-600 hover:to-orange-600 transition-all disabled:opacity-50"
              >
                {schedulerLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                {schedulerLoading ? 'Updating...' : 'Update Schedule'}
              </button>
              <button
                onClick={fetchSchedulerStatus}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-800 text-gray-300 rounded-lg text-sm hover:bg-gray-700 transition border border-gray-700"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            </div>

            {/* Messages */}
            {schedulerMessage && (
              <div className="mt-4 bg-green-500/20 border border-green-500/50 text-green-300 px-4 py-2.5 rounded-lg text-sm">
                {schedulerMessage}
              </div>
            )}
            {schedulerError && (
              <div className="mt-4 bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-2.5 rounded-lg text-sm">
                {schedulerError}
              </div>
            )}

            {/* Reprocess All Biased */}
            <div className="mt-6 pt-4 border-t border-gray-800/50">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleReprocessAll}
                  disabled={reprocessLoading}
                  className="inline-flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white rounded-lg font-semibold text-sm hover:from-violet-600 hover:to-fuchsia-600 transition-all disabled:opacity-50"
                >
                  {reprocessLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  {reprocessLoading ? 'Reprocessing...' : 'Reprocess All Biased Articles'}
                </button>
                <span className="text-xs text-gray-500">Re-analyze biased articles with 0 changes</span>
              </div>
              {reprocessMessage && (
                <p className="mt-2 text-sm text-gray-300 bg-gray-800/50 rounded-lg px-4 py-2">{reprocessMessage}</p>
              )}
            </div>
          </div>
        )}

        {/* Saved Articles (Bookmarks) */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center shadow-md">
                <Bookmark className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Saved Articles</h2>
                <p className="text-xs text-gray-500">{bookmarksTotal} article{bookmarksTotal !== 1 ? 's' : ''} bookmarked</p>
              </div>
            </div>
            <Link
              to="/articles"
              className="inline-flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-primary-400 transition-colors px-3 py-1.5 rounded-lg border border-gray-800/60 hover:border-gray-600"
            >
              Browse Articles <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {bookmarksLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center gap-4 p-4 rounded-xl border border-gray-800/50 bg-gray-800/20 animate-pulse">
                  <div className="w-12 h-12 rounded-lg bg-gray-800" />
                  <div className="flex-1"><div className="h-4 w-3/4 rounded bg-gray-800 mb-2" /><div className="h-3 w-1/2 rounded bg-gray-800/60" /></div>
                </div>
              ))}
            </div>
          ) : bookmarks.length === 0 ? (
            <div className="text-center py-14">
              <div className="text-5xl mb-4">🔖</div>
              <p className="text-gray-300 font-medium mb-1">No saved articles</p>
              <p className="text-gray-500 text-sm">Browse <Link to="/articles" className="text-primary-400 hover:underline">Articles</Link> and click the bookmark icon to save articles here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {bookmarks.map((bookmark) => {
                const article = bookmark.article;
                if (!article) return null;
                const sourceLabel = SOURCE_LABELS[article.source] || article.source;
                const sourceColor = SOURCE_COLORS[article.source] || 'bg-gray-500';

                return (
                  <Link
                    key={bookmark.id}
                    to={`/article/${article.id}`}
                    className="flex items-center gap-4 p-4 rounded-xl border border-gray-800/50 bg-gray-800/20 hover:bg-gray-800/40 hover:border-gray-700 transition-all group"
                  >
                    {/* Bias/source indicator */}
                    <div className="shrink-0 w-12 h-12 rounded-lg border border-gray-700/50 bg-gray-800/50 flex flex-col items-center justify-center gap-0.5">
                      <span className={`w-2.5 h-2.5 rounded-full ${sourceColor}`} />
                      {article.processed && article.is_biased !== null && (
                        <span className={`text-[9px] font-bold ${article.is_biased ? 'text-red-400' : 'text-emerald-400'}`}>
                          {article.bias_score !== null ? `${article.bias_score.toFixed(0)}%` : '✓'}
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <h4 className="text-sm font-medium text-gray-200 truncate group-hover:text-white transition-colors">
                          {article.title || 'Untitled'}
                        </h4>
                        <span className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          🔖 Saved
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-gray-500 font-medium">{sourceLabel}</span>
                        {article.category && (
                          <>
                            <span className="text-gray-700">·</span>
                            <span className="text-[11px] text-gray-500">{article.category}</span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Saved date */}
                    <div className="shrink-0 text-right">
                      <p className="text-[11px] text-gray-500">
                        {new Date(bookmark.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </p>
                    </div>

                    {/* Remove bookmark */}
                    <button
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleRemoveBookmark(article.id); }}
                      disabled={removingBookmark === article.id}
                      className="shrink-0 p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100 disabled:opacity-40"
                      title="Remove bookmark"
                    >
                      {removingBookmark === article.id ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Manual Analysis History */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-md">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Manual Analysis History</h2>
                <p className="text-xs text-gray-500">{total} analysis{total !== 1 ? 'es' : ''} saved</p>
              </div>
            </div>
            <Link
              to="/"
              className="inline-flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-primary-400 transition-colors px-3 py-1.5 rounded-lg border border-gray-800/60 hover:border-gray-600"
            >
              New Analysis <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {analyses.length === 0 ? (
            <div className="text-center py-14">
              <div className="text-5xl mb-4">🔬</div>
              <p className="text-gray-300 font-medium mb-1">No analyses yet</p>
              <p className="text-gray-500 text-sm">Go to <Link to="/" className="text-primary-400 hover:underline">Analyze</Link> and check any article for bias. Your results will appear here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {analyses.map((analysis) => {
                const biasColor = analysis.is_biased
                  ? (analysis.bias_score ?? 0) >= 70
                    ? 'text-red-400 bg-red-500/10 border-red-500/30'
                    : (analysis.bias_score ?? 0) >= 40
                    ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                    : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                  : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';

                return (
                  <Link
                    key={analysis.id}
                    to={`/analysis/${analysis.id}`}
                    className="flex items-center gap-4 p-4 rounded-xl border border-gray-800/50 bg-gray-800/20 hover:bg-gray-800/40 hover:border-gray-700 transition-all group"
                  >
                    {/* Bias score indicator */}
                    <div className={`shrink-0 w-12 h-12 rounded-lg border flex items-center justify-center text-xs font-bold ${biasColor}`}>
                      {analysis.is_biased ? `${(analysis.bias_score ?? 0).toFixed(0)}%` : '✓'}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <h4 className="text-sm font-medium text-gray-200 truncate group-hover:text-white transition-colors">
                          {analysis.title || 'Untitled Article'}
                        </h4>
                        <span className="shrink-0 px-2 py-0.5 text-[10px] font-semibold rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/30">
                          Manual
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-gray-500">
                          {analysis.total_changes ?? 0} change{(analysis.total_changes ?? 0) !== 1 ? 's' : ''}
                        </span>
                        <span className="text-gray-700">·</span>
                        <span className="text-[11px] text-gray-500">
                          {analysis.processing_time ? `${analysis.processing_time.toFixed(1)}s` : ''}
                        </span>
                        {analysis.recommended_headline && (
                          <>
                            <span className="text-gray-700">·</span>
                            <span className="text-[11px] text-gray-500 truncate max-w-[200px]">
                              {analysis.recommended_headline}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Timestamp */}
                    <div className="shrink-0 text-right">
                      <p className="text-[11px] text-gray-500">
                        {new Date(analysis.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </p>
                      <p className="text-[10px] text-gray-600">
                        {new Date(analysis.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>

                    {/* Delete button */}
                    <button
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteTarget(analysis.id); }}
                      className="shrink-0 p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                      title="Delete analysis"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-3 mt-6 pt-4 border-t border-gray-800/40">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-400 border border-gray-800 hover:border-gray-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </button>
              <span className="text-sm text-gray-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage >= totalPages}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-400 border border-gray-800 hover:border-gray-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete Analysis"
        message="Are you sure you want to delete this analysis? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => deleteTarget !== null && handleDelete(deleteTarget)}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

export default DashboardPage;
