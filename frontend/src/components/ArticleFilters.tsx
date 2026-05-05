import { useState, useRef, useEffect } from 'react';
import { Funnel, CalendarDays, X, ChevronDown, Check, Search } from 'lucide-react';
import DateRangePicker from './DateRangePicker';

export interface FilterState {
  source: string;
  is_biased: string;
  date_from: string;
  date_to: string;
  search: string;
  sort_by: string;
  skip: number;
  limit: number;
}

interface ArticleFiltersProps {
  filters: FilterState;
  onFilterChange: (key: string, value: any) => void;
  onClearAll: () => void;
  loading?: boolean;
}

const today = new Date().toISOString().split('T')[0];

const SOURCE_OPTIONS = [
  { value: '', label: 'All Sources', logo: null },
  { value: 'prothom_alo', label: 'প্রথম আলো', logo: '/prothomalo.png' },
  { value: 'daily_star', label: 'ডেইলি স্টার', logo: '/dailystar.png' },
  { value: 'jugantor', label: 'যুগান্তর', logo: '/jugantor.png' },
  { value: 'samakal', label: 'সমকাল', logo: '/samakal.png' },
  { value: 'naya_diganta', label: 'নয়া দিগন্ত', logo: '/nayadiganta.png' },
  { value: 'ittefaq', label: 'ইত্তেফাক', logo: '/ittefaq.png' },
];

