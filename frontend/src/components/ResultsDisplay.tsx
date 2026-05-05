import { useState } from 'react';
import type { FullProcessResponse } from '../types/index';

interface ResultsDisplayProps {
    results: FullProcessResponse;
}

export default function ResultsDisplay({ results }: ResultsDisplayProps) {
    const { analysis, debiased, headline } = results;
    const [viewMode, setViewMode] = useState<'split' | 'diff'>('split');

    const getBiasColor = (score: number) => {
        if (score >= 70) return 'text-red-400 bg-red-500/10 border-red-500/30';
        if (score >= 40) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
        return 'text-green-400 bg-green-500/10 border-green-500/30';
    };

    const highlightBiasedTerms = (text: string, terms: any[] | null) => {
        if (!text || !terms || !Array.isArray(terms) || terms.length === 0) return text;

        const spans: Array<{ start: number; end: number; text: string; data: any }> = [];

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

        spans.sort((a, b) => a.start - b.start);

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
                    className="bg-red-500/20 text-red-300 border-b-2 border-red-500 px-0.5 py-0.5 rounded cursor-help"
                    title={`Biased: ${span.data.reason}\nSuggestion: ${span.data.neutral_alternative}`}
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

    const highlightDebiasedTerms = (text: string, changes: any[] | null, originalContent: string) => {
        if (!text || !changes || !Array.isArray(changes) || changes.length === 0 || !originalContent) return text;

        const spans: Array<{ start: number; end: number; text: string; data: any }> = [];
        const allPositions: Array<{ origStart: number; origEnd: number; change: any }> = [];

        changes.forEach((change: any) => {
            if (!change || !change.original || !change.debiased) return;
            const regex = new RegExp(change.original.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            let match;
            while ((match = regex.exec(originalContent)) !== null) {
                allPositions.push({
                    origStart: match.index,
                    origEnd: match.index + match[0].length,
                    change,
                });
            }
        });

        allPositions.sort((a, b) => a.origStart - b.origStart);

        const nonOverlapping: typeof allPositions = [];
        let lastEndPos = 0;
        for (const pos of allPositions) {
            if (pos.origStart >= lastEndPos) {
                nonOverlapping.push(pos);
                lastEndPos = pos.origEnd;
            }
        }

        let cumulativeOffset = 0;
        for (const pos of nonOverlapping) {
            const origTermLen = pos.origEnd - pos.origStart;
            const debTermLen = pos.change.debiased.length;

            const debStart = pos.origStart + cumulativeOffset;
            const debEnd = debStart + debTermLen;

            const textAtPos = text.substring(debStart, debEnd);
            if (textAtPos.toLowerCase() === pos.change.debiased.toLowerCase()) {
                spans.push({
                    start: debStart,
                    end: debEnd,
                    text: textAtPos,
                    data: pos.change,
                });
                cumulativeOffset += (debTermLen - origTermLen);
            }
        }

        spans.sort((a, b) => a.start - b.start);

        const parts: React.ReactElement[] = [];
        let lastIndex = 0;

        spans.forEach((span, idx) => {
            if (span.start > lastIndex) {
                parts.push(<span key={`text-${idx}`}>{text.slice(lastIndex, span.start)}</span>);
            }

            parts.push(
                <span
                    key={`highlight-${idx}`}
                    className="bg-yellow-500/20 text-yellow-300 border-b-2 border-yellow-500 px-0.5 py-0.5 rounded cursor-help"
                    title={`Original: ${span.data.original}\nReason: ${span.data.reason}`}
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

    return (
        <div className="space-y-6">
            {/* Analysis Header with Bias Score */}
            <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                    <div className="flex-1">
                        <h2 className="text-3xl font-bold text-white mb-2">
                            {analysis.is_biased ? '⚠ Biased' : '✅ Neutral'}
                        </h2>
                    </div>

                    {/* Bias Score Badge */}
                    {analysis.is_biased && (
                        <div className={`px-6 py-3 rounded-xl border text-center ${getBiasColor(analysis.bias_score)}`}>
                            <div className="text-3xl font-bold">{analysis.bias_score.toFixed(0)}%</div>
                            <div className="text-xs mt-1">Bias Score</div>
                        </div>
                    )}

                    {!analysis.is_biased && (
                        <div className="px-6 py-3 rounded-xl border border-green-500/30 bg-green-500/10 text-center">
                            <div className="text-2xl font-bold text-green-400">✅</div>
                            <div className="text-xs mt-1 text-green-400">No Bias Detected</div>
                        </div>
                    )}
                </div>

                {/* Analysis Summary */}
                {analysis.summary && (
                    <div className="bg-gray-800/50 rounded-lg p-4 border-l-4 border-yellow-500">
                        <h3 className="font-semibold text-yellow-400 mb-2">📋 Analysis Summary</h3>
                        <p className="text-gray-300">{analysis.summary}</p>
                    </div>
                )}
            </div>

            {/* View Mode Toggle */}
            {debiased.debiased_content && (
                <div className="flex justify-center">
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

            {/* Split View - Content Comparison */}
            {viewMode === 'split' && (
                <div className="grid lg:grid-cols-2 gap-6">
                    {/* Original Content */}
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
                                {highlightBiasedTerms(debiased.original_content, analysis.biased_terms)}
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
                            {debiased.changes && debiased.changes.length > 0 && (
                                <span className="px-3 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-yellow-400 text-sm">
                                    {debiased.changes.length} changes
                                </span>
                            )}
                        </div>
                        <div className="prose prose-invert max-w-none">
                            <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                                {highlightDebiasedTerms(debiased.debiased_content, debiased.changes, debiased.original_content)}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Diff View */}
            {viewMode === 'diff' && debiased.changes && debiased.changes.length > 0 && (
                <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
                    <h2 className="text-xl font-bold text-white mb-6 flex items-center space-x-2">
                        <span>🔄</span>
                        <span>Changes Made ({debiased.changes.length})</span>
                    </h2>
                    <div className="space-y-4">
                        {debiased.changes.map((change, idx) => (
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

            {/* Biased Terms Detail */}
            {analysis.biased_terms.length > 0 && (
                <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
                    <h3 className="text-xl font-bold text-white mb-4">🔍 Biased Terms Detail</h3>
                    <div className="space-y-3">
                        {analysis.biased_terms.map((term, i) => (
                            <div key={i} className="p-4 bg-red-500/10 rounded-lg border border-red-500/30">
                                <p className="font-semibold text-red-300">{term.term}</p>
                                <p className="text-sm text-gray-400 mt-1">{term.reason}</p>
                                <p className="text-sm text-green-400 mt-1">→ {term.neutral_alternative}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Headlines */}
            <div className="bg-gradient-to-r from-primary-500/10 to-emerald-500/10 border border-primary-500/30 rounded-xl p-6">
                <h3 className="text-lg font-bold text-primary-400 mb-4 flex items-center space-x-2">
                    <span>📰</span>
                    <span>Headlines</span>
                </h3>

                {headline.original_title && (
                    <div className="mb-4">
                        <h4 className="text-sm font-semibold text-gray-400 mb-2">Original:</h4>
                        <p className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg text-gray-300">{headline.original_title}</p>
                    </div>
                )}

                <div>
                    <h4 className="text-sm font-semibold text-gray-400 mb-2">Recommended:</h4>
                    <p className="p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg font-medium text-white">
                        {headline.recommended_headline}
                    </p>
                </div>
            </div>

            {/* Color Legend */}
            {analysis.is_biased && (
                <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
                    <h3 className="text-lg font-bold text-white mb-4">🎨 Color Legend</h3>
                    <div className="grid md:grid-cols-2 gap-4">
                        <div className="flex items-center space-x-3">
                            <span className="bg-red-500/20 text-red-300 border-b-2 border-red-500 px-3 py-1 rounded">
                                Biased
                            </span>
                            <span className="text-gray-400">= Original biased terms</span>
                        </div>
                        <div className="flex items-center space-x-3">
                            <span className="bg-yellow-500/20 text-yellow-300 border-b-2 border-yellow-500 px-3 py-1 rounded">
                                Changed
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
    );
}
