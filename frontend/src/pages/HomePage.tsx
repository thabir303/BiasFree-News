import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { FullProcessResponse } from '../types/index';
import { api, authApi, type Statistics } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import ArticleInput from '../components/ArticleInput';
import ResultsDisplay from '../components/ResultsDisplay';
import usePageTitle from '../hooks/usePageTitle';

const AnimatedCounter = ({ target, duration = 1500 }: { target: number; duration?: number }) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (target === 0) return;
    let start = 0;
    const step = Math.ceil(target / (duration / 16));
    const timer = setInterval(() => {
      start += step;
      if (start >= target) { setCount(target); clearInterval(timer); }
      else setCount(start);
    }, 16);
    return () => clearInterval(timer);
  }, [target, duration]);
  return <>{count.toLocaleString()}</>;
};

const HomePage = () => {
  usePageTitle('Analyze');
  const [results, setResults] = useState<FullProcessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Statistics | null>(null);
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api.getStatistics().then(setStats).catch(() => {});
  }, []);

  const handleAnalyze = async (content: string, title: string) => {
    // Check authentication before analyzing
    if (!isAuthenticated) {
      setError('Please login to analyze articles');
      setTimeout(() => {
        navigate('/login', { state: { from: { pathname: '/' } } });
      }, 2000);
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const data = await api.fullProcess({ content, title: title || undefined });
      setResults(data);

      // Save analysis to user's history (fire and forget)
      try {
        await authApi.saveAnalysis({
          title: title || undefined,
          original_content: content,
          is_biased: data.analysis.is_biased,
          bias_score: data.analysis.bias_score,
          bias_summary: data.analysis.summary,
          biased_terms: data.analysis.biased_terms,
          confidence: data.analysis.confidence,
          debiased_content: data.debiased.debiased_content,
          changes_made: data.debiased.changes,
          total_changes: data.debiased.total_changes,
          generated_headlines: data.headline.generated_headlines,
          recommended_headline: data.headline.recommended_headline,
          headline_reasoning: data.headline.reasoning,
          processing_time: data.processing_time_seconds,
        });
      } catch (saveErr) {
        console.warn('Could not save analysis to history:', saveErr);
      }
    } catch (err: any) {
      console.error('Analysis error:', err);
      
      // Check if it's an authentication error
      if (err.response?.status === 401) {
        setError('Your session has expired. Please login again.');
        setTimeout(() => {
          navigate('/login', { state: { from: { pathname: '/' } } });
        }, 2000);
      } else {
        setError(
          err.response?.data?.detail ||
          err.message ||
          'Failed to analyze article. Please check backend connection.'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            <span className="bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
              BiasFree
            </span>{' '}
            News Analyzer
          </h1>
          {!isAuthenticated && (
            <div className="mt-4 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 px-4 py-3 rounded-lg inline-block">
              ℹ️ Please <button onClick={() => navigate('/login')} className="underline font-semibold">login</button> to analyze articles
            </div>
          )}

          {/* Stats Banner */}
          {stats && (
            <div className="mt-6 flex flex-wrap justify-center gap-6">
              {[
                { label: 'Articles Analyzed', value: stats.processed_articles, icon: '📊' },
                { label: 'Biases Detected', value: stats.biased_articles, icon: '⚠️' },
                { label: 'Total Articles', value: stats.total_articles, icon: '📰' },
              ].map((s) => (
                <div key={s.label} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800/40 border border-gray-700/50">
                  <span className="text-lg">{s.icon}</span>
                  <span className="text-xl font-bold text-white"><AnimatedCounter target={s.value} /></span>
                  <span className="text-xs text-gray-400">{s.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-4 mb-12">
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 text-center">
            <div className="text-3xl mb-3">🔍</div>
            <div className="font-semibold text-white mb-2">Bias Detection</div>
            <div className="text-sm text-gray-400">
              Identifies biased language using advanced AI analysis
            </div>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 text-center">
            <div className="text-3xl mb-3">✨</div>
            <div className="font-semibold text-white mb-2">Auto Debiasing</div>
            <div className="text-sm text-gray-400">
              Generates neutral versions with tracked changes
            </div>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 text-center">
            <div className="text-3xl mb-3">📊</div>
            <div className="font-semibold text-white mb-2">Detailed Analysis</div>
            <div className="text-sm text-gray-400">
              Word-by-word explanations and bias scores
            </div>
          </div>
        </div>

        {/* Input Section - Centered */}
        <div className="w-full mx-auto mb-8">
          <ArticleInput onAnalyze={handleAnalyze} loading={loading} />
        </div>

        {/* Results Section - Full Width Below */}
        <div>
          {loading && (
            <div className="glass-card p-8 flex flex-col items-center justify-center min-h-[300px]">
              <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500 mb-4"></div>
              <p className="text-gray-300 text-lg">Analyzing article...</p>
              <p className="text-gray-400 text-sm mt-2">
                Detecting bias, debiasing content, generating headline
              </p>
            </div>
          )}

          {error && (
            <div className="glass-card p-6 border-red-500/50 bg-red-500/10">
              <h3 className="text-xl font-semibold text-red-400 mb-2">Error</h3>
              <p className="text-gray-300">{error}</p>
            </div>
          )}

          {results && !loading && <ResultsDisplay results={results} />}
        </div>

        {/* Info Section */}
        <div className="mt-12 bg-gradient-to-r from-primary-500/10 to-emerald-500/10 border border-primary-500/30 rounded-xl p-6">
          <div className="flex items-start space-x-3">
            <span className="text-2xl">💡</span>
            <div>
              <div className="font-semibold text-primary-400 mb-2">How to use:</div>
              <ul className="text-sm text-gray-300 space-y-1 list-disc list-inside">
                <li>Paste article text directly for instant bias analysis</li>
                <li>Get detailed bias detection with word-level explanations</li>
                <li>View the AI-generated neutral version of the article</li>
                <li>Explore the database of automatically scraped articles in Articles tab</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
