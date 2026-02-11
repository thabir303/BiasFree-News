import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { api, type Article } from '../services/api';
import ArticleFilters from '../components/ArticleFilters';
import ArticlePagination from '../components/ArticlePagination';
import { useArticleFilters } from '../hooks/useArticleFilters';

const CATEGORY_META: Record<string, { icon: string; text: string; gradient: string }> = {
  'রাজনীতি': { icon: '🏛️', text: 'রাজনীতি (Politics)', gradient: 'from-blue-500 to-indigo-600' },
  'বিশ্ব':   { icon: '🌍', text: 'বিশ্ব (World)',       gradient: 'from-emerald-500 to-teal-600' },
  'মতামত':   { icon: '💬', text: 'মতামত (Opinion)',     gradient: 'from-amber-500 to-orange-600' },
  'বাংলাদেশ': { icon: '🇧🇩', text: 'বাংলাদেশ (Bangladesh)', gradient: 'from-red-500 to-rose-600' },
};

const SOURCE_LABELS: Record<string, string> = {
  prothom_alo: 'প্রথম আলো',
  daily_star: 'Daily Star',
  jugantor: 'যুগান্তর',
  samakal: 'সমকাল',
};

const SOURCE_COLORS: Record<string, string> = {
  prothom_alo: 'bg-orange-500',
  daily_star: 'bg-sky-500',
  jugantor: 'bg-rose-500',
  samakal: 'bg-violet-500',
};

/* ─── Skeleton ──────────────────────────────────── */
const CardSkeleton = () => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 p-5 animate-pulse">
    <div className="flex items-center gap-2 mb-4">
      <div className="h-5 w-20 rounded-full bg-gray-800" />
    </div>
    <div className="h-5 w-4/5 rounded bg-gray-800 mb-2" />
    <div className="h-5 w-3/5 rounded bg-gray-800 mb-4" />
    <div className="h-4 w-full rounded bg-gray-800/60 mb-2" />
    <div className="h-4 w-5/6 rounded bg-gray-800/60 mb-4" />
    <div className="h-8 w-full rounded-lg bg-gray-800/40" />
  </div>
);

