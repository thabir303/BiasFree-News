import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api, authApi, type Article, type Statistics, type VisualizationData } from '../services/api';
import { ChevronDown, BarChart3, TrendingUp, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import ArticleIcon from '../../public/icons/ArticleIcon'
import { BarChart } from '@mui/x-charts/BarChart';
import { PieChart } from '@mui/x-charts/PieChart';
import { CATEGORIES, SOURCE_LABELS } from '../constants/sources';
import usePageTitle from '../hooks/usePageTitle';
import ArticleCard from '../components/ArticleCard';
import {
  BiasDistributionChart,
  SourceBiasRadarChart,
  SourceBreakdownBarChart,
  TimeTrendChart,
  CategoryBreakdownChart,
} from '../components/charts';

interface CategoryData {
  articles: Article[];
  total: number;
}

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
  usePageTitle('Articles');
  const { isAuthenticated } = useAuth();
  const { isDark } = useTheme();
  const chartTextColor = isDark ? '#ffffff' : '#1e293b';
  const chartAxisColor = isDark ? '#4b5563' : '#94a3b8';
  const [categoryData, setCategoryData] = useState<Record<string, CategoryData>>({});
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [initialLoading, setInitialLoading] = useState(true);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [showGraph, setShowGraph] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [vizData, setVizData] = useState<VisualizationData | null>(null);
  const [vizLoading, setVizLoading] = useState(false);
  const [vizDays, setVizDays] = useState(30);
  const [categoryOrder, setCategoryOrder] = useState<string[]>([]);

  useEffect(() => {
    fetchAllCategories();
    fetchStatistics();
    fetchCategoryOrder();
  }, [isAuthenticated]);

  const fetchCategoryOrder = async () => {
    if (!isAuthenticated) {
      setCategoryOrder(CATEGORIES.map(c => c.key));
      return;
    }
    try {
      const prefs = await authApi.getCategoryPreferences();
      if (prefs.categories && prefs.categories.length > 0) {
        const remaining = CATEGORIES.map(c => c.key).filter(k => !prefs.categories.includes(k));
        setCategoryOrder([...prefs.categories, ...remaining]);
      } else {
        setCategoryOrder(CATEGORIES.map(c => c.key));
      }
    } catch {
      setCategoryOrder(CATEGORIES.map(c => c.key));
    }
  };

  const sortedCategories = useMemo(() => {
    if (categoryOrder.length === 0) return CATEGORIES;
    return [...CATEGORIES].sort((a, b) => {
      const idxA = categoryOrder.indexOf(a.key);
      const idxB = categoryOrder.indexOf(b.key);
      return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
    });
  }, [categoryOrder]);

  const fetchStatistics = async () => {
    try {
      const stats = await api.getStatistics();
      setStatistics(stats);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };

  const fetchVizData = async () => {
    setVizLoading(true);
    try {
      const result = await api.getVisualizationData(vizDays);
      setVizData(result);
    } catch (error) {
      console.error('Failed to fetch visualization data:', error);
    } finally {
      setVizLoading(false);
    }
  };

  useEffect(() => {
    if (showAnalytics) fetchVizData();
  }, [vizDays, showAnalytics]);

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



  const totalArticles = statistics?.total_articles ?? Object.values(categoryData).reduce((sum, d) => sum + d.total, 0);

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* ── Hero Header ────────────────────────── */}
        <div className="relative mb-4">
          <div className="absolute -top-8 -left-8 w-64 h-64 bg-primary-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="relative">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-primary-500/20 mt-1">
                <ArticleIcon />
              </div>
              <div>
                <h1 className="text-3xl sm:text-3xl font-bold text-white tracking-tight">
                  Articles
                </h1>
                <p className="text-sm text-gray-500 mt-0.5">
                  Total  {initialLoading ? 'Loading…' : `${totalArticles.toLocaleString()} articles, ${Object.values(categoryData).filter(d => d.total > 0).length} categories`}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Statistics Graph (collapsible) ──────── */}
        {statistics && (
          <div className="mb-8">
            <button
              onClick={() => setShowGraph(!showGraph)}
              className="w-full flex items-center justify-between px-5 py-4 rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm hover:bg-gray-900/60 hover:border-gray-700 transition-all duration-300 group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-md shadow-violet-500/20">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-sm font-semibold text-white">সংবাদ পরিসংখ্যান</h3>
                  <p className="text-[11px] text-gray-500">Article Statistics &amp; Insights</p>
                </div>
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform duration-300 ${showGraph ? 'rotate-180' : ''}`} />
            </button>

            <div className={`overflow-hidden transition-all duration-500 ease-in-out ${showGraph ? 'max-h-[800px] opacity-100 mt-4' : 'max-h-0 opacity-0'}`}>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* ─ Source Distribution Bar Chart ─ */}
                <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
                  <h4 className="text-sm font-semibold text-white mb-1">উৎস ভিত্তিক সংবাদ</h4>
                  <p className="text-[11px] text-gray-500 mb-5">Articles by Source</p>
                  
                  {/* MUI Bar Chart */}
                  <div className="h-64">
                    {(() => {
                      const sources = Object.keys(statistics.by_source);
                      const sourceColorMap: Record<string, string> = {
                        'prothom_alo': '#fb923c',
                        'daily_star': '#38bdf8',
                        'jugantor': '#f43f5e',
                        'samakal': '#a78bfa',
                      };
                      
                      return (
                        <BarChart
                          xAxis={[{
                            scaleType: 'band',
                            data: sources.map(s => SOURCE_LABELS[s] || s),
                          }]}
                          series={[{
                            data: Object.values(statistics.by_source),
                            color: '#60a5fa',
                          }]}
                          colors={sources.map(s => sourceColorMap[s] || '#60a5fa')}
                          height={240}
                          margin={{ top: 10, bottom: 30, left: 40, right: 10 }}
                          sx={{
                            '& .MuiChartsAxis-tickLabel': {
                              fill: `${chartTextColor} !important`,
                              fontSize: '12px',
                              fontWeight: '500',
                            },
                            '& .MuiChartsAxis-tickLabel tspan': {
                              fill: `${chartTextColor} !important`,
                            },
                            '& .MuiChartsAxis-label': {
                              fill: `${chartTextColor} !important`,
                            },
                            '& .MuiChartsAxis-line': {
                              stroke: chartAxisColor,
                            },
                            '& .MuiChartsAxis-tick': {
                              stroke: chartAxisColor,
                            },
                          }}
                        />
                      );
                    })()}
                  </div>
                </div>

                {/* ─ Analysis Overview (Pie Chart) ─ */}
                <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
                  <h4 className="text-sm font-semibold text-white mb-1">বিশ্লেষণ অবস্থা</h4>
                  <p className="text-[11px] text-gray-500 mb-4">Analysis Overview</p>

                  {/* MUI Pie Chart — Processed vs Unprocessed (always both visible) */}
                  {(() => {
                    const processedCount = statistics.processed_count;
                    const unprocessedCount = statistics.total_articles - statistics.processed_count;
                    const neutralCount = statistics.processed_count - statistics.biased_count;
                    const biasedCount = statistics.biased_count;
                    const total = processedCount + unprocessedCount;

                    // Give analyzed slice a minimum 7% visual arc so it's always visible,
                    // but labels/chips still show the real numbers.
                    const MIN_VISUAL_FRAC = 0.07;
                    const analyzedVisual = total > 0
                      ? Math.max(processedCount, Math.round(total * MIN_VISUAL_FRAC))
                      : 1;
                    const pendingVisual = Math.max(total - analyzedVisual, 0);

                    // Real counts for tooltip/legend labels
                    const realCounts: Record<number, number> = { 0: processedCount, 1: unprocessedCount };

                    const pieData = [
                      { id: 0, value: analyzedVisual, label: `Analyzed (${processedCount})` },
                      ...(pendingVisual > 0 ? [{ id: 1, value: pendingVisual, label: `Pending (${unprocessedCount})` }] : []),
                    ];

                    return (
                      <>
                        <div className="h-56">
                          <PieChart
                            colors={isDark ? ['#818cf8', '#1e293b'] : ['#818cf8', '#e2e8f0']}
                            series={[{
                              data: pieData,
                              // arc label and tooltip both use real counts
                              arcLabel: (item) =>
                                item.id === 0
                                  ? (processedCount > 0 ? `${processedCount}` : '')
                                  : (unprocessedCount > 0 ? `${unprocessedCount}` : ''),
                              arcLabelMinAngle: 20,
                              innerRadius: 52,
                              outerRadius: 88,
                              paddingAngle: 2,
                              cornerRadius: 4,
                              valueFormatter: (item: any) =>
                                `${(realCounts[item.id as number] ?? item.value).toLocaleString()}`,
                            }]}
                            height={220}
                            margin={{ top: 10, bottom: 10, left: 10, right: 150 }}
                            sx={{
                              '& text': { fill: `${chartTextColor} !important`, fontSize: '13px', fontFamily: 'inherit' },
                              '& tspan': { fill: `${chartTextColor} !important` },
                              '& .MuiChartsLegend-series text': { fill: `${chartTextColor} !important`, fontWeight: '600', fontSize: '13px' },
                              '& .MuiChartsLegend-series tspan': { fill: `${chartTextColor} !important` },
                              '& .MuiChartsLegend-label': { fill: `${chartTextColor} !important` },
                              '& .MuiChartsLegend-mark': { rx: 2 },
                              '& .MuiPieArc-root': { stroke: isDark ? '#0f172a' : '#ffffff', strokeWidth: 2 },
                              '& .MuiChartsArcLabel-root': { fill: `${chartTextColor} !important`, fontWeight: '700', fontSize: '12px' },
                            }}
                          />
                        </div>

                        {/* Biased / Neutral breakdown — always visible as stat chips */}
                        <div className="mt-3 flex gap-2 flex-wrap">
                          <div className="flex items-center gap-2 flex-1 min-w-[120px] rounded-xl border border-red-500/25 bg-red-500/10 px-3.5 py-2.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-red-400 shrink-0" />
                            <div className="min-w-0">
                              <p className="text-[10px] text-red-400/70 uppercase tracking-wider font-medium leading-none mb-0.5">Biased</p>
                              <p className="text-lg font-bold text-red-400 leading-none tabular-nums">{biasedCount.toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 flex-1 min-w-[120px] rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0" />
                            <div className="min-w-0">
                              <p className="text-[10px] text-emerald-400/70 uppercase tracking-wider font-medium leading-none mb-0.5">Neutral</p>
                              <p className="text-lg font-bold text-emerald-400 leading-none tabular-nums">{neutralCount.toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 flex-1 min-w-[120px] rounded-xl border border-slate-600/40 bg-slate-700/20 px-3.5 py-2.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-slate-500 shrink-0" />
                            <div className="min-w-0">
                              <p className="text-[10px] text-slate-400/70 uppercase tracking-wider font-medium leading-none mb-0.5">Pending</p>
                              <p className="text-lg font-bold text-slate-400 leading-none tabular-nums">{unprocessedCount.toLocaleString()}</p>
                            </div>
                          </div>
                        </div>
                      </>
                    );
                  })()}

                  {/* Progress bar */}
                  <div className="mt-4 pt-4 border-t border-gray-800/60">
                    <div className="flex justify-between mb-1.5">
                      <span className="text-[11px] text-gray-500">Processing progress</span>
                      <span className="text-[11px] font-bold text-gray-400">
                        {statistics.total_articles > 0 ? ((statistics.processed_count / statistics.total_articles) * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-800/80 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary-500 to-emerald-500 transition-all duration-700"
                        style={{ width: `${statistics.total_articles > 0 ? (statistics.processed_count / statistics.total_articles) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Analytics Visualization (collapsible) ── */}
        {isAuthenticated && (
          <div className="mb-8">
            <button
              onClick={() => { setShowAnalytics(!showAnalytics); if (!showAnalytics && !vizData) fetchVizData(); }}
              className="w-full flex items-center justify-between px-5 py-4 rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm hover:bg-gray-900/60 hover:border-gray-700 transition-all duration-300 group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-cyan-500 flex items-center justify-center shadow-md shadow-sky-500/20">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-sm font-semibold text-white">বিশ্লেষণ চার্ট</h3>
                  <p className="text-[11px] text-gray-500">Bias Analytics &amp; Trends</p>
                </div>
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform duration-300 ${showAnalytics ? 'rotate-180' : ''}`} />
            </button>

            <div className={`overflow-hidden transition-all duration-500 ease-in-out ${showAnalytics ? 'max-h-[3000px] opacity-100 mt-4' : 'max-h-0 opacity-0'}`}>
              {/* Period selector + refresh */}
              <div className="flex items-center justify-end gap-3 mb-4">
                <select
                  value={vizDays}
                  onChange={(e) => setVizDays(Number(e.target.value))}
                  className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                  <option value={365}>Last year</option>
                </select>
                <button
                  onClick={fetchVizData}
                  disabled={vizLoading}
                  className="p-1.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${vizLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {vizLoading && !vizData ? (
                <div className="flex items-center justify-center py-16">
                  <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary-500" />
                </div>
              ) : vizData ? (
                <div className="space-y-4">
                  {/* Row 1: Bias Score Distribution + Source Radar */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <BiasDistributionChart data={vizData.bias_distribution} />
                    <SourceBiasRadarChart data={vizData.source_comparison} />
                  </div>

                  {/* Row 2: Source Breakdown Bar */}
                  <SourceBreakdownBarChart data={vizData.source_comparison} />

                  {/* Row 3: Time-Series Trend */}
                  <TimeTrendChart data={vizData.time_series} />

                  {/* Row 4: Category Breakdown Cards */}
                  <CategoryBreakdownChart data={vizData.category_breakdown} />
                </div>
              ) : (
                <div className="flex flex-col items-center py-12 text-gray-500 text-sm">
                  <p>Could not load analytics data.</p>
                  <button onClick={fetchVizData} className="mt-2 text-primary-400 hover:text-primary-300 text-xs">Try again</button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Category Stat Cards ────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
          {initialLoading
            ? Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
            : sortedCategories.map((cat) => {
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
          sortedCategories.map((cat) => {
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
                    <ArticleCard key={article.id} article={article} onBiasCheck={handleBiasCheck} processingIds={processingIds} />
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