const BIAS_OPTIONS = [
  { value: '', label: 'All Articles', badge: null },
  {
    value: 'true',
    label: 'Biased Only',
    badge: { text: 'Biased', bg: 'bg-red-500/15', textColor: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-400' },
  },
  {
    value: 'false',
    label: 'Unbiased Only',
    badge: { text: 'Neutral', bg: 'bg-emerald-500/15', textColor: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  },
];

const LIMIT_OPTIONS = [
  { value: 12, label: '12' },
  { value: 24, label: '24' },
  { value: 48, label: '48' },
];

/* ─── Custom Dropdown ────────────────────────────────── */
interface DropdownOption {
  value: string;
  label: string;
  logo?: string | null;
  badge?: { text: string; bg: string; textColor: string; border: string; dot: string } | null;
}

interface CustomDropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  dropdownId?: string;
  openDropdown?: string | null;
  setOpenDropdown?: (id: string | null) => void;
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({ options, value, onChange, disabled = false, dropdownId, openDropdown, setOpenDropdown }) => {
  const open = dropdownId ? openDropdown === dropdownId : false;
  const [localOpen, setLocalOpen] = useState(false);
  const isOpen = dropdownId ? open : localOpen;
  const ref = useRef<HTMLDivElement>(null);

  const setOpen = (v: boolean) => {
    if (dropdownId && setOpenDropdown) {
      setOpenDropdown(v ? dropdownId : null);
    } else {
      setLocalOpen(v);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const selected = options.find((o) => o.value === value) ?? options[0];

  const renderLabel = (option: DropdownOption, small = false) => {
    if (option.logo) {
      return (
        <span className="flex items-center gap-2">
          <img src={option.logo} alt={option.label} className={`${small ? 'w-7 h-7' : 'w-8 h-8'} rounded-md object-contain shrink-0 bg-white p-0.2`} />
          <span className="text-white">{option.label}</span>
        </span>
      );
    }
    if (option.badge) {
      return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${option.badge.bg} ${option.badge.border} ${option.badge.textColor}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${option.badge.dot}`} />
          {option.badge.text}
        </span>
      );
    }
    return <span className="text-gray-400">{option.label}</span>;
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen(!isOpen)}
        className={`
          w-full flex items-center justify-between gap-2
          bg-gray-800/60 border rounded-xl px-3.5 py-2.5 text-sm font-medium
          transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
          ${isOpen
            ? 'border-primary-500/60 ring-2 ring-primary-500/20 bg-gray-800/90'
            : 'border-gray-700/50 hover:border-gray-600 hover:bg-gray-800/80'
          }
        `}
      >
        <span className="flex items-center gap-2 min-w-0 truncate">
          {renderLabel(selected, true)}
        </span>
        <ChevronDown
          size={14}
          className={`shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180 text-primary-400' : 'text-gray-500'}`}
        />
      </button>

      {isOpen && (
        <div className="absolute z-[999] top-[calc(100%+6px)] left-0 right-0 rounded-xl border border-gray-700/70 bg-gray-900/95 backdrop-blur-sm shadow-2xl shadow-black/60 overflow-hidden">
          <div className="py-1.5 max-h-60 overflow-y-auto">
            {options.map((option) => {
              const isSelected = option.value === value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => { onChange(option.value); setOpen(false); }}
                  className={`
                    w-full flex items-center justify-between gap-2 px-3.5 py-2 text-sm transition-colors
                    ${isSelected ? 'bg-primary-500/10 text-primary-300' : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'}
                  `}
                >
                  {renderLabel(option)}
                  {isSelected && <Check size={13} className="text-primary-400 shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

/* ─── Main Filter Component ──────────────────────────── */
const ArticleFilters: React.FC<ArticleFiltersProps> = ({
  filters,
  onFilterChange,
  onClearAll,
  loading = false,
}) => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const activeFiltersCount = [
    filters.source,
    filters.is_biased,
    filters.date_from,
    filters.date_to,
    filters.search,
  ].filter(Boolean).length;

  return (
    <div className="relative z-[100] rounded-2xl border border-gray-800/60 bg-gray-900/30 backdrop-blur-sm p-5 sm:p-6 mb-6">
      {/* Search Bar */}
      <div className="mb-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={filters.search || ''}
            onChange={(e) => onFilterChange('search', e.target.value)}
            placeholder="Search by title or content..."
            disabled={loading}
            className="w-full pl-10 pr-4 py-2.5 bg-gray-800/60 border border-gray-700/50 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500/50 disabled:opacity-50 transition-all"
          />
          {filters.search && (
            <button onClick={() => onFilterChange('search', '')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Funnel size={15} />
          Filters
          {activeFiltersCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-primary-500/20 text-primary-400 tabular-nums">
              {activeFiltersCount}
            </span>
          )}
        </h3>
        {activeFiltersCount > 0 && (
          <button
            onClick={onClearAll}
            disabled={loading}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <X size={12} />
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Source Filter */}
        <div className={`relative ${openDropdown === 'source' ? 'z-100' : 'z-0'}`}>
          <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">
            Source
          </label>
          <CustomDropdown
            options={SOURCE_OPTIONS}
            value={filters.source}
            onChange={(v) => onFilterChange('source', v)}
            disabled={loading}
            dropdownId="source"
            openDropdown={openDropdown}
            setOpenDropdown={setOpenDropdown}
          />
        </div>

        {/* Bias Status Filter */}
        <div className={`relative ${openDropdown === 'bias' ? 'z-100' : 'z-0'}`}>
          <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">
            Bias Status
          </label>
          <CustomDropdown
            options={BIAS_OPTIONS}
            value={filters.is_biased}
            onChange={(v) => onFilterChange('is_biased', v)}
            disabled={loading}
            dropdownId="bias"
            openDropdown={openDropdown}
            setOpenDropdown={setOpenDropdown}
          />
        </div>

        {/* Date Range */}
        <div className="sm:col-span-2">
          <label className="flex items-center gap-1 text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">
            <CalendarDays size={11} />
            Date Range
          </label>
          <DateRangePicker
            fromDate={filters.date_from}
            toDate={filters.date_to}
            onFromChange={(v) => onFilterChange('date_from', v)}
            onToChange={(v) => onFilterChange('date_to', v)}
            disabled={loading}
            maxDate={today}
          />
        </div>
      </div>

      {/* Per Page + Sort — second row */}
      <div className="mt-3 flex items-center gap-3 flex-wrap">
        <label className="text-[11px] font-medium text-gray-500 uppercase tracking-wider shrink-0">
          Per Page
        </label>
        <div className="flex gap-1.5">
          {LIMIT_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => onFilterChange('limit', option.value)}
              disabled={loading}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                filters.limit === option.value
                  ? 'bg-primary-500/20 border border-primary-500/40 text-primary-400'
                  : 'bg-gray-800/60 border border-gray-700/50 text-gray-400 hover:border-gray-600'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        {/* Sort Options */}
        <div className="flex items-center gap-1.5 ml-4">
          <label className="text-[11px] font-medium text-gray-500 uppercase tracking-wider shrink-0">Sort</label>
          {[
            { value: '', label: 'Newest' },
            { value: 'oldest', label: 'Oldest' },
            { value: 'bias_high', label: 'Bias ↓' },
            { value: 'bias_low', label: 'Bias ↑' },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => onFilterChange('sort_by', opt.value)}
              disabled={loading}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all disabled:opacity-50 ${
                (filters.sort_by || '') === opt.value
                  ? 'bg-primary-500/20 border border-primary-500/40 text-primary-400'
                  : 'bg-gray-800/60 border border-gray-700/50 text-gray-400 hover:border-gray-600'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {(filters.date_from || filters.date_to) && (
          <div className="ml-auto flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary-500/10 border border-primary-500/20">
            <CalendarDays size={12} className="text-primary-400" />
            <span className="text-xs text-primary-400">
              {filters.date_from || '...'} → {filters.date_to || today}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ArticleFilters;
