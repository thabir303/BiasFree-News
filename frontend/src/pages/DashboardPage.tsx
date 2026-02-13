import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { authApi, type UserAnalysis } from '../services/api';
import { ChevronRight, Trash2, FileText } from 'lucide-react';

const DashboardPage = () => {
  const [loading, setLoading] = useState(true);
  const [analyses, setAnalyses] = useState<UserAnalysis[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchAnalyses();
  }, []);

  const fetchAnalyses = async () => {
    setLoading(true);
    try {
      const result = await authApi.getMyAnalyses({ limit: 30 });
      setAnalyses(result.analyses || []);
      setTotal(result.total || 0);
    } catch (error) {
      console.error('Failed to fetch user analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await authApi.deleteAnalysis(id);
      setAnalyses(prev => prev.filter(a => a.id !== id));
      setTotal(prev => prev - 1);
    } catch (error) {
      console.error('Failed to delete analysis:', error);
    }
  };
  
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
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(analysis.id); }}
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
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
