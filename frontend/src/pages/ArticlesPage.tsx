import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, type Article } from '../services/api';

const ArticlesPage = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [filters, setFilters] = useState({
    source: '',
    category: '',
    is_biased: '',
    skip: 0,
    limit: 12,
  });
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchArticles();
  }, [filters]);

  const fetchArticles = async () => {
    setLoading(true);
    try {
      const params: any = { ...filters };
      if (params.is_biased !== '') {
        params.is_biased = params.is_biased === 'true';
      } else {
        delete params.is_biased;
      }
      if (!params.source) delete params.source;
      if (!params.category) delete params.category;

      const response = await api.getArticles(params);
      setArticles(response.articles);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to fetch articles:', error);
    } finally {
      setLoading(false);
    }
  };

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
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return 'N/A';
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'N/A';
    }
  };

  const handleBiasCheck = async (articleId: number, e: React.MouseEvent) => {
    e.preventDefault(); // Prevent navigation
    e.stopPropagation();
    
    if (processingIds.has(articleId)) return;

    setProcessingIds(prev => new Set(prev).add(articleId));
    
    try {
      const updatedArticle = await api.processArticle(articleId);
      
      // Update the article in the list
      setArticles(prevArticles =>
        prevArticles.map(article =>
          article.id === articleId ? updatedArticle : article
        )
      );
    } catch (error) {
      console.error('Failed to process article:', error);
      alert('Failed to analyze article. Please try again.');
    } finally {
      setProcessingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(articleId);
        return newSet;
      });
    }
  };

  const getBiasColor = (score: number) => {
    if (score >= 70) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (score >= 40) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    return 'text-green-400 bg-green-500/10 border-green-500/30';
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">
            <span className="text-white">📰 </span>
            <span className="bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
              Articles Database
            </span>
            </h1>
          <p className="text-gray-400">Browse and analyze scraped articles</p>
        </div>

        {/* Filters */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                Category
              </label>
              <select
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">All Categories</option>
                <option value="রাজনীতি">রাজনীতি</option>
                <option value="বিশ্ব">বিশ্ব</option>
                <option value="মতামত">মতামত</option>
                <option value="বাংলাদেশ">বাংলাদেশ</option>
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
        <div className="mb-4 text-gray-400">
          Showing {filters.skip + 1}-{Math.min(filters.skip + filters.limit, total)} of {total} articles
        </div>

        {/* Loading State */}
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
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-300">
                      {article.source.replace('_', ' ')}
                    </span>
                    {article.category && (
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-primary-500/10 text-primary-400 border border-primary-500/30">
                        {article.category}
                      </span>
                    )}
                  </div>
                  {article.is_biased && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold border ${getBiasColor(
                        article.bias_score
                      )}`}
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
            <p className="text-gray-500">Try adjusting your filters or scrape some articles</p>
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
            <span className="text-gray-400">
              Page {Math.floor(filters.skip / filters.limit) + 1}
            </span>
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

export default ArticlesPage;
