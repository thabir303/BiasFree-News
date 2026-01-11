import { useState, useEffect } from 'react';
import { api, type Statistics, type SchedulerStatus } from '../services/api';

const DashboardPage = () => {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 300000); 
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [stats, scheduler] = await Promise.all([
        api.getStatistics(),
        api.getSchedulerStatus(),
      ]);
      setStatistics(stats);
      setSchedulerStatus(scheduler);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  const biasedPercentage = statistics
    ? ((statistics.biased_count / statistics.total_articles) * 100).toFixed(1)
    : '0';

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">📊 Dashboard</h1>
          <p className="text-gray-400">Real-time statistics and monitoring</p>
        </div>

        {/* Statistics Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/30 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">📰</span>
              <span className="text-sm text-blue-400 font-semibold">TOTAL</span>
            </div>
            <div className="text-4xl font-bold text-white mb-1">{statistics?.total_articles || 0}</div>
            <div className="text-sm text-gray-400">Articles Collected</div>
          </div>

          <div className="bg-gradient-to-br from-red-500/10 to-red-600/10 border border-red-500/30 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">⚠️</span>
              <span className="text-sm text-red-400 font-semibold">BIASED</span>
            </div>
            <div className="text-4xl font-bold text-white mb-1">{statistics?.biased_count || 0}</div>
            <div className="text-sm text-gray-400">{biasedPercentage}% of Total</div>
          </div>

          <div className="bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/30 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">✅</span>
              <span className="text-sm text-green-400 font-semibold">NEUTRAL</span>
            </div>
            <div className="text-4xl font-bold text-white mb-1">
              {(statistics?.total_articles || 0) - (statistics?.biased_count || 0)}
            </div>
            <div className="text-sm text-gray-400">Unbiased Articles</div>
          </div>

          <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/30 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">🔄</span>
              <span className="text-sm text-purple-400 font-semibold">PROCESSED</span>
            </div>
            <div className="text-4xl font-bold text-white mb-1">{statistics?.processed_count || 0}</div>
            <div className="text-sm text-gray-400">AI Analyzed</div>
          </div>
        </div>

        {/* Scheduler Status */}
        <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
              <span>⏰</span>
              <span>Scheduler Status</span>
            </h2>
            <div
              className={`px-4 py-2 rounded-full text-sm font-semibold ${
                schedulerStatus?.running
                  ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                  : 'bg-red-500/10 text-red-400 border border-red-500/30'
              }`}
            >
              {schedulerStatus?.running ? '🟢 Running' : '🔴 Stopped'}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-sm text-gray-400 mb-1">Next Scheduled Run</div>
              <div className="text-xl font-semibold text-white">
                {schedulerStatus?.next_run
                  ? new Date(schedulerStatus.next_run).toLocaleString('en-US', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })
                  : 'Not Scheduled'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {schedulerStatus?.next_run &&
                  `(${Math.round((new Date(schedulerStatus.next_run).getTime() - Date.now()) / 3600000)} hours from now)`}
              </div>
            </div>

            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-sm text-gray-400 mb-1">Schedule Configuration</div>
              <div className="text-xl font-semibold text-white">Daily at 6:00 AM BDT</div>
              <div className="text-xs text-gray-500 mt-1">Automatic scraping enabled</div>
            </div>
          </div>

          {/* Last Run Information */}
          {schedulerStatus?.last_run && (
            <div className="mt-6 bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              <div className="text-sm text-gray-400 mb-3 font-semibold">Last Scraping Run</div>
              <div className="grid md:grid-cols-4 gap-4">
                <div>
                  <div className="text-xs text-gray-500 mb-1">Status</div>
                  <div className={`text-sm font-semibold ${
                    schedulerStatus.last_run.status === 'success' ? 'text-green-400' :
                    schedulerStatus.last_run.status === 'failed' ? 'text-red-400' :
                    'text-yellow-400'
                  }`}>
                    {schedulerStatus.last_run.status === 'success' ? '✅ Success' :
                     schedulerStatus.last_run.status === 'failed' ? '❌ Failed' :
                     '⚠️ Partial'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Started At</div>
                  <div className="text-sm text-white">
                    {schedulerStatus.last_run.started_at
                      ? new Date(schedulerStatus.last_run.started_at).toLocaleString('en-US', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })
                      : 'N/A'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Articles Scraped</div>
                  <div className="text-sm font-semibold text-blue-400">
                    {schedulerStatus.last_run.articles_scraped || 0}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Duration</div>
                  <div className="text-sm text-white">
                    {schedulerStatus.last_run.completed_at && schedulerStatus.last_run.started_at
                      ? `${Math.round(
                          (new Date(schedulerStatus.last_run.completed_at).getTime() -
                           new Date(schedulerStatus.last_run.started_at).getTime()) / 1000
                        )}s`
                      : 'N/A'}
                  </div>
                </div>
              </div>
              {schedulerStatus.last_run.errors && schedulerStatus.last_run.errors.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <div className="text-xs text-red-400 mb-1">Errors:</div>
                  <div className="text-xs text-gray-400 space-y-1">
                    {schedulerStatus.last_run.errors.slice(0, 3).map((err: string, idx: number) => (
                      <div key={idx}>• {err}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Source Distribution */}
        {statistics && statistics.by_source && (
          <div className="bg-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-800 p-6">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center space-x-2">
              <span>📊</span>
              <span>Articles by Source</span>
            </h2>
            <div className="space-y-4">
              {Object.entries(statistics.by_source).map(([source, count]) => {
                const percentage = ((count / statistics.total_articles) * 100).toFixed(1);
                return (
                  <div key={source} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white font-semibold capitalize">
                        {source.replace('_', ' ')}
                      </span>
                      <span className="text-gray-400">{count} articles ({percentage}%)</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-primary-500 to-emerald-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Last Updated */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
