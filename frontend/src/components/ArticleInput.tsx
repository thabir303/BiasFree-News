import { useState } from 'react';

interface ArticleInputProps {
    onAnalyze: (content: string, title: string) => void;
    loading: boolean;
}

export default function ArticleInput({ onAnalyze, loading }: ArticleInputProps) {
    const [content, setContent] = useState('');
    const [title, setTitle] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (content.trim().length >= 50) {
            onAnalyze(content, title);
        }
    };

    const charCount = content.length;
    const isValid = charCount >= 50;

    return (
        <div className="glass-card w-full p-6">
            <h2 className="text-2xl font-bold mb-4 text-primary-400">নিবন্ধ বিশ্লেষণ করুন</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">শিরোনাম (Optional)</label>
                    <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        className="input-field w-full"
                        disabled={loading}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">নিবন্ধ *</label>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        className="textarea-field w-full"
                        disabled={loading}
                        rows={12}
                    />
                    <div className="text-sm mt-2 text-gray-400">
                        {charCount} chars {!isValid && '(minimum 50 required)'}
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={!isValid || loading}
                    className="btn-primary w-full disabled:opacity-50"
                >
                    {loading ? 'Processing...' : '🔍 Analyze'}
                </button>
            </form>
        </div>
    );
}
