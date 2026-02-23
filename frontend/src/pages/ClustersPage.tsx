import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, type ArticleCluster, type ClusteringStats } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { ChevronDown, Layers, BarChart3, RefreshCw, Loader2 } from 'lucide-react';

const SOURCE_LABELS: Record<string, string> = {
  prothom_alo: 'প্রথম আলো',
  daily_star: 'ডেইলি স্টার',
  jugantor: 'যুগান্তর',
  samakal: 'সমকাল',
  naya_diganta: 'নয়া দিগন্ত',
  ittefaq: 'ইত্তেফাক',
};

const SOURCE_COLORS: Record<string, string> = {
  prothom_alo: 'bg-orange-500',
  daily_star: 'bg-sky-500',
  jugantor: 'bg-rose-500',
  samakal: 'bg-violet-500',
  naya_diganta: 'bg-green-500',
  ittefaq: 'bg-teal-500',
};

const CATEGORIES = [
  { key: 'রাজনীতি', label: 'রাজনীতি', icon: '🏛️' },
  { key: 'বিশ্ব', label: 'বিশ্ব', icon: '🌍' },
  { key: 'মতামত', label: 'মতামত', icon: '💬' },
  { key: 'বাংলাদেশ', label: 'বাংলাদেশ', icon: '🇧🇩' },
];

/* ─── Skeleton ─── */
const ClusterSkeleton = () => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 p-6 animate-pulse">
    <div className="h-5 w-2/3 rounded bg-gray-800 mb-3" />
    <div className="h-4 w-1/2 rounded bg-gray-800/60 mb-4" />
    <div className="flex gap-2 mb-4">
      <div className="h-6 w-16 rounded-full bg-gray-800" />
      <div className="h-6 w-16 rounded-full bg-gray-800" />
    </div>
    <div className="h-10 w-full rounded-lg bg-gray-800/40" />
  </div>
);

