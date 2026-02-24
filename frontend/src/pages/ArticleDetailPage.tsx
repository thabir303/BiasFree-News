import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, authApi, type Article } from '../services/api';
import { SOURCE_LABELS, SOURCE_COLORS, SOURCE_TEXT_COLORS } from '../constants/sources';
import { useAuth } from '../contexts/AuthContext';
import usePageTitle from '../hooks/usePageTitle';

const ArticleDetailPage = () => {
  usePageTitle('Article Detail');
  const { id } = useParams<{ id: string }>();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [viewMode, setViewMode] = useState<'split' | 'diff'>('split');
  const [expandedMergedId, setExpandedMergedId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const { isAuthenticated } = useAuth();

  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  };

  // Check if article is bookmarked
  useEffect(() => {
    if (isAuthenticated && id) {
      authApi.getBookmarks().then(res => {
        setIsBookmarked(res.bookmarks.some(b => b.article_id === parseInt(id)));
      }).catch(() => {});
    }
  }, [isAuthenticated, id]);

  const toggleBookmark = async () => {
    if (!isAuthenticated || !id) return;
    try {
      if (isBookmarked) {
        await authApi.removeBookmark(parseInt(id));
        setIsBookmarked(false);
        showToast('success', 'Bookmark removed');
      } else {
        await authApi.addBookmark(parseInt(id));
        setIsBookmarked(true);
        showToast('success', 'Article bookmarked!');
      }
    } catch {
      showToast('error', 'Failed to update bookmark');
    }
  };

  useEffect(() => {
    if (id) {
      fetchArticle(parseInt(id));
    }
  }, [id]);

  const fetchArticle = async (articleId: number) => {
    setLoading(true);
    try {
      const data = await api.getArticle(articleId);
      setArticle(data);
    } catch (error) {
      console.error('Failed to fetch article:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBiasAnalysis = async () => {
    if (!id || processing) return;

    setProcessing(true);
    try {
      const updatedArticle = await api.processArticle(parseInt(id));
      setArticle(updatedArticle);
    } catch (error) {
      console.error('Failed to analyze article:', error);
      showToast('error', 'Failed to analyze article. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const handleReanalyze = async () => {
    if (!id || processing) return;

    setProcessing(true);
    try {
      await api.reprocessArticle(parseInt(id));
      // Refetch the full article to get updated data
      const refreshed = await api.getArticle(parseInt(id));
      setArticle(refreshed);
      showToast('success', 'Article re-analyzed successfully!');
    } catch (error) {
      console.error('Failed to re-analyze article:', error);
      showToast('error', 'Failed to re-analyze article. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const formatDate = (dateStr: string | null | undefined) => {
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

  const highlightText = (text: string, highlights: any[] | undefined, type: 'biased' | 'debiased') => {
    if (!text) return '';
    if (!highlights || !Array.isArray(highlights) || highlights.length === 0) return text;

    const spans: Array<{ start: number; end: number; text: string; data: any }> = [];

    if (type === 'biased' && article?.biased_terms && Array.isArray(article.biased_terms)) {
      article.biased_terms.forEach((term: any) => {
        if (!term || !term.term) return;
        const regex = new RegExp(term.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        let match;
        while ((match = regex.exec(text)) !== null) {
          spans.push({
            start: match.index,
            end: match.index + match[0].length,
            text: match[0],
            data: term,
          });
        }
      });
    } else if (type === 'debiased' && article?.changes_made && Array.isArray(article.changes_made) && article?.original_content) {
      // Find positions of original biased terms in the ORIGINAL text
      // to determine where actual changes happened, instead of highlighting
      // every occurrence of the debiased word in the entire text.
      const originalText = article.original_content;

      const allPositions: Array<{ origStart: number; origEnd: number; change: any }> = [];

      article.changes_made.forEach((change: any) => {
        if (!change || !change.original || !change.debiased) return;
        const regex = new RegExp(change.original.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        let match;
        while ((match = regex.exec(originalText)) !== null) {
          allPositions.push({
            origStart: match.index,
            origEnd: match.index + match[0].length,
            change,
          });
        }
      });

      // Sort by position in original text
      allPositions.sort((a, b) => a.origStart - b.origStart);

      // Remove overlapping positions
      const nonOverlapping: typeof allPositions = [];
      let lastEndPos = 0;
      for (const pos of allPositions) {
        if (pos.origStart >= lastEndPos) {
          nonOverlapping.push(pos);
          lastEndPos = pos.origEnd;
        }
      }

      // Compute corresponding positions in the debiased text
      let cumulativeOffset = 0;
      for (const pos of nonOverlapping) {
        const origTermLen = pos.origEnd - pos.origStart;
        const debTermLen = pos.change.debiased.length;

        const debStart = pos.origStart + cumulativeOffset;
        const debEnd = debStart + debTermLen;

        // Verify the debiased word is actually at this mapped position
        const textAtPos = text.substring(debStart, debEnd);
        if (textAtPos.toLowerCase() === pos.change.debiased.toLowerCase()) {
          spans.push({
            start: debStart,
            end: debEnd,
            text: textAtPos,
            data: pos.change,
          });
          // Only adjust offset when replacement actually occurred
          cumulativeOffset += (debTermLen - origTermLen);
        }
      }
    }

    spans.sort((a, b) => a.start - b.start);

    const parts: React.ReactElement[] = [];
    let lastIndex = 0;

    spans.forEach((span, idx) => {
      if (span.start > lastIndex) {
        parts.push(<span key={`text-${idx}`}>{text.slice(lastIndex, span.start)}</span>);
      }

      const tooltipContent =
        type === 'biased'
          ? `Biased: ${span.data.reason}\nSuggestion: ${span.data.neutral_alternative}`
          : `Original: ${span.data.original}\nReason: ${span.data.reason}`;

      parts.push(
        <span
          key={`highlight-${idx}`}
          className={`
            relative group cursor-help px-1 py-0.5 rounded transition-all
            ${
              type === 'biased'
                ? 'bg-red-500/20 text-red-300 border-b-2 border-red-500'
                : 'bg-yellow-500/20 text-yellow-300 border-b-2 border-yellow-500'
            }
          `}
          title={tooltipContent}
        >
          {span.text}
          <span className="invisible group-hover:visible absolute z-10 w-64 p-3 mt-2 text-sm bg-gray-900 border border-gray-700 rounded-lg shadow-xl left-0 top-full">
            {type === 'biased' ? (
              <>
                <div className="font-bold text-red-400 mb-1">Biased Term</div>
                <div className="text-gray-300 mb-2">{span.data.reason}</div>
                <div className="text-xs text-gray-500">
                  Suggestion: <span className="text-green-400">{span.data.neutral_alternative}</span>
                </div>
              </>
            ) : (
              <>
                <div className="font-bold text-yellow-400 mb-1">Changed</div>
                <div className="text-gray-300 mb-1">
                  <span className="text-red-400 line-through">{span.data.original}</span>
                  {' → '}
                  <span className="text-green-400">{span.data.debiased}</span>
                </div>
                <div className="text-xs text-gray-500">{span.data.reason}</div>
              </>
            )}
          </span>
        </span>
      );

      lastIndex = span.end;
    });

    if (lastIndex < text.length) {
      parts.push(<span key="text-end">{text.slice(lastIndex)}</span>);
    }

    return <>{parts}</>;
  };

  const getBiasColor = (score: number) => {
    if (score >= 70) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (score >= 40) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    return 'text-green-400 bg-green-500/10 border-green-500/30';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-gray-300 mb-2">Article Not Found</h2>
          <Link to="/articles" className="text-primary-400 hover:underline">
            Back to Articles
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-20 right-4 z-[9999] max-w-md px-4 py-3 rounded-xl border shadow-xl backdrop-blur-sm transition-all duration-300 animate-[slideIn_0.3s_ease-out] ${
          toast.type === 'error' ? 'bg-red-500/15 border-red-500/30 text-red-300' :
          toast.type === 'success' ? 'bg-green-500/15 border-green-500/30 text-green-300' :
          'bg-blue-500/15 border-blue-500/30 text-blue-300'
        }`}>
          <div className="flex items-start gap-2">
            <p className="text-sm flex-1">{toast.message}</p>
            <button onClick={() => setToast(null)} className="text-gray-400 hover:text-white shrink-0 mt-0.5">✕</button>
          </div>
        </div>
      )}
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center gap-1.5 text-xs text-gray-500 mb-8">
          <Link to="/articles" className="hover:text-primary-400 transition-colors">
            Articles
          </Link>
          <svg className="w-3 h-3 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {article.category && (
            <>
              <Link 
                to={`/articles/category/${encodeURIComponent(article.category)}`}
                className="hover:text-primary-400 transition-colors"
              >
                {article.category}
              </Link>
              <svg className="w-3 h-3 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </>
          )}
          <span className="text-gray-400 font-medium truncate max-w-xs">
            {article.title || 'Untitled Article'}
          </span>
        </nav>

        {/* Article Header */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white mb-2">{article.title || 'Untitled'}</h1>
              <div className="flex flex-wrap gap-3 text-sm text-gray-400">
                <span className="px-3 py-1 bg-gray-800 rounded-full">
                  📰 {article.source.replace('_', ' ')}
                </span>
                {article.category && (
                  <span className="px-2 py-1 bg-primary-500/10 text-primary-400 border border-primary-500/30 rounded-md text-xs">
                    {article.category}
                  </span>
                )}
                <span className="px-3 py-1 bg-gray-800 rounded-full">
                  📅 {formatDate(article.scraped_at)}
                </span>
                {article.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1 bg-gray-800 rounded-full hover:bg-gray-700 transition-colors"
                  >
                    🔗 Source
                  </a>
                )}
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(window.location.href);
                    showToast('success', 'Link copied to clipboard!');
                  }}
                  className="px-3 py-1 bg-gray-800 rounded-full hover:bg-gray-700 transition-colors cursor-pointer"
                >
                  📋 Copy Link
                </button>
                {isAuthenticated && (
                  <button
                    onClick={toggleBookmark}
                    className={`px-3 py-1 rounded-full transition-colors cursor-pointer ${
                      isBookmarked ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-gray-800 hover:bg-gray-700'
                    }`}
                  >
                    {isBookmarked ? '★ Saved' : '☆ Save'}
                  </button>
                )}
                {article.cluster_id && article.cluster_info && (
                  <span className="px-3 py-1 bg-violet-500/10 text-violet-400 border border-violet-500/30 rounded-full">
                    🔗 Merged from {article.cluster_info.article_count} articles ({article.cluster_info.sources.length} sources)
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-col items-end gap-3">
              {/* Bias Check Button for Unprocessed Articles */}
              {!article.processed && (
                <button
                  onClick={handleBiasAnalysis}
                  disabled={processing}
                  className="px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-colors flex items-center space-x-2"
                >
                  {processing ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
                      <span>Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <span>🔍</span>
                      <span>Analyze for Bias</span>
                    </>
                  )}
                </button>
              )}

              {/* Bias Score Display */}
              {article.processed && article.is_biased && (
                <div className={`px-6 py-3 rounded-xl border text-center ${getBiasColor(article.bias_score)}`}>
                  <div className="text-3xl font-bold">{article.bias_score.toFixed(0)}%</div>
                  <div className="text-xs mt-1">Bias Score</div>
                </div>
              )}

              {/* No Bias Badge */}
              {article.processed && !article.is_biased && (
                <div className="px-6 py-3 rounded-xl border border-green-500/30 bg-green-500/10 text-center">
                  <div className="text-2xl font-bold text-green-400">✅</div>
                  <div className="text-xs mt-1 text-green-400">No Bias Detected</div>
                </div>
              )}

              {/* Re-analyze button for already-processed articles */}
              {article.processed && isAuthenticated && (
                <button
                  onClick={handleReanalyze}
                  disabled={processing}
                  className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-gray-300 hover:text-white rounded-xl font-medium transition-colors flex items-center space-x-2 border border-gray-700 hover:border-gray-600 text-sm"
                >
                  {processing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></div>
                      <span>Re-analyzing...</span>
                    </>
                  ) : (
                    <>
                      <span>🔄</span>
                      <span>Check for Bias</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Bias Summary */}
          {article.bias_summary && (
            <div className="bg-gray-800/50 rounded-lg p-4 border-l-4 border-yellow-500">
              <h3 className="font-semibold text-yellow-400 mb-2">📋 Analysis Summary</h3>
              <p className="text-gray-300">{article.bias_summary}</p>
            </div>
          )}
        </div>

        {/* View Mode Toggle - Only show if article is processed */}
        {article.processed && article.debiased_content && (
          <div className="flex justify-center mb-6">
            <div className="inline-flex rounded-lg border border-gray-800 bg-gray-900/50 p-1">
              <button
                onClick={() => setViewMode('split')}
                className={`px-6 py-2 rounded-lg transition-all ${
                  viewMode === 'split'
                    ? 'bg-primary-500 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Split View
              </button>
              <button
                onClick={() => setViewMode('diff')}
                className={`px-6 py-2 rounded-lg transition-all ${
                  viewMode === 'diff'
                    ? 'bg-primary-500 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Diff View
              </button>
            </div>
          </div>
        )}

        {/* Unprocessed Article Notice */}
        {!article.processed && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-6 mb-6 text-center">
            <div className="text-4xl mb-3">🔍</div>
            <h3 className="text-xl font-bold text-blue-400 mb-2">Article Not Yet Analyzed</h3>
            <p className="text-gray-400 mb-4">
              Click the "Analyze for Bias" button above to check this article for biased content using AI.
            </p>
          </div>
        )}

        {/* Original Content Only (for unprocessed articles) */}
        {!article.processed && (
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
            <h2 className="text-xl font-bold text-white flex items-center space-x-2 mb-4">
              <span>📄</span>
              <span>Article Content</span>
            </h2>
            <div className="prose prose-invert max-w-none">
              <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                {article.original_content || 'No content available'}
              </p>
            </div>
          </div>
        )}

        {/* Split View (for processed articles) */}
        {article.processed && viewMode === 'split' && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Original Content */}
            <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                  <span>📄</span>
                  <span>Original Article</span>
                </h2>
                {article.biased_terms && article.biased_terms.length > 0 && (
                  <span className="px-3 py-1 bg-red-500/10 border border-red-500/30 rounded-full text-red-400 text-sm">
                    {article.biased_terms.length} biased terms
                  </span>
                )}
              </div>
              <div className="prose prose-invert max-w-none">
                <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {highlightText(article.original_content || '', article.biased_terms, 'biased')}
                </p>
              </div>
            </div>

            {/* Debiased Content */}
            <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                  <span>✨</span>
                  <span>Debiased Article</span>
                </h2>
                {article.total_changes > 0 && (
                  <span className="px-3 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-yellow-400 text-sm">
                    {article.total_changes} changes
                  </span>
                )}
              </div>
              <div className="prose prose-invert max-w-none">
                <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {article.debiased_content
                    ? highlightText(article.debiased_content, article.changes_made, 'debiased')
                    : 'No debiased version available'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Diff View (for processed articles) */}
        {article.processed && viewMode === 'diff' && article.changes_made && article.changes_made.length > 0 && (
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center space-x-2">
              <span>🔄</span>
              <span>Changes Made ({article.total_changes})</span>
            </h2>
            <div className="space-y-4">
              {article.changes_made.map((change, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/50 rounded-lg p-4 border border-gray-700"
                >
                  <div className="grid md:grid-cols-2 gap-4 mb-3">
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                      <div className="text-xs text-red-400 font-semibold mb-1">ORIGINAL</div>
                      <div className="text-gray-300 line-through">{change.original}</div>
                    </div>
                    <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                      <div className="text-xs text-green-400 font-semibold mb-1">DEBIASED</div>
                      <div className="text-gray-300">{change.debiased}</div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-400 bg-gray-900/50 rounded-lg p-3">
                    <span className="font-semibold text-yellow-400">Reason:</span> {change.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Headline (for processed articles) */}
        {article.processed && article.recommended_headline && (
          <div className="mt-6 bg-gradient-to-r from-primary-500/10 to-emerald-500/10 border border-primary-500/30 rounded-xl p-6">
            <h3 className="text-lg font-bold text-primary-400 mb-3 flex items-center space-x-2">
              <span>📰</span>
              <span>Recommended Neutral Headline</span>
            </h3>
            <p className="text-xl text-white font-medium">{article.recommended_headline}</p>
          </div>
        )}

        {/* Legend (only show for processed articles) */}
        {article.processed && article.is_biased && (
          <div className="mt-6 bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
            <h3 className="text-lg font-bold text-white mb-4">🎨 Color Legend</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-3">
                <span className="bg-red-500/20 text-red-300 border-b-2 border-red-500 px-3 py-1 rounded">
                  Biased Word
                </span>
                <span className="text-gray-400">= Original biased terms</span>
              </div>
              <div className="flex items-center space-x-3">
                <span className="bg-yellow-500/20 text-yellow-300 border-b-2 border-yellow-500 px-3 py-1 rounded">
                  Changed Word
                </span>
                <span className="text-gray-400">= Debiased replacements</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-4">
              💡 Hover over highlighted text to see detailed explanations
            </p>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════
            MERGED / UNIFIED ARTICLE SECTION
            Shows when this article was clustered with similar articles
            from different newspapers.
           ════════════════════════════════════════════════════════════ */}
        {article.cluster_info && (
          <div id="merged-section" className="mt-10">
            {/* Section Heading */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-1.5 h-10 rounded-full bg-gradient-to-b from-violet-500 to-fuchsia-500" />
              <div>
                <h2 className="text-2xl font-bold text-white">
                  🔗 Merged Article
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  {article.cluster_info.article_count} articles from{' '}
                  {article.cluster_info.sources.length} different newspaper
                  {article.cluster_info.sources.length > 1 ? 's' : ''} cover the same event
                </p>
              </div>
            </div>

            {/* Sources involved */}
            <div className="flex flex-wrap gap-2 mb-5">
              {article.cluster_info.sources.map((src) => (
                <span
                  key={src}
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-800/80 border border-gray-700`}
                >
                  <span className={`w-2 h-2 rounded-full ${SOURCE_COLORS[src] || 'bg-gray-500'}`} />
                  <span className={SOURCE_TEXT_COLORS[src] || 'text-gray-300'}>
                    {SOURCE_LABELS[src] || src}
                  </span>
                </span>
              ))}
              {article.cluster_info.avg_similarity && (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  📊 Avg Similarity: {(article.cluster_info.avg_similarity * 100).toFixed(1)}%
                </span>
              )}
            </div>

            {/* Unified Content Card */}
            {article.cluster_info.unified_content && (
              <div className="bg-gradient-to-br from-violet-500/5 to-fuchsia-500/5 border border-violet-500/20 rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-sm">
                    ✨
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">Unified Summary</h3>
                    <p className="text-[11px] text-gray-500">
                      Extractive summary generated from all {article.cluster_info.article_count} articles (LSA + TextRank)
                    </p>
                  </div>
                </div>
                {article.cluster_info.unified_headline && (
                  <h4 className="text-base font-semibold text-violet-300 mb-3">
                    {article.cluster_info.unified_headline}
                  </h4>
                )}
                <div className="prose prose-invert max-w-none">
                  <p className="text-gray-300 leading-relaxed whitespace-pre-wrap text-[15px]">
                    {article.cluster_info.unified_content}
                  </p>
                </div>

                {/* Analyze unified content for bias button */}
                <div className="mt-5 pt-4 border-t border-violet-500/10">
                  <button
                    onClick={async () => {
                      if (!article.cluster_info?.unified_content) return;
                      try {
                        const result = await api.fullProcess({
                          content: article.cluster_info.unified_content,
                          title: article.cluster_info.unified_headline || article.title || undefined,
                        });
                        showToast(
                          result.analysis.is_biased ? 'info' : 'success',
                          result.analysis.is_biased
                            ? `⚠️ Bias Detected! Score: ${result.analysis.bias_score}% — ${result.analysis.summary}`
                            : `✅ No significant bias detected. ${result.analysis.summary}`
                        );
                      } catch (err) {
                        console.error('Failed to analyze unified content:', err);
                        showToast('error', 'Bias analysis failed. Please try again.');
                      }
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 hover:border-violet-500/40 transition-all"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    Analyze Unified Article for Bias
                  </button>
                </div>
              </div>
            )}

            {/* Merged Articles List */}
            <div className="space-y-3">
              <h3 className="text-base font-semibold text-gray-300 mb-3">
                📰 Articles Merged Into This Cluster
              </h3>

              {article.cluster_info.merged_articles.map((merged) => {
                const srcColor = SOURCE_COLORS[merged.source] || 'bg-gray-500';
                const srcLabel = SOURCE_LABELS[merged.source] || merged.source;
                const isExpanded = expandedMergedId === merged.id;

                return (
                  <div
                    key={merged.id}
                    className="rounded-xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm overflow-hidden transition-all duration-300 hover:border-gray-700"
                  >
                    {/* Header Row */}
                    <button
                      onClick={() => setExpandedMergedId(isExpanded ? null : merged.id)}
                      className="w-full flex items-center justify-between p-4 text-left transition-colors hover:bg-gray-800/30"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <span className={`w-2.5 h-2.5 rounded-full ${srcColor} shrink-0`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-gray-100 truncate">
                            {merged.title || 'Untitled'}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">{srcLabel}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0 ml-3">
                        {/* Similarity Badge */}
                        {merged.similarity_percent !== null && (
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold ${
                              merged.similarity_percent >= 80
                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                                : merged.similarity_percent >= 60
                                ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                                : 'bg-gray-500/15 text-gray-400 border border-gray-500/20'
                            }`}
                          >
                            {merged.similarity_percent.toFixed(1)}% match
                          </span>
                        )}

                        {/* Bias badge */}
                        {merged.processed && merged.is_biased && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                            {merged.bias_score.toFixed(0)}% bias
                          </span>
                        )}
                        {merged.processed && !merged.is_biased && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Neutral
                          </span>
                        )}

                        {/* Expand arrow */}
                        <svg
                          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </button>

                    {/* Expanded Content */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-1 border-t border-gray-800/40">
                        <p className="text-sm text-gray-400 leading-relaxed whitespace-pre-wrap mb-3">
                          {merged.original_content}
                        </p>
                        <div className="flex items-center gap-3">
                          <Link
                            to={`/article/${merged.id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-primary-400 bg-primary-500/10 border border-primary-500/20 hover:bg-primary-500/20 transition-all"
                          >
                            View Full Article →
                          </Link>
                          {merged.url && (
                            <a
                              href={merged.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-400 bg-gray-800 border border-gray-700 hover:bg-gray-700 transition-all"
                            >
                              🔗 Original Source
                            </a>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ArticleDetailPage;