const CategoryArticlesPage = () => {
  const { categoryName } = useParams<{ categoryName: string }>();
  const navigate = useNavigate();
  const decodedCategory = categoryName ? decodeURIComponent(categoryName) : '';

  const meta = CATEGORY_META[decodedCategory] || { icon: '📰', text: decodedCategory, gradient: 'from-gray-500 to-gray-600' };

  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [total, setTotal] = useState(0);
  
  const {
    filters,
    handleFilterChange,
    handleClearAll,
    handlePageChange,
    handleDirectPageChange,
    getCurrentPage,
    getTotalPages,
  } = useArticleFilters();

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

  const handlePageChangeWithScroll = (direction: 'next' | 'prev') => {
    handlePageChange(direction);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDirectPageChangeWithScroll = (page: number) => {
    handleDirectPageChange(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return '';
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
    } finally {
      setProcessingIds((prev) => {
        const s = new Set(prev);
        s.delete(articleId);
        return s;
      });
    }
  };

  const getBiasIndicator = (score: number) => {
    if (score >= 70) return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' };
    if (score >= 40) return { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' };
    return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' };
  };

  const totalPages = getTotalPages(total);
  const currentPage = getCurrentPage();

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* ── Breadcrumb ──────────────────────────── */}
        <nav className="flex items-center gap-1.5 text-xs text-gray-500 mb-8">
          <button
            onClick={() => navigate('/articles')}
            className="hover:text-primary-400 transition-colors"
          >
            Articles
          </button>
          <svg className="w-3 h-3 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
          <span className="text-gray-400 font-medium">{meta.text}</span>
        </nav>

        {/* ── Header ──────────────────────────────── */}
        <div className="relative mb-6">
          <div className={`absolute -top-6 -left-6 w-48 h-48 bg-gradient-to-br ${meta.gradient} opacity-[0.04] rounded-full blur-3xl pointer-events-none`} />
          <div className="relative flex items-center gap-4">
            <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${meta.gradient} flex items-center justify-center text-2xl shadow-lg`}>
              {meta.icon}
            </div>
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                {meta.text}
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                {loading ? 'Loading…' : `${total.toLocaleString()} article${total !== 1 ? 's' : ''} found`}
              </p>
            </div>
          </div>
        </div>

        {/* ── Filters ─────────────────────────────── */}
        <ArticleFilters
          filters={filters}
          onFilterChange={handleFilterChange}
          onClearAll={handleClearAll}
          loading={loading}
        />

        {/* ── Results Info Bar ─────────────────────── */}
        {!loading && total > 0 && (
          <div className="flex items-center justify-between mb-6 px-1">
            <p className="text-xs text-gray-500">
              Showing <span className="text-gray-300 font-medium">{filters.skip + 1}–{Math.min(filters.skip + filters.limit, total)}</span> of <span className="text-gray-300 font-medium">{total.toLocaleString()}</span>
            </p>
            <p className="text-xs text-gray-600">
              Page {currentPage} / {totalPages}
            </p>
          </div>
        )}

        {/* ── Loading ──────────────────────────────── */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        )}

        {/* ── Articles Grid ────────────────────────── */}
        {!loading && articles.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
            {articles.map((article) => {
              const bias = getBiasIndicator(article.bias_score);
              const sourceColor = SOURCE_COLORS[article.source] || 'bg-gray-500';
              const sourceLabel = SOURCE_LABELS[article.source] || article.source;
              const date = formatDate(article.scraped_at);

              return (
                <Link
                  key={article.id}
                  to={`/article/${article.id}`}
                  className="group relative flex flex-col rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-5 transition-all duration-300 hover:border-gray-700 hover:bg-gray-900/60 hover:shadow-xl hover:shadow-black/20 hover:-translate-y-0.5"
                >
                  {/* Top row */}
                  <div className="flex items-center justify-between mb-3.5">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${sourceColor} shrink-0`} />
                      <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                        {sourceLabel}
                      </span>
                    </div>
                    {article.processed && article.is_biased && (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${bias.bg} ${bias.border} ${bias.color}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        {article.bias_score.toFixed(0)}%
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h3 className="text-[15px] font-semibold leading-snug text-gray-100 mb-2 line-clamp-2 group-hover:text-white transition-colors">
                    {article.title || 'Untitled'}
                  </h3>

                  {/* Snippet */}
                  <p className="text-sm leading-relaxed text-gray-500 mb-4 line-clamp-3 flex-1">
                    {article.original_content}
                  </p>

                  {/* Footer */}
                  <div className="mt-auto pt-3 border-t border-gray-800/50 flex items-center justify-between">
                    {date && <span className="text-[11px] text-gray-600 font-medium">{date}</span>}

                    {!article.processed ? (
                      <button
                        onClick={(e) => handleBiasCheck(article.id, e)}
                        disabled={processingIds.has(article.id)}
                        className="ml-auto inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-primary-500/10 text-primary-400 border border-primary-500/20 hover:bg-primary-500/20 hover:border-primary-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                      >
                        {processingIds.has(article.id) ? (
                          <>
                            <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                            Analyzing…
                          </>
                        ) : (
                          <>
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                            Analyze
                          </>
                        )}
                      </button>
                    ) : article.is_biased ? (
                      <span className={`ml-auto inline-flex items-center gap-1 text-[11px] font-medium ${bias.color}`}>
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" /></svg>
                        Bias Detected
                      </span>
                    ) : (
                      <span className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" /></svg>
                        Neutral
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {/* ── Empty State ──────────────────────────── */}
        {!loading && articles.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-20 h-20 rounded-2xl bg-gray-800/60 flex items-center justify-center mb-6">
              <svg className="w-10 h-10 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No articles found</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              Try adjusting your filters or scrape more articles to populate this category.
            </p>
            {[filters.source, filters.is_biased].filter(Boolean).length > 0 && (
              <button
                onClick={handleClearAll}
                className="mt-4 text-sm text-primary-400 hover:text-primary-300 transition-colors"
              >
                Clear all filters
              </button>
            )}
          </div>
        )}

        {/* ── Pagination ───────────────────────────── */}
        <ArticlePagination
          total={total}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handleDirectPageChangeWithScroll}
          onPrevNext={handlePageChangeWithScroll}
          loading={loading}
        />
      </div>
    </div>
  );
};

export default CategoryArticlesPage;
