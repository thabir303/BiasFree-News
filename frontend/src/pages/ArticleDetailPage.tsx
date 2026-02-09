import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type Article } from '../services/api';

const ArticleDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [viewMode, setViewMode] = useState<'split' | 'diff'>('split');

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
      alert('Failed to analyze article. Please try again.');
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
    } else if (type === 'debiased' && article?.changes_made && Array.isArray(article.changes_made)) {
      article.changes_made.forEach((change: any) => {
        if (!change || !change.debiased) return;
        const regex = new RegExp(change.debiased.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        let match;
        while ((match = regex.exec(text)) !== null) {
          spans.push({
            start: match.index,
            end: match.index + match[0].length,
            text: match[0],
            data: change,
          });
        }
      });
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
          <span className="invisible group-hover:visible absolute z-10 w-64 p-3 mt-2 text-sm bg-gray-900 border border-gray-700 rounded-lg shadow-xl -left-1/2 transform -translate-x-1/2">
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
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <Link
          to="/articles"
          className="inline-flex items-center space-x-2 text-gray-400 hover:text-white mb-6 transition-colors"
        >
          <span>←</span>
          <span>Back to Articles</span>
        </Link>

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
                  <span className="px-3 py-1 bg-primary-500/10 text-primary-400 border border-primary-500/30 rounded-full">
                    📂 {article.category}
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
                {article.original_content || article.content || 'No content available'}
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
                  {highlightText(article.original_content || article.content || '', article.biased_terms, 'biased')}
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
      </div>
    </div>
  );
};

export default ArticleDetailPage;
