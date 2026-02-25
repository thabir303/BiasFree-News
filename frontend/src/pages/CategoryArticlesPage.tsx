import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, authApi, type Article } from '../services/api';
import ArticleFilters from '../components/ArticleFilters';
import ArticlePagination from '../components/ArticlePagination';
import { useArticleFilters } from '../hooks/useArticleFilters';
import { CATEGORY_META } from '../constants/sources';
import usePageTitle from '../hooks/usePageTitle';
import ArticleCard from '../components/ArticleCard';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

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
  usePageTitle(categoryName ? decodeURIComponent(categoryName) : 'Category');
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const decodedCategory = categoryName ? decodeURIComponent(categoryName) : '';

  const meta = CATEGORY_META[decodedCategory] || { icon: '📰', text: decodedCategory, gradient: 'from-gray-500 to-gray-600' };

  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [total, setTotal] = useState(0);
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set());
  const [savingIds, setSavingIds] = useState<Set<number>>(new Set());
  
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
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.search) params.search = filters.search;
      if (filters.sort_by) params.sort_by = filters.sort_by;
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

  useEffect(() => {
    if (isAuthenticated) {
      authApi.getBookmarks().then(result => {
        setSavedIds(new Set(result.bookmarks.map(b => b.article_id)));
      }).catch(() => {});
    }
  }, [isAuthenticated]);

  const handleToggleSave = async (articleId: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (savingIds.has(articleId)) return;
    setSavingIds(prev => new Set(prev).add(articleId));
    try {
      if (savedIds.has(articleId)) {
        await authApi.removeBookmark(articleId);
        setSavedIds(prev => { const s = new Set(prev); s.delete(articleId); return s; });
        toast.success('Bookmark removed');
      } else {
        await authApi.addBookmark(articleId);
        setSavedIds(prev => new Set(prev).add(articleId));
        toast.success('Article saved!');
      }
    } catch (error) {
      console.error('Failed to toggle bookmark:', error);
      toast.error('Failed to save article');
    } finally {
      setSavingIds(prev => { const s = new Set(prev); s.delete(articleId); return s; });
    }
  };

  const handlePageChangeWithScroll = (direction: 'next' | 'prev') => {
    handlePageChange(direction);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDirectPageChangeWithScroll = (page: number) => {
    handleDirectPageChange(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
            {articles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                onBiasCheck={handleBiasCheck}
                processingIds={processingIds}
                isSaved={savedIds.has(article.id)}
                onToggleSave={isAuthenticated ? handleToggleSave : undefined}
                savingIds={savingIds}
              />
            ))}
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
