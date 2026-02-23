import { useState, useEffect, useRef } from 'react';
import { api, type Newspaper } from '../services/api';
import DateRangePicker from '../components/DateRangePicker';

const ManualScrapingPage = () => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>([
    'prothom_alo',
    'daily_star',
    'jugantor',
    'samakal',
    'naya_diganta',
    'ittefaq',
  ]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const today = new Date().toISOString().split('T')[0]; // max date cap

  const newspapers: Newspaper[] = [
    { key: 'prothom_alo', name: 'প্রথম আলো', base_url: 'https://www.prothomalo.com', language: 'bn', enabled: true },
    { key: 'daily_star', name: 'ডেইলি স্টার', base_url: 'https://bangla.thedailystar.net', language: 'en', enabled: true },
    { key: 'jugantor', name: 'যুগান্তর', base_url: 'https://www.jugantor.com', language: 'bn', enabled: true },
    { key: 'samakal', name: 'সমকাল', base_url: 'https://samakal.com', language: 'bn', enabled: true },
    { key: 'naya_diganta', name: 'নয়া দিগন্ত', base_url: 'https://dailynayadiganta.com', language: 'bn', enabled: true },
    { key: 'ittefaq', name: 'ইত্তেফাক', base_url: 'https://www.ittefaq.com.bd', language: 'bn', enabled: true },
  ];

  const NEWSPAPER_LOGOS: Record<string, string> = {
    prothom_alo: '/prothomalo.png',
    daily_star: '/dailystar.png',
    jugantor: '/jugantor.png',
    samakal: '/samakal.png',
    naya_diganta: '/nayadiganta.png',
    ittefaq: '/ittefaq.png',
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const pollJobStatus = async (id: string) => {
    try {
      const status = await api.getScrapingStatus(id);
      setJobStatus(status.status);
      
      if (status.status === 'completed') {
        setLoading(false);
        const stats = status.statistics || {};
        setResult({
          status: 'success',
          message: 'Scraping completed successfully!',
          total_scraped: stats.total_scraped ?? 0,
          total_processed: stats.total_processed ?? 0,
          by_source: stats.by_source ?? {},
          errors: stats.errors ?? [],
        });
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      } else if (status.status === 'failed') {
        setLoading(false);
        setError(status.error || 'Scraping failed');
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      }
    } catch (err) {
      console.error('Failed to poll job status:', err);
    }
  };

  const toggleSource = (source: string) => {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]
    );
  };

  const handleScrape = async () => {
    setError('');
    setResult(null);
    setJobId(null);
    setJobStatus('');

    if (selectedSources.length === 0) {
      setError('Please select at least one newspaper source');
      return;
    }

    setLoading(true);

    try {
      const response = await api.manualScrape({
        sources: selectedSources,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });

      if (response.status === 'started' && response.job_id) {
        // Background job started
        setJobId(response.job_id);
        setJobStatus('running');
        setResult({
          status: 'started',
          message: response.message,
          sources: response.sources
        });
        
        // Start polling for status
        pollingRef.current = setInterval(() => {
          pollJobStatus(response.job_id);
        }, 3000); // Poll every 3 seconds
      } else {
        // Direct response - flatten statistics into result for display
        setLoading(false);
        const stats = response.statistics || {};
        setResult({
          status: response.status || 'completed',
          message: response.message || 'Scraping completed successfully',
          total_scraped: stats.total_scraped ?? response.total_scraped ?? 0,
          total_processed: stats.total_processed ?? response.total_processed ?? 0,
          by_source: stats.by_source ?? response.by_source ?? {},
          errors: stats.errors ?? response.errors ?? [],
        });
      }
    } catch (err: any) {
      setLoading(false);
      setError(err.response?.data?.detail || 'Failed to start scraping. Please try again.');
      console.error('Scraping error:', err);
    }
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">🔍 Manual Scraping</h1>
          <p className="text-gray-400">
            Trigger on-demand scraping for specific newspapers and date ranges
          </p>
        </div>

        {/* Scraping Form */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center space-x-2">
            <span>⚙️</span>
            <span>Configuration</span>
          </h2>

          {/* Date Range */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-300 mb-3">
              📅 Date Range <span className="text-gray-500 font-normal">(Optional)</span>
            </label>
            <DateRangePicker
              fromDate={startDate}
              toDate={endDate}
              onFromChange={setStartDate}
              onToChange={setEndDate}
              disabled={loading}
              maxDate={today}
            />
            <p className="text-xs text-gray-600 mt-2">
              Leave empty to scrape today's articles. Future dates are not allowed.
            </p>
          </div>

          {/* Source Selection */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-300 mb-3">
              📰 Select Newspapers
            </label>
            <div className="grid md:grid-cols-3 gap-3">
              {newspapers.map((newspaper) => (
                <button
                  key={newspaper.key}
                  onClick={() => toggleSource(newspaper.key)}
                  className={`
                    p-4 rounded-lg border-2 text-left transition-all
                    ${
                      selectedSources.includes(newspaper.key)
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                    }
                  `}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {NEWSPAPER_LOGOS[newspaper.key] && (
                        <img
                          src={NEWSPAPER_LOGOS[newspaper.key]}
                          alt={newspaper.name}
                          className="w-10 h-10 rounded-md object-contain shrink-0 bg-white p-1"
                        />
                      )}
                      <div>
                        <div className="font-semibold text-white">{newspaper.name}</div>
                        <div className="text-xs text-gray-500 mt-1">{newspaper.base_url}</div>
                      </div>
                    </div>
                    <div
                      className={`
                        w-6 h-6 rounded-md border-2 flex items-center justify-center
                        ${
                          selectedSources.includes(newspaper.key)
                            ? 'border-primary-500 bg-primary-500'
                            : 'border-gray-600'
                        }
                      `}
                    >
                      {selectedSources.includes(newspaper.key) && (
                        <span className="text-white text-sm">✓</span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleScrape}
              disabled={loading || selectedSources.length === 0}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-primary-500 to-emerald-500 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-primary-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center space-x-2">
                  <span className="animate-spin">⏳</span>
                  <span>Scraping in Progress...</span>
                </span>
              ) : (
                '🚀 Start Scraping'
              )}
            </button>
            {(startDate || endDate || selectedSources.length !== newspapers.length) && (
              <button
                onClick={() => {
                  setStartDate('');
                  setEndDate('');
                  setSelectedSources(newspapers.map((n) => n.key));
                  setError('');
                  setResult(null);
                }}
                className="px-6 py-3 bg-gray-800 text-gray-300 font-semibold rounded-lg hover:bg-gray-700 transition-all"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">❌</span>
              <div>
                <div className="font-semibold text-red-400">Error</div>
                <div className="text-gray-300 text-sm">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Running Job Status */}
        {loading && jobStatus === 'running' && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-6 mb-6">
            <div className="flex items-center space-x-3">
              <span className="text-3xl animate-spin">🔄</span>
              <div>
                <div className="text-xl font-bold text-yellow-400">Scraping in Progress...</div>
                <div className="text-gray-400 text-sm">
                  Job ID: {jobId} - This may take a few minutes. Do not close this page.
                </div>
              </div>
            </div>
            <div className="mt-4 bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-sm text-gray-400">
                Scraping newspapers: {selectedSources.map(s => s.replace('_', ' ')).join(', ')}
              </div>
            </div>
          </div>
        )}

        {/* Success Result */}
        {result && result.status !== 'started' && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <span className="text-3xl">✅</span>
              <div>
                <div className="text-xl font-bold text-green-400">Scraping Complete!</div>
                <div className="text-gray-400 text-sm">{result.message}</div>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-4 mt-6">
              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400 mb-1">Total Scraped</div>
                <div className="text-2xl font-bold text-white">{result.total_scraped || result.total_articles || 0}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400 mb-1">Processed</div>
                <div className="text-2xl font-bold text-primary-400">{result.total_processed || result.new_articles || 0}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400 mb-1">By Source</div>
                <div className="text-sm font-bold text-yellow-400">
                  {result.by_source ? Object.keys(result.by_source).length : 0} sources
                </div>
              </div>
            </div>

            {result.by_source && Object.keys(result.by_source).length > 0 && (
              <div className="mt-4 bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400 mb-2">Articles per Source</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(result.by_source).map(([source, stats]: [string, any]) => {
                    // Handle both object and number formats
                    const articleCount = typeof stats === 'object' 
                      ? (stats?.new_articles ?? stats?.total_scraped ?? 0)
                      : (stats || 0);
                    
                    return (
                      <span
                        key={source}
                        className="px-3 py-1 bg-primary-500/10 border border-primary-500/30 rounded-full text-primary-400 text-sm"
                      >
                        {source.replace(/_/g, ' ')}: {articleCount}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            {result.errors && result.errors.length > 0 && (
              <div className="mt-4 bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/30">
                <div className="text-sm text-yellow-400 mb-2">⚠️ Warnings</div>
                <ul className="text-sm text-gray-400 list-disc list-inside">
                  {result.errors.slice(0, 5).map((err: string, i: number) => (
                    <li key={i}>{err}</li>
                  ))}
                  {result.errors.length > 5 && <li>...and {result.errors.length - 5} more</li>}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Info Box */}
        <div className="mt-6 bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-start space-x-3">
            <span className="text-xl">💡</span>
            <div className="text-sm text-gray-300">
              <div className="font-semibold text-blue-400 mb-1">How it works:</div>
              <ul className="space-y-1 list-disc list-inside">
                <li>Select one or more newspapers to scrape</li>
                <li>Optionally specify a date range for historical scraping</li>
                <li>Articles will be automatically analyzed for bias detection</li>
                <li>Biased articles will be debiased using AI</li>
                <li>Duplicate articles are automatically skipped</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ManualScrapingPage;
