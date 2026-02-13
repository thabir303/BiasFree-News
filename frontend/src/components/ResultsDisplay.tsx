import type { FullProcessResponse } from '../types/index';

interface ResultsDisplayProps {
    results: FullProcessResponse;
}

export default function ResultsDisplay({ results }: ResultsDisplayProps) {
    const { analysis, debiased, headline } = results;

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
            {/* Bias Analysis */}
            <div className="glass-card p-6">
                <h3 className="text-2xl font-bold mb-4">{analysis.is_biased ? '⚠ Biased' : '✅ Neutral'}</h3>

                <div className="mb-4">
                    <p>Bias Score: {analysis.bias_score.toFixed(1)}%</p>
                    <div className="w-full bg-gray-700 rounded-full h-3 mt-2">
                        <div
                            className="h-3 rounded-full bg-red-500"
                            style={{ width: `${analysis.bias_score}%` }}
                        />
                    </div>
                </div>

                <p className="text-gray-300">{analysis.summary}</p>

                {analysis.biased_terms.length > 0 && (
                    <div className="mt-4 space-y-2">
                        <h4 className="font-semibold">Biased Terms:</h4>
                        {analysis.biased_terms.map((term, i) => (
                            <div key={i} className="p-3 bg-red-500/20 rounded-lg border border-red-500/50">
                                <p className="font-medium">{term.term}</p>
                                <p className="text-sm opacity-90">{term.reason}</p>
                                <p className="text-sm mt-1">→ {term.neutral_alternative}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Debiased Content */}
            <div className="glass-card p-6">
                <h3 className="text-2xl font-bold mb-6">📝 Content Comparison</h3>

                <div className="grid lg:grid-cols-2 gap-6 mb-6">
                    {/* Original Content */}
                    <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-5">
                        <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-bold text-white flex items-center space-x-2">
                                <span>📄</span>
                                <span>Original Article</span>
                            </h4>
                            {analysis.biased_terms && analysis.biased_terms.length > 0 && (
                                <span className="px-2.5 py-1 bg-red-500/10 border border-red-500/30 rounded-full text-red-400 text-xs font-semibold">
                                    {analysis.biased_terms.length} biased terms
                                </span>
                            )}
                        </div>
                        <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 max-h-[500px] overflow-y-auto">
                            <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">
                                {highlightBiasedTerms(debiased.original_content, analysis.biased_terms)}
                            </p>
                        </div>
                    </div>

                    {/* Debiased Content */}
                    <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-5">
                        <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-bold text-white flex items-center space-x-2">
                                <span>✨</span>
                                <span>Debiased Article</span>
                            </h4>
                            {debiased.changes && debiased.changes.length > 0 && (
                                <span className="px-2.5 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-yellow-400 text-xs font-semibold">
                                    {debiased.changes.length} changes
                                </span>
                            )}
                        </div>
                        <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-4 max-h-[500px] overflow-y-auto">
                            <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">
                                {highlightDebiasedTerms(debiased.debiased_content, debiased.changes, debiased.original_content)}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Changes Summary */}
                {debiased.changes && debiased.changes.length > 0 && (
                    <div className="bg-gray-800/50 rounded-lg p-5 border border-gray-700 mb-4">
                        <h4 className="text-base font-bold text-white mb-3 flex items-center space-x-2">
                            <span>🔄</span>
                            <span>Changes Made ({debiased.changes.length})</span>
                        </h4>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            {debiased.changes.map((change, idx) => (
                                <div key={idx} className="flex items-start gap-3 text-sm bg-gray-900/30 rounded-lg p-3">
                                    <span className="text-gray-500 shrink-0 font-semibold">{idx + 1}.</span>
                                    <div className="flex-1">
                                        <span className="text-red-400 line-through">{change.original}</span>
                                        <span className="text-gray-500 mx-2">→</span>
                                        <span className="text-green-400 font-medium">{change.debiased}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Legend */}
                <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
                    <div className="flex flex-wrap gap-6 text-sm">
                        <div className="flex items-center gap-2">
                            <span className="bg-red-500/20 text-red-300 border-b-2 border-red-500 px-2 py-1 rounded">
                                Biased
                            </span>
                            <span className="text-gray-400">= Original biased terms</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="bg-yellow-500/20 text-yellow-300 border-b-2 border-yellow-500 px-2 py-1 rounded">
                                Changed
                            </span>
                            <span className="text-gray-400">= Debiased replacements</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Headlines */}
            <div className="glass-card p-6">
                <h3 className="text-2xl font-bold mb-4">📰 Headlines</h3>

                {headline.original_title && (
                    <div className="mb-4">
                        <h4 className="text-sm font-semibold text-gray-400 mb-2">Original:</h4>
                        <p className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">{headline.original_title}</p>
                    </div>
                )}

                <div>
                    <h4 className="text-sm font-semibold text-gray-400 mb-2">Recommended:</h4>
                    <p className="p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg font-medium">
                        {headline.recommended_headline}
                    </p>
                </div>
            </div>
        </div>
    );
}