const ClustersPage = () => {
  const { isAdmin } = useAuth();
  const [clusters, setClusters] = useState<ArticleCluster[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<ClusteringStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [page, setPage] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const limit = 12;

  useEffect(() => {
    fetchClusters();
    fetchStats();
  }, [page, categoryFilter]);

  const fetchClusters = async () => {
    setLoading(true);
    try {
      const params: any = { skip: page * limit, limit };
      if (categoryFilter) params.category = categoryFilter;
      const res = await api.getClusters(params);
      setClusters(res.clusters);
      setTotal(res.total);
    } catch (error) {
      console.error('Failed to fetch clusters:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const s = await api.getClusteringStats();
      setStats(s);
    } catch (error) {
      console.error('Failed to fetch clustering stats:', error);
    }
  };

  const handleGenerateClusters = async () => {
    if (generating) return;
    setGenerating(true);
    try {
      await api.generateClusters({ days_back: 7 });
      await fetchClusters();
      await fetchStats();
    } catch (error) {
      console.error('Failed to generate clusters:', error);
    } finally {
      setGenerating(false);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* ── Header ── */}
        <div className="relative mb-6">
          <div className="absolute -top-8 -left-8 w-64 h-64 bg-violet-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/20 mt-1">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">
                  Article Clusters
                </h1>
                <p className="text-sm text-gray-500 mt-0.5">
                  {loading ? 'Loading…' : `${total} clusters detected across multiple sources`}
                </p>
              </div>
            </div>

            {isAdmin && (
              <button
                onClick={handleGenerateClusters}
                disabled={generating}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 hover:border-violet-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {generating ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                {generating ? 'Clustering…' : 'Generate Clusters'}
              </button>
            )}
          </div>
        </div>

        {/* ── Stats Collapsible ── */}
        {stats && (
          <div className="mb-6">
            <button
              onClick={() => setShowStats(!showStats)}
              className="w-full flex items-center justify-between px-5 py-4 rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm hover:bg-gray-900/60 hover:border-gray-700 transition-all duration-300"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-md shadow-violet-500/20">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-sm font-semibold text-white">Clustering Statistics</h3>
                  <p className="text-[11px] text-gray-500">
                    {stats.total_clusters} clusters · {stats.clustering_coverage}% coverage · threshold {stats.similarity_threshold}
                  </p>
                </div>
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform duration-300 ${showStats ? 'rotate-180' : ''}`} />
            </button>

            <div className={`overflow-hidden transition-all duration-500 ease-in-out ${showStats ? 'max-h-[400px] opacity-100 mt-4' : 'max-h-0 opacity-0'}`}>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'Total Clusters', value: stats.total_clusters, icon: '🔗', color: 'from-violet-500 to-fuchsia-500' },
                  { label: 'Articles Clustered', value: stats.total_articles_clustered, icon: '📊', color: 'from-emerald-500 to-teal-500' },
                  { label: 'Multi-Source', value: stats.multi_source_clusters, icon: '🌐', color: 'from-blue-500 to-indigo-500' },
                  { label: 'Avg Cluster Size', value: stats.avg_cluster_size, icon: '📐', color: 'from-amber-500 to-orange-500' },
                ].map((stat, i) => (
                  <div key={i} className="rounded-xl border border-gray-800/60 bg-gray-900/40 p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${stat.color} flex items-center justify-center text-lg shadow-md`}>
                        {stat.icon}
                      </div>
                      <div>
                        <p className="text-white font-bold text-lg">{stat.value}</p>
                        <p className="text-gray-500 text-[11px]">{stat.label}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-3 rounded-xl border border-gray-800/60 bg-gray-900/40 p-4">
                <div className="flex justify-between mb-1.5">
                  <span className="text-[11px] text-gray-500">Clustering Coverage</span>
                  <span className="text-[11px] font-bold text-gray-400">{stats.clustering_coverage}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-800/80 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-700"
                    style={{ width: `${stats.clustering_coverage}%` }}
                  />
                </div>
                <p className="text-[10px] text-gray-600 mt-2">
                  Model: {stats.model} · Similarity ≥ {stats.similarity_threshold}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Category Filter ── */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => { setCategoryFilter(''); setPage(0); }}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              !categoryFilter
                ? 'bg-violet-500/20 text-violet-400 border-violet-500/40'
                : 'bg-gray-900/40 text-gray-400 border-gray-800/60 hover:border-gray-700'
            }`}
          >
            All
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.key}
              onClick={() => { setCategoryFilter(cat.key); setPage(0); }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                categoryFilter === cat.key
                  ? 'bg-violet-500/20 text-violet-400 border-violet-500/40'
                  : 'bg-gray-900/40 text-gray-400 border-gray-800/60 hover:border-gray-700'
              }`}
            >
              {cat.icon} {cat.label}
            </button>
          ))}
        </div>

        {/* ── Cluster Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => <ClusterSkeleton key={i} />)}
          </div>
        ) : clusters.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-20 h-20 rounded-2xl bg-gray-800/60 flex items-center justify-center mb-6">
              <Layers className="w-10 h-10 text-gray-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No clusters found</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              {isAdmin
                ? 'Click "Generate Clusters" to detect similar articles across newspapers.'
                : 'Article clusters will appear here once generated by an administrator.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clusters.map((cluster) => (
              <ClusterCard key={cluster.id} cluster={cluster} />
            ))}
          </div>
        )}

        {/* ── Pagination ── */}
        {totalPages > 1 && (
          <div className="flex justify-center items-center gap-3 mt-8">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 border border-gray-800 hover:border-gray-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 border border-gray-800 hover:border-gray-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

/* ─── Cluster Card ─── */
const ClusterCard = ({ cluster }: { cluster: ArticleCluster }) => {
  const similarityPercent = cluster.avg_similarity ? (cluster.avg_similarity * 100).toFixed(0) : '—';

  const SimColor = () => {
    const sim = cluster.avg_similarity || 0;
    if (sim >= 0.9) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (sim >= 0.8) return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  };

  const catInfo = CATEGORIES.find(c => c.key === cluster.category);

  return (
    <Link
      to={`/clusters/${cluster.id}`}
      className="group relative flex flex-col rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-5 transition-all duration-300 hover:border-violet-500/30 hover:bg-gray-900/60 hover:shadow-xl hover:shadow-violet-500/5 hover:-translate-y-0.5"
    >
      {/* Header: Category + similarity */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {catInfo && <span className="text-sm">{catInfo.icon}</span>}
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            {catInfo?.label || cluster.category || 'Mixed'}
          </span>
        </div>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${SimColor()}`}>
          {similarityPercent}% similar
        </span>
      </div>

      {/* Title */}
      <h3 className="text-[15px] font-semibold leading-snug text-gray-100 mb-2 line-clamp-2 group-hover:text-white transition-colors">
        {cluster.representative_title || cluster.cluster_label || 'Untitled Cluster'}
      </h3>

      {/* Source pills */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {cluster.sources.map((src) => (
          <span
            key={src}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-800/60 text-gray-400 border border-gray-700/50"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${SOURCE_COLORS[src] || 'bg-gray-500'} shrink-0`} />
            {SOURCE_LABELS[src] || src}
          </span>
        ))}
      </div>

      {/* Article count + preview */}
      <div className="mt-auto pt-3 border-t border-gray-800/50">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-600">
            {cluster.article_count} articles from {cluster.sources.length} source{cluster.sources.length !== 1 ? 's' : ''}
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-violet-400 opacity-0 group-hover:opacity-100 transition-opacity">
            View Cluster
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
          </span>
        </div>
      </div>
    </Link>
  );
};

export default ClustersPage;
