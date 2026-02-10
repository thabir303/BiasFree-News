import { Funnel } from 'lucide-react';

export interface FilterState {
  source: string;
  is_biased: string;
  skip: number;
  limit: number;
}

interface ArticleFiltersProps {
  filters: FilterState;
  onFilterChange: (key: string, value: any) => void;
  onClearAll: () => void;
  loading?: boolean;
}

const SOURCE_OPTIONS = [
  { value: '', label: 'All Sources' },
  { value: 'prothom_alo', label: 'প্রথম আলো' },
  { value: 'daily_star', label: 'Daily Star' },
  { value: 'jugantor', label: 'যুগান্তর' },
  { value: 'samakal', label: 'সমকাল' },
];

const BIAS_OPTIONS = [
  { value: '', label: 'All Articles' },
  { value: 'true', label: 'Biased Only' },
  { value: 'false', label: 'Unbiased Only' },
];

const LIMIT_OPTIONS = [
  { value: 12, label: '12' },
  { value: 24, label: '24' },
  { value: 48, label: '48' },
];

const ArticleFilters: React.FC<ArticleFiltersProps> = ({
  filters,
  onFilterChange,
  onClearAll,
  loading = false,
}) => {
  const activeFiltersCount = [filters.source, filters.is_biased].filter(Boolean).length;

  return (
    <div className="rounded-2xl border border-gray-800/60 bg-gray-900/30 backdrop-blur-sm p-5 sm:p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Funnel />
          Filters
          {activeFiltersCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-primary-500/20 text-primary-400">
              {activeFiltersCount}
            </span>
          )}
        </h3>
        {activeFiltersCount > 0 && (
          <button
            onClick={onClearAll}
            disabled={loading}
            className="text-xs text-gray-500 hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Source Filter */}
        <div>
          <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">
            Source
          </label>
          <select
            value={filters.source}
            onChange={(e) => onFilterChange('source', e.target.value)}
            disabled={loading}
            className="w-full bg-gray-800/60 border border-gray-700/50 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all appearance-none cursor-pointer"
          >
            {SOURCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Bias Status Filter */}
        <div>
          <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">
            Bias Status
          </label>
          <select
            value={filters.is_biased}
            onChange={(e) => onFilterChange('is_biased', e.target.value)}
            disabled={loading}
            className="w-full bg-gray-800/60 border border-gray-700/50 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all appearance-none cursor-pointer"
          >
            {BIAS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Per Page Filter */}
        <div>
          <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">
            Per Page
          </label>
          <select
            value={filters.limit}
            onChange={(e) => onFilterChange('limit', parseInt(e.target.value))}
            disabled={loading}
            className="w-full bg-gray-800/60 border border-gray-700/50 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all appearance-none cursor-pointer"
          >
            {LIMIT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

export default ArticleFilters;