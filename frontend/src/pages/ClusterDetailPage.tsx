import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type ClusterDetail, type PairwiseSimilarity } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, Layers, ExternalLink, Loader2, Shield } from 'lucide-react';

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

const ClusterDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated } = useAuth();
  const [cluster, setCluster] = useState<ClusterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedArticle, setExpandedArticle] = useState<number | null>(null);
  const [debiasing, setDebiasing] = useState(false);
  const [debiasResult, setDebiasResult] = useState<any>(null);
  const [showDebiased, setShowDebiased] = useState(false);

  useEffect(() => {
    if (id) fetchCluster(parseInt(id));
  }, [id]);

  const fetchCluster = async (clusterId: number) => {
    setLoading(true);
    try {
      const data = await api.getClusterDetail(clusterId);
      setCluster(data);
    } catch (error) {
      console.error('Failed to fetch cluster:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDebiasUnified = async () => {
    if (!id || debiasing) return;
    setDebiasing(true);
    try {
      const result = await api.debiasUnifiedContent(parseInt(id));
      setDebiasResult(result);
      if (result.debiased_content) {
        setShowDebiased(true);
      }
    } catch (error) {
      console.error('Failed to debias unified content:', error);
    } finally {
      setDebiasing(false);
    }
  };

  const getBiasIndicator = (score: number | null) => {
    if (score === null) return { color: 'text-gray-500', bg: 'bg-gray-500/10', label: 'Unprocessed' };
    if (score >= 70) return { color: 'text-red-400', bg: 'bg-red-500/10', label: 'High Bias' };
    if (score >= 40) return { color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Moderate' };
    return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Low/None' };
  };

  const getSimilarity = (articleId: number, similarities: PairwiseSimilarity[]) => {
    const related = similarities.filter(s => s.article_a === articleId || s.article_b === articleId);
    if (related.length === 0) return null;
    const avg = related.reduce((sum, s) => sum + s.similarity, 0) / related.length;
    return avg;
  };

  if (loading) {
    return (
      <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 w-64 rounded bg-gray-800 mb-4" />
            <div className="h-5 w-96 rounded bg-gray-800/60 mb-8" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="rounded-2xl border border-gray-800/60 bg-gray-900/40 p-6 h-48" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!cluster) {
    return (
      <div className="min-h-screen py-10 px-4 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-300 mb-2">Cluster not found</h2>
          <Link to="/clusters" className="text-violet-400 hover:text-violet-300 text-sm">
            Back to Clusters
          </Link>
        </div>
      </div>
    );
  }

  const similarityPercent = cluster.avg_similarity ? (cluster.avg_similarity * 100).toFixed(1) : '—';

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* ── Back + Header ── */}
        <Link
          to="/clusters"
          className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Clusters
        </Link>

        <div className="relative mb-8">
          <div className="absolute -top-8 -left-8 w-64 h-64 bg-violet-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="relative">
            <div className="flex items-start gap-3 mb-2">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/20 mt-1">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight leading-tight">
                  {cluster.representative_title || cluster.cluster_label}
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  Cluster #{cluster.id} · {cluster.article_count} articles · {cluster.sources.length} sources · {similarityPercent}% avg similarity
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Cluster Meta Cards ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <div className="rounded-xl border border-gray-800/60 bg-gray-900/40 p-4 text-center">
            <p className="text-2xl font-bold text-white">{cluster.article_count}</p>
            <p className="text-[11px] text-gray-500">Articles</p>
          </div>
          <div className="rounded-xl border border-gray-800/60 bg-gray-900/40 p-4 text-center">
            <p className="text-2xl font-bold text-white">{cluster.sources.length}</p>
            <p className="text-[11px] text-gray-500">Sources</p>
          </div>
          <div className="rounded-xl border border-gray-800/60 bg-gray-900/40 p-4 text-center">
            <p className="text-2xl font-bold text-violet-400">{similarityPercent}%</p>
            <p className="text-[11px] text-gray-500">Avg Similarity</p>
          </div>
          <div className="rounded-xl border border-gray-800/60 bg-gray-900/40 p-4 text-center">
            <p className="text-2xl font-bold text-white">{cluster.category || '—'}</p>
            <p className="text-[11px] text-gray-500">Category</p>
          </div>
        </div>

        {/* ── Source Pills ── */}
        <div className="flex flex-wrap gap-2 mb-6">
          {cluster.sources.map((src) => (
            <span
              key={src}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800/60 text-gray-300 border border-gray-700/50"
            >
              <span className={`w-2 h-2 rounded-full ${SOURCE_COLORS[src] || 'bg-gray-500'}`} />
              {SOURCE_LABELS[src] || src}
            </span>
          ))}
        </div>

        {/* ── Unified Content (if available) ── */}
        {cluster.unified_content && (
          <div className="rounded-2xl border border-violet-500/30 bg-violet-500/5 backdrop-blur-sm p-6 mb-8">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <span className="text-violet-400">✦</span> Unified Article
              </h3>
              <div className="flex items-center gap-2">
                {/* Toggle original/debiased */}
                {(debiasResult?.debiased_content || cluster.debiased_unified_content) && (
                  <button
                    onClick={() => setShowDebiased(!showDebiased)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      showDebiased
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                        : 'bg-gray-800/60 text-gray-400 border-gray-700/50 hover:border-gray-600'
                    }`}
                  >
                    {showDebiased ? '✦ Showing Debiased' : 'Show Original'}
                  </button>
                )}
                {/* Debias button */}
                {isAuthenticated && !debiasResult?.debiased_content && !cluster.debiased_unified_content && (
                  <button
                    onClick={handleDebiasUnified}
                    disabled={debiasing}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 hover:border-emerald-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    {debiasing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Shield className="w-3.5 h-3.5" />
                    )}
                    {debiasing ? 'Analyzing…' : 'Analyze & Debias'}
                  </button>
                )}
              </div>
            </div>

            {/* Bias result badge */}
            {debiasResult && (
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${
                  debiasResult.is_biased
                    ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                    : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                }`}>
                  {debiasResult.is_biased
                    ? `Biased (${debiasResult.bias_score?.toFixed(0)}%) · ${debiasResult.total_changes} changes`
                    : 'No bias detected ✓'}
                </span>
                {debiasResult.bias_summary && (
                  <span className="text-[11px] text-gray-500">{debiasResult.bias_summary}</span>
                )}
              </div>
            )}

            {cluster.unified_headline && (
              <p className="text-base font-medium text-gray-200 mb-3">{cluster.unified_headline}</p>
            )}

            {/* Show debiased or original content */}
            <p className="text-sm leading-relaxed text-gray-400 whitespace-pre-wrap">
              {showDebiased && (debiasResult?.debiased_content || cluster.debiased_unified_content)
                ? (debiasResult?.debiased_content || cluster.debiased_unified_content)
                : cluster.unified_content}
            </p>
          </div>
        )}

        {/* ── Similarity Matrix ── */}
        {cluster.pairwise_similarities.length > 0 && (
          <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6 mb-8">
            <h3 className="text-sm font-semibold text-white mb-4">Pairwise Similarity Matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="text-left py-2 px-3 text-gray-500 font-medium">Article A</th>
                    <th className="text-left py-2 px-3 text-gray-500 font-medium">Article B</th>
                    <th className="text-right py-2 px-3 text-gray-500 font-medium">Cosine Similarity</th>
                  </tr>
                </thead>
                <tbody>
                  {cluster.pairwise_similarities.map((sim, i) => {
                    const artA = cluster.articles.find(a => a.id === sim.article_a);
                    const artB = cluster.articles.find(a => a.id === sim.article_b);
                    const simPercent = (sim.similarity * 100).toFixed(1);
                    const simColor = sim.similarity >= 0.9 ? 'text-emerald-400' : sim.similarity >= 0.8 ? 'text-blue-400' : 'text-amber-400';
                    return (
                      <tr key={i} className="border-t border-gray-800/40">
                        <td className="py-2 px-3 text-gray-300">
                          <span className={`w-1.5 h-1.5 rounded-full inline-block mr-1.5 ${SOURCE_COLORS[artA?.source || ''] || 'bg-gray-500'}`} />
                          {artA?.title?.slice(0, 50) || `#${sim.article_a}`}
                        </td>
                        <td className="py-2 px-3 text-gray-300">
                          <span className={`w-1.5 h-1.5 rounded-full inline-block mr-1.5 ${SOURCE_COLORS[artB?.source || ''] || 'bg-gray-500'}`} />
                          {artB?.title?.slice(0, 50) || `#${sim.article_b}`}
                        </td>
                        <td className={`py-2 px-3 text-right font-bold ${simColor}`}>
                          {simPercent}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Articles List ── */}
        <h3 className="text-lg font-semibold text-white mb-4">
          Articles in this Cluster ({cluster.articles.length})
        </h3>

        <div className="space-y-4">
          {cluster.articles.map((article) => {
            const bias = getBiasIndicator(article.bias_score);
            const sourceColor = SOURCE_COLORS[article.source] || 'bg-gray-500';
            const sourceLabel = SOURCE_LABELS[article.source] || article.source;
            const avgSim = getSimilarity(article.id, cluster.pairwise_similarities);
            const isExpanded = expandedArticle === article.id;

            return (
              <div
                key={article.id}
                className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm overflow-hidden transition-all duration-300 hover:border-gray-700"
              >
                {/* Article header */}
                <div
                  className="p-5 cursor-pointer"
                  onClick={() => setExpandedArticle(isExpanded ? null : article.id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`w-2 h-2 rounded-full ${sourceColor} shrink-0`} />
                        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{sourceLabel}</span>
                        {article.is_biased !== null && (
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold ${bias.bg} ${bias.color}`}>
                            {article.bias_score !== null ? `${article.bias_score.toFixed(0)}%` : bias.label}
                          </span>
                        )}
                        {avgSim !== null && (
                          <span className="text-[10px] text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded">
                            Sim: {(avgSim * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-semibold text-gray-100 leading-snug line-clamp-2">
                        {article.title || 'Untitled'}
                      </h4>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Link
                        to={`/article/${article.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 transition-all"
                        title="View full article"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                      <svg
                        className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                <div className={`overflow-hidden transition-all duration-300 ${isExpanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'}`}>
                  <div className="px-5 pb-5 pt-0 border-t border-gray-800/50">
                    <p className="text-sm leading-relaxed text-gray-400 mt-4 whitespace-pre-wrap">
                      {article.original_content}
                    </p>
                    {article.published_date && (
                      <p className="text-[11px] text-gray-600 mt-3">
                        Published: {new Date(article.published_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                      </p>
                    )}
                    {article.url && (
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300 mt-2 transition-colors"
                      >
                        Original article <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ClusterDetailPage;
