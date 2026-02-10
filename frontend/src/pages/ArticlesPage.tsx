import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, type Article } from '../services/api';

const CATEGORIES = [
  { key: 'রাজনীতি', label: 'রাজনীতি', sublabel: 'Politics', icon: '🏛️', gradient: 'from-blue-500 to-indigo-600', accent: 'border-blue-500', bg: 'bg-blue-500/5', ring: 'ring-blue-500/20' },
  { key: 'বিশ্ব', label: 'বিশ্ব', sublabel: 'World', icon: '🌍', gradient: 'from-emerald-500 to-teal-600', accent: 'border-emerald-500', bg: 'bg-emerald-500/5', ring: 'ring-emerald-500/20' },
  { key: 'মতামত', label: 'মতামত', sublabel: 'Opinion', icon: '💬', gradient: 'from-amber-500 to-orange-600', accent: 'border-amber-500', bg: 'bg-amber-500/5', ring: 'ring-amber-500/20' },
  { key: 'বাংলাদেশ', label: 'বাংলাদেশ', sublabel: 'Bangladesh', icon: '🇧🇩', gradient: 'from-red-500 to-rose-600', accent: 'border-red-500', bg: 'bg-red-500/5', ring: 'ring-red-500/20' },
];

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

interface CategoryData {
  articles: Article[];
  total: number;
}

/* ─── Skeleton loaders ──────────────────────────────────── */
const CardSkeleton = () => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 p-5 animate-pulse">
    <div className="flex items-center gap-2 mb-4">
      <div className="h-5 w-20 rounded-full bg-gray-800" />
      <div className="h-5 w-14 rounded-full bg-gray-800" />
    </div>
    <div className="h-5 w-4/5 rounded bg-gray-800 mb-2" />
    <div className="h-5 w-3/5 rounded bg-gray-800 mb-4" />
    <div className="h-4 w-full rounded bg-gray-800/60 mb-2" />
    <div className="h-4 w-5/6 rounded bg-gray-800/60 mb-4" />
    <div className="h-8 w-full rounded-lg bg-gray-800/40" />
  </div>
);

const StatSkeleton = () => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 p-5 animate-pulse">
    <div className="flex items-center gap-3">
      <div className="w-12 h-12 rounded-xl bg-gray-800" />
      <div>
        <div className="h-5 w-16 rounded bg-gray-800 mb-1.5" />
        <div className="h-3 w-20 rounded bg-gray-800/60" />
      </div>
    </div>
  </div>
);

