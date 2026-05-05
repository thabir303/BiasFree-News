import { useState } from 'react';

interface ArticleInputProps {
    onAnalyze: (content: string, title: string) => void;
    loading: boolean;
}

export default function ArticleInput({ onAnalyze, loading }: ArticleInputProps) {
    const [content, setContent] = useState('');
    const [title, setTitle] = useState('');

    const MAX_CONTENT_CHARS = 2000;
    const MIN_CONTENT_CHARS = 50;
    const MAX_TITLE_CHARS = 200;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (content.trim().length >= MIN_CONTENT_CHARS && content.length <= MAX_CONTENT_CHARS && title.length <= MAX_TITLE_CHARS) {
            onAnalyze(content, title);
        }
    };

    const charCount = content.length;
    const titleCharCount = title.length;
    const isTitleValid = titleCharCount <= MAX_TITLE_CHARS;
    const isContentTooShort = charCount < MIN_CONTENT_CHARS;
    const isContentTooLong = charCount > MAX_CONTENT_CHARS;
    const isValid = !isContentTooShort && !isContentTooLong && isTitleValid;

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
                        className={`input-field w-full ${!isTitleValid ? 'border-red-500' : ''}`}
                        disabled={loading}
                        maxLength={MAX_TITLE_CHARS}
                    />
                    <div className={`text-sm mt-1 ${!isTitleValid ? 'text-red-400' : 'text-gray-400'}`}>
                        {titleCharCount}/{MAX_TITLE_CHARS} chars
                        {!isTitleValid && ' (Maximum 200 character)'}
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">নিবন্ধ *</label>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        className={`textarea-field w-full ${isContentTooLong ? 'border-red-500' : ''}`}
                        disabled={loading}
                        rows={12}
                    />
                    <div className={`text-sm mt-2 ${isContentTooLong ? 'text-red-400' : isContentTooShort ? 'text-yellow-400' : 'text-green-400'}`}>
                        {charCount}/{MAX_CONTENT_CHARS} chars
                        {isContentTooShort && ` (Minimum ${MIN_CONTENT_CHARS} characters)`}
                        {isContentTooLong && ` (Maximum ${MAX_CONTENT_CHARS} characters)`}
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
