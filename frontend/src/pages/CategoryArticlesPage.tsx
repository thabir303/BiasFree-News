import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { api, type Article } from '../services/api';

const CATEGORY_LABELS: Record<string, string> = {
  'রাজনীতি': '🏛️ রাজনীতি (Politics)',
  'বিশ্ব': '🌍 বিশ্ব (World)',
  'মতামত': '💬 মতামত (Opinion)',
  'বাংলাদেশ': '🇧🇩 বাংলাদেশ (Bangladesh)',
};

const CategoryArticlesPage = () => {
  const { categoryName } = useParams<{ categoryName: string }>();
  const navigate = useNavigate();
  const decodedCategory = categoryName ? decodeURIComponent(categoryName) : '';

  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({
    source: '',
    is_biased: '',
    skip: 0,
    limit: 12,
  });

  const fetchArticles = useCallback(async () => {
    if (!decodedCategory) return;
    setLoading(true);
    try {
      const params: any = {
        category: decodedCategory,
        skip: filters.skip,
        limit: filters.limit,
      };
      if (filters.source) params.source = filters.source;
      if (filters.is_biased !== '') {
        params.is_biased = filters.is_biased === 'true';
      }

      const response = await api.getArticles(params);
      setArticles(response.articles);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to fetch articles:', error);
    } finally {
      setLoading(false);
    }
  }, [decodedCategory, filters]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  const handleFilterChange = (key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value, skip: 0 }));
  };

  const handlePageChange = (direction: 'next' | 'prev') => {
    setFilters((prev) => ({
      ...prev,
      skip: direction === 'next' ? prev.skip + prev.limit : Math.max(0, prev.skip - prev.limit),
    }));
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return 'N/A';
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return 'N/A';
    }
  };

  const handleBiasCheck = async (articleId: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (processingIds.has(articleId)) return;

    setProcessingIds((prev) => new Set(prev).add(articleId));
    try {
      const updatedArticle = await api.processArticle(articleId);
      setArticles((prev) => prev.map((a) => (a.id === articleId ? updatedArticle : a)));
    } catch (error) {
      console.error('Failed to process article:', error);
      alert('Failed to analyze article. Please try again.');
    } finally {
      setProcessingIds((prev) => {
        const s = new Set(prev);
        s.delete(articleId);
        return s;
      });
    }
  };

  const getBiasColor = (score: number) => {
    if (score >= 70) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (score >= 40) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    return 'text-green-400 bg-green-500/10 border-green-500/30';
  };

  const totalPages = Math.ceil(total / filters.limit);
  const currentPage = Math.floor(filters.skip / filters.limit) + 1;

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Back Button + Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/articles')}
            className="flex items-center gap-2 text-gray-400 hover:text-primary-400 transition-colors mb-4 group"
          >
            <span className="group-hover:-translate-x-1 transition-transform">←</span>
            <span>Back to All Categories</span>
          </button>
          <h1 className="text-4xl font-bold mb-2">
            <span className="bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
              {CATEGORY_LABELS[decodedCategory] || decodedCategory}
            </span>
          </h1>
          <p className="text-gray-400">
            {total} article{total !== 1 ? 's' : ''} in this category
          </p>
        </div>

        {/* Filters */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Newspaper Source
              </label>
              <select
                value={filters.source}
                onChange={(e) => handleFilterChange('source', e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">All Sources</option>
                <option value="prothom_alo">প্রথম আলো</option>
                <option value="daily_star">Daily Star</option>
                <option value="jugantor">যুগান্তর</option>
                <option value="samakal">সমকাল</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Bias Status
              </label>
              <select
                value={filters.is_biased}
                onChange={(e) => handleFilterChange('is_biased', e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">All Articles</option>
                <option value="true">Biased Only</option>
                <option value="false">Unbiased Only</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Items per Page
              </label>
              <select
                value={filters.limit}
                onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="12">12</option>
                <option value="24">24</option>
                <option value="48">48</option>
              </select>
            </div>
          </div>
        </div>

        {/* Results Count */}
        <div className="mb-4 flex items-center justify-between">
          <span className="text-gray-400">
            Showing {total > 0 ? filters.skip + 1 : 0}–{Math.min(filters.skip + filters.limit, total)} of {total} articles
          </span>
          <span className="text-gray-500 text-sm">
            Page {currentPage} of {totalPages || 1}
          </span>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
          </div>
        )}

        {/* Articles Grid */}
        {!loading && articles.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {articles.map((article) => (
              <Link
                key={article.id}
                to={`/article/${article.id}`}
                className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 hover:border-primary-500/50 transition-all hover:shadow-lg hover:shadow-primary-500/10 group"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-300">
                    {article.source.replace('_', ' ')}
                  </span>
                  {article.is_biased && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold border ${getBiasColor(article.bias_score)}`}
                    >
                      {article.bias_score.toFixed(0)}%
                    </span>
                  )}
                </div>

                {/* Title */}
                <h3 className="text-lg font-semibold text-white mb-2 line-clamp-2 group-hover:text-primary-400 transition-colors">
                  {article.title || 'Untitled'}
                </h3>

                {/* Content Preview */}
                <p className="text-sm text-gray-400 mb-4 line-clamp-3">
                  {article.original_content}
                </p>

                {/* Stats */}
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>📅 {formatDate(article.scraped_at)}</span>
                  {article.total_changes > 0 && (
                    <span className="text-yellow-400">✏️ {article.total_changes} changes</span>
                  )}
                </div>

                {/* Status Badge or Action Button */}
                {!article.processed ? (
                  <button
                    onClick={(e) => handleBiasCheck(article.id, e)}
                    disabled={processingIds.has(article.id)}
                    className="mt-3 w-full px-4 py-2 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center space-x-2"
                  >
                    {processingIds.has(article.id) ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></div>
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <span>🔍</span>
                        <span>Check for Bias</span>
                      </>
                    )}
                  </button>
                ) : article.is_biased ? (
                  <div className="mt-3 px-3 py-1 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400 text-center">
                    ⚠️ Bias Detected ({article.bias_score.toFixed(0)}%)
                  </div>
                ) : (
                  <div className="mt-3 px-3 py-1 bg-green-500/10 border border-green-500/30 rounded-lg text-xs text-green-400 text-center">
                    ✅ No Bias Detected
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && articles.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📭</div>
            <h3 className="text-2xl font-bold text-gray-300 mb-2">No Articles Found</h3>
            <p className="text-gray-500">Try adjusting your filters or scrape some articles first</p>
          </div>
        )}

        {/* Pagination */}
        {!loading && articles.length > 0 && (
          <div className="flex justify-center items-center space-x-4">
            <button
              onClick={() => handlePageChange('prev')}
              disabled={filters.skip === 0}
              className="px-6 py-2 bg-gray-800 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition-colors"
            >
              ← Previous
            </button>

            {/* Page Numbers */}
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 7) {
                  pageNum = i + 1;
                } else if (currentPage <= 4) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 3) {
                  pageNum = totalPages - 6 + i;
                } else {
                  pageNum = currentPage - 3 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() =>
                      setFilters((prev) => ({ ...prev, skip: (pageNum - 1) * prev.limit }))
                    }
                    className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                      pageNum === currentPage
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => handlePageChange('next')}
              disabled={filters.skip + filters.limit >= total}
              className="px-6 py-2 bg-gray-800 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition-colors"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CategoryArticlesPage;