/* ─── Main Component ────────────────────────────────────── */
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
        data[r.key] = { articles: r.articles, total: r.total };
      });
      setCategoryData(data);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    } finally {
      setInitialLoading(false);
    }
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
    } finally {
      setProcessingIds((prev) => {
        const s = new Set(prev);
        s.delete(articleId);
        return s;
      });
    }
  };

  const getBiasIndicator = (score: number) => {
    if (score >= 70) return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', label: 'High Bias' };
    if (score >= 40) return { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', label: 'Moderate' };
    return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', label: 'Low Bias' };
  };

  const totalArticles = Object.values(categoryData).reduce((sum, d) => sum + d.total, 0);

  /* ─── Article Card ──────────────────────────────── */
  const ArticleCard = ({ article }: { article: Article }) => {
    const bias = getBiasIndicator(article.bias_score);
    const sourceColor = SOURCE_COLORS[article.source] || 'bg-gray-500';
    const sourceLabel = SOURCE_LABELS[article.source] || article.source;
    const date = formatDate(article.scraped_at);

    return (
      <Link
        to={`/article/${article.id}`}
        className="group relative flex flex-col rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-5 transition-all duration-300 hover:border-gray-700 hover:bg-gray-900/60 hover:shadow-xl hover:shadow-black/20 hover:-translate-y-0.5"
      >
        {/* Top row — source + bias */}
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

        {/* Content snippet */}
        <p className="text-sm leading-relaxed text-gray-500 mb-4 line-clamp-2 flex-1">
          {article.original_content}
        </p>

        {/* Footer */}
        <div className="mt-auto pt-3 border-t border-gray-800/50 flex items-center justify-between">
          {date && (
            <span className="text-[11px] text-gray-600 font-medium">{date}</span>
          )}

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
  };

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* ── Hero Header ────────────────────────── */}
        <div className="relative mb-4">
          <div className="absolute -top-8 -left-8 w-64 h-64 bg-primary-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="relative">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-primary-500/20 mt-1">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>
              </div>
              <div>
                <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                  Articles
                </h1>
                <p className="text-sm text-gray-500 mt-0.5">
                  Total  {initialLoading ? 'Loading…' : `${totalArticles.toLocaleString()} articles, 7${Object.values(categoryData).filter(d => d.total > 0).length} categories`}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Category Stat Cards ────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
          {initialLoading
            ? Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
            : CATEGORIES.map((cat) => {
                const data = categoryData[cat.key];
                const count = data?.total || 0;
                return (
                  <Link
                    key={cat.key}
                    to={`/articles/category/${encodeURIComponent(cat.key)}`}
                    className={`group relative rounded-2xl border border-gray-800/60 ${cat.bg} p-4 sm:p-5 transition-all duration-300 hover:border-gray-700 hover:shadow-lg hover:shadow-black/10 hover:-translate-y-0.5`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br ${cat.gradient} flex items-center justify-center text-lg shadow-md`}>
                        {cat.icon}
                      </div>
                      <div className="min-w-0">
                        <p className="text-white font-semibold text-sm sm:text-base truncate group-hover:text-primary-400 transition-colors">
                          {cat.label}
                        </p>
                        <p className="text-gray-500 text-xs mt-0.5">
                          {count.toLocaleString()} article{count !== 1 ? 's' : ''}
                        </p>
                      </div>
                    </div>
                    {/* Hover arrow */}
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    </div>
                  </Link>
                );
              })}
        </div>

        {/* ── Loading Skeletons ──────────────────── */}
        {initialLoading && (
          <div className="space-y-14">
            {[1, 2].map((i) => (
              <div key={i}>
                <div className="h-7 w-40 rounded bg-gray-800 mb-6 animate-pulse" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Array.from({ length: 3 }).map((_, j) => <CardSkeleton key={j} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Category Sections ──────────────────── */}
        {!initialLoading &&
          CATEGORIES.map((cat) => {
            const data = categoryData[cat.key];
            if (!data || data.articles.length === 0) return null;

            return (
              <section key={cat.key} className="mb-14">
                {/* Section Header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className={`w-1 h-8 rounded-full bg-gradient-to-b ${cat.gradient}`} />
                    <div>
                      <h2 className="text-xl sm:text-2xl font-bold text-white leading-tight">
                        {cat.icon} {cat.label}
                      </h2>
                      <p className="text-gray-500 text-xs mt-0.5">
                        {cat.sublabel} · {data.total.toLocaleString()} article{data.total !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/articles/category/${encodeURIComponent(cat.key)}`}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium text-gray-400 border border-gray-800 hover:border-gray-700 hover:text-white hover:bg-gray-800/60 transition-all group"
                  >
                    View All
                    <svg className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </Link>
                </div>

                {/* Article Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.articles.slice(0, 6).map((article) => (
                    <ArticleCard key={article.id} article={article} />
                  ))}
                </div>

                {/* Mobile: See More */}
                {data.total > 6 && (
                  <div className="mt-5 text-center lg:hidden">
                    <Link
                      to={`/articles/category/${encodeURIComponent(cat.key)}`}
                      className="inline-flex items-center gap-1 text-sm font-medium text-primary-400 hover:text-primary-300 transition-colors"
                    >
                      See all {data.total.toLocaleString()} articles
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
                    </Link>
                  </div>
                )}
              </section>
            );
          })}

        {/* ── Empty State ────────────────────────── */}
        {!initialLoading && totalArticles === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-20 h-20 rounded-2xl bg-gray-800/60 flex items-center justify-center mb-6">
              <svg className="w-10 h-10 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No articles yet</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              Start by scraping some articles from the Manual Scraping page. They'll appear here organized by category.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ArticlesPage;
