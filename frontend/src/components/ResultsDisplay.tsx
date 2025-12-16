import type { FullProcessResponse } from '../types/index';

interface ResultsDisplayProps {
    results: FullProcessResponse;
}

export default function ResultsDisplay({ results }: ResultsDisplayProps) {
    const { analysis, debiased, headline } = results;

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
                <h3 className="text-2xl font-bold mb-4">📝 Debiased Content</h3>

                <div className="grid md:grid-cols-2 gap-4">
                    <div>
                        <h4 className="text-sm font-semibold text-gray-400 mb-2">Original:</h4>
                        <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 max-h-96 overflow-y-auto">
                            <p className="text-gray-300 whitespace-pre-wrap">{debiased.original_content}</p>
                        </div>
                    </div>

                    <div>
                        <h4 className="text-sm font-semibold text-gray-400 mb-2">Debiased:</h4>
                        <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-4 max-h-96 overflow-y-auto">
                            <p className="text-gray-300 whitespace-pre-wrap">{debiased.debiased_content}</p>
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
