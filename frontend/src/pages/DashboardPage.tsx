import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, type Article } from '../services/api';
import { ChevronRight } from 'lucide-react';

const DashboardPage = () => {
  const [loading, setLoading] = useState(true);
  const [analyzedArticles, setAnalyzedArticles] = useState<Article[]>([]);

  useEffect(() => {
    fetchAnalyzedArticles();
  }, []);

  const fetchAnalyzedArticles = async () => {
    setLoading(true);
    try {
      const result = await api.getArticles({ processed: true, limit: 20, skip: 0 });
      setAnalyzedArticles(result.articles || []);
    } catch (error) {
      console.error('Failed to fetch analyzed articles:', error);
    } finally {
      setLoading(false);
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
          <p className="text-gray-400">Your analyzed articles history</p>
        </div>

        {/* Recently Analyzed Articles */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
              <span>🔬</span>
              <span>Recently Analyzed Articles</span>
            </h2>
            <Link
              to="/articles"
              className="inline-flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-primary-400 transition-colors"
            >
              View All <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {analyzedArticles.length === 0 ? (
            <div className="text-center py-10">
              <div className="text-4xl mb-3">🔍</div>
              <p className="text-gray-400 text-sm">No articles analyzed yet. Go to Articles and click "Analyze" on any article.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {analyzedArticles.slice(0, 10).map((article) => {
                const biasColor = article.is_biased
                  ? article.bias_score >= 70
                    ? 'text-red-400 bg-red-500/10 border-red-500/30'
                    : article.bias_score >= 40
                    ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                    : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                  : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
                return (
                  <Link
                    key={article.id}
                    to={`/article/${article.id}`}
                    className="flex items-center gap-4 p-3.5 rounded-xl border border-gray-800/50 bg-gray-800/20 hover:bg-gray-800/40 hover:border-gray-700 transition-all group"
                  >
                    {/* Bias indicator */}
                    <div className={`shrink-0 w-12 h-12 rounded-lg border flex items-center justify-center text-xs font-bold ${biasColor}`}>
                      {article.is_biased ? `${article.bias_score.toFixed(0)}%` : '✓'}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-gray-200 truncate group-hover:text-white transition-colors">
                        {article.title || 'Untitled'}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[11px] text-gray-500 capitalize">{article.source.replace('_', ' ')}</span>
                        <span className="text-gray-700">·</span>
                        <span className="text-[11px] text-gray-500">{article.category || 'Uncategorized'}</span>
                      </div>
                    </div>

                    {/* Timestamp */}
                    <div className="shrink-0 text-right">
                      <p className="text-[11px] text-gray-500">
                        {article.processed_at
                          ? new Date(article.processed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                          : ''}
                      </p>
                      <p className="text-[10px] text-gray-600">
                        {article.processed_at
                          ? new Date(article.processed_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                          : ''}
                      </p>
                    </div>

                    {/* Arrow */}
                    <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 shrink-0 transition-colors" />
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
