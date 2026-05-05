import { Link } from 'react-router-dom';
import type { Article } from '../services/api';
import { SOURCE_LABELS, SOURCE_COLORS, SOURCE_LOGOS } from '../constants/sources';

interface ArticleCardProps {
  article: Article;
  onBiasCheck?: (articleId: number, e: React.MouseEvent) => void;
  processingIds?: Set<number>;
  isSaved?: boolean;
  onToggleSave?: (articleId: number, e: React.MouseEvent) => void;
  savingIds?: Set<number>;
}

const getBiasIndicator = (score: number) => {
  if (score >= 70) return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', label: 'High Bias' };
  if (score >= 40) return { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', label: 'Moderate' };
  return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', label: 'Low Bias' };
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

const ArticleCard = ({ article, onBiasCheck, processingIds = new Set(), isSaved = false, onToggleSave, savingIds = new Set() }: ArticleCardProps) => {
  const bias = getBiasIndicator(article.bias_score);
  const sourceColor = SOURCE_COLORS[article.source] || 'bg-gray-500';
  const sourceLogo = SOURCE_LOGOS[article.source];
  const sourceLabel = SOURCE_LABELS[article.source] || article.source;
  const date = formatDate(article.scraped_at);

  return (
    <Link
      to={`/article/${article.id}`}
      className="group relative flex flex-col rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-5 transition-all duration-300 hover:border-gray-700 hover:bg-gray-900/60 hover:shadow-xl hover:shadow-black/20 hover:-translate-y-0.5"
    >
      {/* Top row — source + bias + save */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2">
          {sourceLogo ? (
            <img src={sourceLogo} alt={sourceLabel} className="w-8 h-8 rounded-md object-contain shrink-0 bg-white p-0.2" />
          ) : (
            <span className={`w-2 h-2 rounded-full ${sourceColor} shrink-0`} />
          )}
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
        <div className="flex items-center gap-1.5">
          {isSaved && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              🔖 Saved
            </span>
          )}
          {onToggleSave && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleSave(article.id, e); }}
              disabled={savingIds.has(article.id)}
              className={`p-1.5 rounded-lg transition-all disabled:opacity-40 ${
                isSaved
                  ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10'
                  : 'text-gray-600 hover:text-amber-400 hover:bg-amber-500/10 opacity-0 group-hover:opacity-100'
              }`}
              title={isSaved ? 'Remove bookmark' : 'Save article'}
            >
              {savingIds.has(article.id) ? (
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              ) : (
                <svg className="w-4 h-4" fill={isSaved ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Cluster/Merged badge */}
      {article.cluster_id && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20 w-fit mb-2">
          🔗 Merged
        </span>
      )}

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
            onClick={(e) => onBiasCheck?.(article.id, e)}
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

export default ArticleCard;
