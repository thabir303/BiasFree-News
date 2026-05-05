import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { authApi, type UserAnalysis } from '../services/api';
import { ChevronRight, ArrowLeft } from 'lucide-react';
import usePageTitle from '../hooks/usePageTitle';

const AnalysisDetailPage = () => {
  usePageTitle('Analysis Detail');
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<UserAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'split' | 'diff'>('split');

  useEffect(() => {
    if (id) {
      fetchAnalysis(parseInt(id));
    }
  }, [id]);

  const fetchAnalysis = async (analysisId: number) => {
    setLoading(true);
    try {
      // Fetch all analyses and find by id
      const result = await authApi.getMyAnalyses({ limit: 100 });
      const found = result.analyses.find(a => a.id === analysisId);
      setAnalysis(found || null);
    } catch (error) {
      console.error('Failed to fetch analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const getBiasColor = (score: number) => {
    if (score >= 70) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (score >= 40) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    return 'text-green-400 bg-green-500/10 border-green-500/30';
  };

  const highlightBiasedTerms = (text: string, terms: any[] | null, type: 'biased' | 'debiased') => {
    if (!text || !terms || !Array.isArray(terms) || terms.length === 0) return text;

    const spans: Array<{ start: number; end: number; text: string; data: any }> = [];

    if (type === 'biased') {
      terms.forEach((term: any) => {
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
    } else if (type === 'debiased' && analysis?.changes_made && analysis?.original_content) {
      // Instead of highlighting every occurrence of the debiased word,
      // find where the ORIGINAL biased terms were in the original text,
      // then compute their corresponding positions in the debiased text.
      const originalText = analysis.original_content;

      const allPositions: Array<{ origStart: number; origEnd: number; change: any }> = [];

      analysis.changes_made.forEach((change: any) => {
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

    // Remove overlapping spans
    const filtered: typeof spans = [];
    let lastEnd = 0;
    for (const span of spans) {
      if (span.start >= lastEnd) {
        filtered.push(span);
        lastEnd = span.end;
      }
    }

    const parts: React.ReactElement[] = [];
    let lastIndex = 0;

    filtered.forEach((span, idx) => {
      if (span.start > lastIndex) {
        parts.push(<span key={`text-${idx}`}>{text.slice(lastIndex, span.start)}</span>);
      }

      parts.push(
        <span
          key={`highlight-${idx}`}
          className={`
            relative group cursor-help px-0.5 py-0.5 rounded transition-all
            ${type === 'biased'
              ? 'bg-red-500/20 text-red-300 border-b-2 border-red-500'
              : 'bg-yellow-500/20 text-yellow-300 border-b-2 border-yellow-500'
            }
          `}
          title={type === 'biased'
            ? `Biased: ${span.data.reason}\nSuggestion: ${span.data.neutral_alternative}`
            : `Original: ${span.data.original}\nReason: ${span.data.reason}`
          }
        >
          {span.text}
        </span>
      );

      lastIndex = span.end;
    });

    if (lastIndex < text.length) {
      parts.push(<span key="text-end">{text.slice(lastIndex)}</span>);
    }

    return <>{parts}</>;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-gray-300 mb-2">Analysis Not Found</h2>
          <Link to="/dashboard" className="text-primary-400 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const biasScore = analysis.bias_score ?? 0;

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-xs text-gray-500 mb-8">
          <Link to="/dashboard" className="hover:text-primary-400 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" />
            Dashboard
          </Link>
          <ChevronRight className="w-3 h-3 text-gray-700" />
          <span className="text-gray-400 font-medium truncate max-w-xs">
            {analysis.title || 'Untitled Analysis'}
          </span>
        </nav>

        {/* Header */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-white">
                  {analysis.title || 'Untitled Article'}
                </h1>
                <span className="shrink-0 px-2.5 py-1 text-xs font-semibold rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/30">
                  Manual Analysis
                </span>
              </div>
              <div className="flex flex-wrap gap-3 text-sm text-gray-400">
                <span className="px-3 py-1 bg-gray-800 rounded-full">
                  📅 {new Date(analysis.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
                {analysis.processing_time && (
                  <span className="px-3 py-1 bg-gray-800 rounded-full">
                    ⏱ {analysis.processing_time.toFixed(1)}s
                  </span>
                )}
                {analysis.total_changes != null && analysis.total_changes > 0 && (
                  <span className="px-3 py-1 bg-gray-800 rounded-full">
                    ✏️ {analysis.total_changes} changes
                  </span>
                )}
              </div>
            </div>

            {/* Bias Score */}
            {analysis.is_biased ? (
              <div className={`px-6 py-3 rounded-xl border text-center ${getBiasColor(biasScore)}`}>
                <div className="text-3xl font-bold">{biasScore.toFixed(0)}%</div>
                <div className="text-xs mt-1">Bias Score</div>
              </div>
            ) : (
              <div className="px-6 py-3 rounded-xl border border-green-500/30 bg-green-500/10 text-center">
                <div className="text-2xl font-bold text-green-400">✅</div>
                <div className="text-xs mt-1 text-green-400">No Bias Detected</div>
              </div>
            )}
          </div>

          {/* Bias Summary */}
          {analysis.bias_summary && (
            <div className="bg-gray-800/50 rounded-lg p-4 border-l-4 border-yellow-500">
              <h3 className="font-semibold text-yellow-400 mb-2">📋 Analysis Summary</h3>
              <p className="text-gray-300">{analysis.bias_summary}</p>
            </div>
          )}
        </div>

        {/* Biased Terms */}
        {analysis.biased_terms && analysis.biased_terms.length > 0 && (
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
              <span>⚠️</span>
              <span>Biased Terms ({analysis.biased_terms.length})</span>
            </h2>
            <div className="space-y-3">
              {analysis.biased_terms.map((term: any, idx: number) => (
                <div key={idx} className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="font-semibold text-red-300 mb-1">"{term.term}"</p>
                      <p className="text-sm text-gray-400 mb-2">{term.reason}</p>
                      <div className="text-sm">
                        <span className="text-gray-500">Suggestion: </span>
                        <span className="text-green-400">{term.neutral_alternative}</span>
                      </div>
                    </div>
                    {term.severity && (
                      <span className={`shrink-0 px-2 py-0.5 text-[10px] font-semibold rounded-full border ${
                        term.severity === 'high' ? 'text-red-400 bg-red-500/10 border-red-500/30' :
                        term.severity === 'medium' ? 'text-amber-400 bg-amber-500/10 border-amber-500/30' :
                        'text-blue-400 bg-blue-500/10 border-blue-500/30'
                      }`}>
                        {term.severity}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* View Mode Toggle */}
        {analysis.debiased_content && analysis.debiased_content !== analysis.original_content && (
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

        {/* Split View */}
        {viewMode === 'split' && (
          <div className={`grid ${analysis.debiased_content && analysis.debiased_content !== analysis.original_content ? 'lg:grid-cols-2' : 'lg:grid-cols-1'} gap-6`}>
            {/* Original */}
            <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                  <span>📄</span>
                  <span>Original Article</span>
                </h2>
                {analysis.biased_terms && analysis.biased_terms.length > 0 && (
                  <span className="px-3 py-1 bg-red-500/10 border border-red-500/30 rounded-full text-red-400 text-sm">
                    {analysis.biased_terms.length} biased terms
                  </span>
                )}
              </div>
              <div className="prose prose-invert max-w-none">
                <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {highlightBiasedTerms(analysis.original_content, analysis.biased_terms, 'biased')}
                </p>
              </div>
            </div>

            {/* Debiased */}
            {analysis.debiased_content && analysis.debiased_content !== analysis.original_content && (
              <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                    <span>✨</span>
                    <span>Debiased Article</span>
                  </h2>
                  {analysis.total_changes != null && analysis.total_changes > 0 && (
                    <span className="px-3 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-yellow-400 text-sm">
                      {analysis.total_changes} changes
                    </span>
                  )}
                </div>
                <div className="prose prose-invert max-w-none">
                  <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {highlightBiasedTerms(analysis.debiased_content, analysis.changes_made, 'debiased')}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Diff View */}
        {viewMode === 'diff' && analysis.changes_made && analysis.changes_made.length > 0 && (
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center space-x-2">
              <span>🔄</span>
              <span>Changes Made ({analysis.changes_made.length})</span>
            </h2>
            <div className="space-y-4">
              {analysis.changes_made.map((change: any, idx: number) => (
                <div key={idx} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
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

        {/* Recommended Headline */}
        {analysis.recommended_headline && (
          <div className="mt-6 bg-gradient-to-r from-primary-500/10 to-emerald-500/10 border border-primary-500/30 rounded-xl p-6">
            <h3 className="text-lg font-bold text-primary-400 mb-3 flex items-center space-x-2">
              <span>📰</span>
              <span>Recommended Neutral Headline</span>
            </h3>
            <p className="text-xl text-white font-medium">{analysis.recommended_headline}</p>
            {analysis.headline_reasoning && (
              <p className="text-sm text-gray-400 mt-2">{analysis.headline_reasoning}</p>
            )}
          </div>
        )}

        {/* All Generated Headlines */}
        {analysis.generated_headlines && analysis.generated_headlines.length > 1 && (
          <div className="mt-4 bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
            <h3 className="text-lg font-bold text-white mb-4">📝 All Generated Headlines</h3>
            <div className="space-y-2">
              {analysis.generated_headlines.map((h, idx) => (
                <div key={idx} className={`p-3 rounded-lg border ${
                  h === analysis.recommended_headline
                    ? 'border-primary-500/30 bg-primary-500/5 text-primary-300'
                    : 'border-gray-800 bg-gray-800/30 text-gray-300'
                }`}>
                  <span className="text-xs text-gray-500 mr-2">{idx + 1}.</span>
                  {h}
                  {h === analysis.recommended_headline && (
                    <span className="ml-2 text-xs text-primary-400">⭐ Recommended</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Legend */}
        {analysis.is_biased && (
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

export default AnalysisDetailPage;
