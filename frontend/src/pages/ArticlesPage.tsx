import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, type Article } from '../services/api';

const CATEGORIES = [
  { key: 'রাজনীতি', label: 'রাজনীতি', sublabel: 'Politics', icon: '🏛️', color: 'from-blue-500 to-indigo-600' },
  { key: 'বিশ্ব', label: 'বিশ্ব', sublabel: 'World', icon: '🌍', color: 'from-emerald-500 to-teal-600' },
  { key: 'মতামত', label: 'মতামত', sublabel: 'Opinion', icon: '💬', color: 'from-amber-500 to-orange-600' },
  { key: 'বাংলাদেশ', label: 'বাংলাদেশ', sublabel: 'Bangladesh', icon: '🇧🇩', color: 'from-red-500 to-rose-600' },
];

interface CategoryData {
  articles: Article[];
  total: number;
  loading: boolean;
}

const ArticlesPage = () => {
  const [categoryData, setCategoryData] = useState<Record<string, CategoryData>>({});
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    fetchAllCategories();
  }, []);

  const fetchAllCategories = async () => {
    setInitialLoading(true);
    try {
      const results = await Promise.all(
        CATEGORIES.map(async (cat) => {
          try {
            const response = await api.getArticles({ category: cat.key, limit: 6, skip: 0 });
            return { key: cat.key, articles: response.articles, total: response.total };
          } catch {
            return { key: cat.key, articles: [], total: 0 };
          }
        })
      );

      const data: Record<string, CategoryData> = {};
      results.forEach((r) => {
        data[r.key] = { articles: r.articles, total: r.total, loading: false };
      });
      setCategoryData(data);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    } finally {
      setInitialLoading(false);
    }
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
      setCategoryData((prev) => {
        const updated = { ...prev };
        for (const key of Object.keys(updated)) {
          updated[key] = {
            ...updated[key],
            articles: updated[key].articles.map((a) =>
              a.id === articleId ? updatedArticle : a
            ),
          };
        }
        return updated;
      });
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

  const totalArticles = Object.values(categoryData).reduce((sum, d) => sum + d.total, 0);

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold mb-2">
            <span className="text-white">📰 </span>
            <span className="bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
              Articles Database
            </span>
          </h1>
          <p className="text-gray-400">
            Browse articles by category • {totalArticles} total articles
          </p>
        </div>

        {/* Quick Stats */}
        {!initialLoading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            {CATEGORIES.map((cat) => {
              const data = categoryData[cat.key];
              return (
                <Link
                  key={cat.key}
                  to={`/articles/category/${encodeURIComponent(cat.key)}`}
                  className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-4 hover:border-primary-500/50 transition-all hover:shadow-lg group"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${cat.color} flex items-center justify-center text-lg`}>
                      {cat.icon}
                    </div>
                    <div>
                      <p className="text-white font-semibold group-hover:text-primary-400 transition-colors">
                        {cat.label}
                      </p>
                      <p className="text-gray-500 text-xs">
                        {data?.total || 0} articles
                      </p>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {/* Loading State */}
        {initialLoading && (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
          </div>
        )}

        {/* Category Sections */}
        {!initialLoading &&
          CATEGORIES.map((cat) => {
            const data = categoryData[cat.key];
            if (!data || data.articles.length === 0) return null;

            return (
              <section key={cat.key} className="mb-12">
                {/* Category Header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-lg bg-gradient-to-br ${cat.color} flex items-center justify-center text-lg shadow-lg`}
                    >
                      {cat.icon}
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-white">{cat.label}</h2>
                      <p className="text-gray-500 text-sm">{cat.sublabel} • {data.total} articles</p>
                    </div>
                  </div>
                  {data.total > 6 && (
                    <Link
                      to={`/articles/category/${encodeURIComponent(cat.key)}`}
                      className="flex items-center gap-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-primary-400 hover:text-primary-300 rounded-lg text-sm font-medium transition-all group"
                    >
                      <span>See More</span>
                      <span className="group-hover:translate-x-1 transition-transform">»</span>
                    </Link>
                  )}
                </div>

                {/* Articles Grid — 6 cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {data.articles.slice(0, 6).map((article) => (
                    <Link
                      key={article.id}
                      to={`/article/${article.id}`}
                      className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-5 hover:border-primary-500/50 transition-all hover:shadow-lg hover:shadow-primary-500/10 group"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between mb-3">
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-300">
                          {article.source.replace('_', ' ')}
                        </span>
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
                      <h3 className="text-base font-semibold text-white mb-2 line-clamp-2 group-hover:text-primary-400 transition-colors">
                        {article.title || 'Untitled'}
                      </h3>

                      {/* Content Preview */}
                      <p className="text-sm text-gray-400 mb-3 line-clamp-2">
                        {article.original_content}
                      </p>

                      {/* Footer */}
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>📅 {formatDate(article.scraped_at)}</span>
                        {article.total_changes > 0 && (
                          <span className="text-yellow-400">✏️ {article.total_changes}</span>
                        )}
                      </div>

                      {/* Status */}
                      {!article.processed ? (
                        <button
                          onClick={(e) => handleBiasCheck(article.id, e)}
                          disabled={processingIds.has(article.id)}
                          className="mt-3 w-full px-3 py-1.5 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center space-x-2"
                        >
                          {processingIds.has(article.id) ? (
                            <>
                              <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-white"></div>
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

                {/* See More link at bottom for mobile */}
                {data.total > 6 && (
                  <div className="mt-4 text-center md:hidden">
                    <Link
                      to={`/articles/category/${encodeURIComponent(cat.key)}`}
                      className="inline-flex items-center gap-1 text-primary-400 hover:text-primary-300 text-sm font-medium"
                    >
                      See all {data.total} articles »
                    </Link>
                  </div>
                )}
              </section>
            );
          })}

        {/* Empty State */}
        {!initialLoading && totalArticles === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📭</div>
            <h3 className="text-2xl font-bold text-gray-300 mb-2">No Articles Found</h3>
            <p className="text-gray-500">Scrape some articles to get started</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ArticlesPage;
