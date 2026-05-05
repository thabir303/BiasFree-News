import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react';

interface DateRangePickerProps {
  fromDate: string;
  toDate: string;
  onFromChange: (v: string) => void;
  onToChange: (v: string) => void;
  disabled?: boolean;
  maxDate?: string;
  className?: string;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const DAY_LABELS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

function toIso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function fromIso(s: string): Date {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d, 12);
}
function displayDate(s: string): string {
  if (!s) return '';
  const d = fromIso(s);
  return `${d.getDate()} ${MONTH_NAMES[d.getMonth()].slice(0, 3)} ${d.getFullYear()}`;
}
function daysInMonth(y: number, m: number) { return new Date(y, m + 1, 0).getDate(); }
function firstDayOfMonth(y: number, m: number) { return new Date(y, m, 1).getDay(); }

const DateRangePicker: React.FC<DateRangePickerProps> = ({
  fromDate, toDate, onFromChange, onToChange,
  disabled = false, maxDate, className = '',
}) => {
  const todayStr  = maxDate || toIso(new Date());
  const todayDate = fromIso(todayStr);

  const [open, setOpen]             = useState(false);
  const [selecting, setSelecting]   = useState<'from' | 'to'>('from');
  const [hovered, setHovered]       = useState<string | null>(null);
  const [viewYear, setViewYear]     = useState(todayDate.getFullYear());
  const [viewMonth, setViewMonth]   = useState(todayDate.getMonth());
  const [popoverStyle, setPopoverStyle] = useState<React.CSSProperties>({});

  const triggerRef = useRef<HTMLDivElement>(null);

  const computePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const popoverWidth = 308;
    let left = rect.left + window.scrollX;
    const maxLeft = window.innerWidth - popoverWidth - 8;
    if (left > maxLeft) left = maxLeft;
    setPopoverStyle({
      position: 'absolute',
      top: rect.bottom + window.scrollY + 8,
      left,
      width: popoverWidth,
      zIndex: 99999,
    });
  }, []);

  const openFor = (field: 'from' | 'to') => {
    if (disabled) return;
    setSelecting(field);
    const anchor = field === 'from'
      ? (fromDate ? fromIso(fromDate) : todayDate)
      : (toDate   ? fromIso(toDate)   : todayDate);
    setViewYear(anchor.getFullYear());
    setViewMonth(anchor.getMonth());
    computePosition();
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const update = () => computePosition();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [open, computePosition]);

  useEffect(() => {
    if (!open) return;
    const handle = (e: MouseEvent) => {
      const target = e.target as Node;
      const popoverEl = document.getElementById('drp-popover');
      if (
        triggerRef.current && !triggerRef.current.contains(target) &&
        popoverEl && !popoverEl.contains(target)
      ) {
        setOpen(false);
        setHovered(null);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [open]);

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
    else setViewMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
    else setViewMonth(m => m + 1);
  };
  const canGoNext =
    viewYear < todayDate.getFullYear() ||
    (viewYear === todayDate.getFullYear() && viewMonth < todayDate.getMonth());

  const buildCells = (): (string | null)[] => {
    const cells: (string | null)[] = Array(firstDayOfMonth(viewYear, viewMonth)).fill(null);
    for (let d = 1; d <= daysInMonth(viewYear, viewMonth); d++)
      cells.push(toIso(new Date(viewYear, viewMonth, d, 12)));
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  };

  const handleDayClick = (dateStr: string) => {
    if (dateStr > todayStr) return;
    if (selecting === 'from') {
      onFromChange(dateStr);
      if (toDate && toDate < dateStr) onToChange('');
      setSelecting('to');
    } else {
      if (fromDate && dateStr < fromDate) {
        onToChange(fromDate); onFromChange(dateStr);
      } else {
        onToChange(dateStr);
      }
      setOpen(false); setHovered(null);
    }
  };

  const isDisabled   = (d: string) => d > todayStr;
  const isRangeEdge  = (d: string) => d === fromDate || d === toDate;
  const isInRange    = (d: string): boolean => {
    const lo = fromDate;
    const hi = toDate || (selecting === 'to' ? hovered : null);
    if (!lo || !hi) return false;
    const [a, b] = lo <= hi ? [lo, hi] : [hi, lo];
    return d > a && d < b;
  };
  const isRangeStart = (d: string) => d === fromDate && (!!toDate || (selecting === 'to' && !!hovered && hovered > fromDate));
  const isRangeEnd   = (d: string) => d === toDate && !!fromDate;

  const makePreset = (from: number, to = 0) => {
    const f = new Date(todayDate); f.setDate(f.getDate() - from);
    const t = new Date(todayDate); t.setDate(t.getDate() - to);
    return { from: toIso(f), to: toIso(t) };
  };
  const PRESETS = [
    { label: 'Today',      ...makePreset(0, 0) },
    { label: 'Yesterday',  ...makePreset(1, 1) },
    { label: 'Last 7d',    ...makePreset(6, 0) },
    { label: 'Last 30d',   ...makePreset(29, 0) },
    { label: 'This month', from: toIso(new Date(todayDate.getFullYear(), todayDate.getMonth(), 1)), to: todayStr },
  ];
  const hasValue = fromDate || toDate;

  const popoverJsx = (
    <div
      id="drp-popover"
      style={popoverStyle}
      className="bg-[#111318] border border-gray-700/60 rounded-2xl shadow-2xl shadow-black/70 overflow-hidden animate-popover-in"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800/80">
        <button type="button" onClick={prevMonth}
          className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors">
          <ChevronLeft size={15} />
        </button>
        <span className="text-sm font-semibold text-white tracking-wide">
          {MONTH_NAMES[viewMonth]} {viewYear}
        </span>
        <button type="button" onClick={nextMonth} disabled={!canGoNext}
          className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white disabled:opacity-25 disabled:cursor-not-allowed transition-colors">
          <ChevronRight size={15} />
        </button>
      </div>

      <div className="p-3">
        {/* Selecting pills */}
        <div className="flex items-center gap-1.5 mb-3 px-1">
          {(['from', 'to'] as const).map((side) => {
            const val = side === 'from' ? fromDate : toDate;
            return (
              <button key={side} type="button" onClick={() => setSelecting(side)}
                className={`flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full font-medium transition-all duration-150 ${
                  selecting === side
                    ? 'bg-primary-500/20 text-primary-400 ring-1 ring-primary-500/40'
                    : 'text-gray-600 hover:text-gray-400'
                }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${val ? 'bg-primary-400' : 'bg-gray-600'}`} />
                {val ? displayDate(val) : side === 'from' ? 'Pick start' : 'Pick end'}
              </button>
            );
          })}
        </div>

        {/* Day-of-week headers */}
        <div className="grid grid-cols-7 mb-1">
          {DAY_LABELS.map(d => (
            <div key={d} className="text-center text-[10px] font-semibold text-gray-600 py-1 uppercase tracking-wider">{d}</div>
          ))}
        </div>

        {/* Day cells */}
        <div className="grid grid-cols-7">
          {buildCells().map((dateStr, idx) => {
            if (!dateStr) return <div key={`e${idx}`} className="h-8" />;
            const dis        = isDisabled(dateStr);
            const edge       = isRangeEdge(dateStr);
            const inRange    = isInRange(dateStr);
            const rangeStart = isRangeStart(dateStr);
            const rangeEnd   = isRangeEnd(dateStr);
            const isToday    = dateStr === todayStr;
            return (
              <div key={dateStr}
                className={`relative h-8 flex items-center justify-center ${inRange ? 'bg-primary-500/10' : ''} ${rangeStart ? 'rounded-l-full' : ''} ${rangeEnd ? 'rounded-r-full' : ''}`}>
                <button type="button" disabled={dis}
                  onClick={() => handleDayClick(dateStr)}
                  onMouseEnter={() => !dis && setHovered(dateStr)}
                  onMouseLeave={() => setHovered(null)}
                  className={`w-7 h-7 rounded-full text-[12px] font-medium transition-all duration-100 relative ${
                    edge
                      ? 'bg-primary-500 text-white shadow-md shadow-primary-500/40 ring-2 ring-primary-500/30 z-10'
                      : inRange
                        ? 'text-primary-300 hover:bg-primary-500/20'
                        : dis
                          ? 'text-gray-700 cursor-not-allowed'
                          : 'text-gray-300 hover:bg-gray-700/70 hover:text-white'
                  }`}>
                  {fromIso(dateStr).getDate()}
                  {isToday && !edge && (
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary-500/60" />
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Presets */}
        <div className="border-t border-gray-800/80 mt-3 pt-3 flex flex-wrap gap-1.5">
          {PRESETS.map(p => (
            <button key={p.label} type="button"
              onClick={() => { onFromChange(p.from); onToChange(p.to); setOpen(false); setHovered(null); }}
              className="text-[11px] px-2.5 py-1 rounded-lg font-medium bg-gray-800/80 text-gray-400 hover:bg-primary-500/15 hover:text-primary-400 border border-gray-700/50 hover:border-primary-500/40 transition-all duration-150">
              {p.label}
            </button>
          ))}
          {hasValue && (
            <button type="button"
              onClick={() => { onFromChange(''); onToChange(''); setOpen(false); setHovered(null); }}
              className="ml-auto text-[11px] px-2.5 py-1 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/30 transition-all duration-150 flex items-center gap-1">
              <X size={10} />
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div ref={triggerRef} className={`relative ${className}`}>
      {/* Trigger buttons */}
      <div className="flex items-center gap-2">
        {/* From */}
        <button type="button" onClick={() => openFor('from')} disabled={disabled}
          className={`flex-1 flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-sm font-medium transition-all duration-150
            ${open && selecting === 'from'
              ? 'border-primary-500/70 bg-gray-800 ring-2 ring-primary-500/25 text-white'
              : fromDate
                ? 'border-gray-700/60 bg-gray-800/70 text-white hover:border-primary-500/50'
                : 'border-gray-700/50 bg-gray-800/50 text-gray-500 hover:border-gray-600 hover:text-gray-400'
            } disabled:opacity-40 disabled:cursor-not-allowed`}>
          <CalendarDays size={14} className={fromDate ? 'text-primary-400 flex-shrink-0' : 'text-gray-600 flex-shrink-0'} />
          <span className="flex-1 text-left truncate text-xs sm:text-sm">{fromDate ? displayDate(fromDate) : 'From date'}</span>
          {fromDate && (
            <span role="button" onClick={e => { e.stopPropagation(); onFromChange(''); }}
              className="flex-shrink-0 text-gray-600 hover:text-gray-300 transition-colors p-0.5 rounded">
              <X size={11} />
            </span>
          )}
        </button>

        {/* Arrow */}
        <div className="flex-shrink-0">
          <svg width="16" height="8" viewBox="0 0 16 8" className="text-gray-700">
            <path d="M1 4h12M9 1l4 3-4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          </svg>
        </div>

        {/* To */}
        <button type="button" onClick={() => openFor('to')} disabled={disabled}
          className={`flex-1 flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-sm font-medium transition-all duration-150
            ${open && selecting === 'to'
              ? 'border-primary-500/70 bg-gray-800 ring-2 ring-primary-500/25 text-white'
              : toDate
                ? 'border-gray-700/60 bg-gray-800/70 text-white hover:border-primary-500/50'
                : 'border-gray-700/50 bg-gray-800/50 text-gray-500 hover:border-gray-600 hover:text-gray-400'
            } disabled:opacity-40 disabled:cursor-not-allowed`}>
          <CalendarDays size={14} className={toDate ? 'text-primary-400 flex-shrink-0' : 'text-gray-600 flex-shrink-0'} />
          <span className="flex-1 text-left truncate text-xs sm:text-sm">{toDate ? displayDate(toDate) : 'To date'}</span>
          {toDate && (
            <span role="button" onClick={e => { e.stopPropagation(); onToChange(''); }}
              className="flex-shrink-0 text-gray-600 hover:text-gray-300 transition-colors p-0.5 rounded">
              <X size={11} />
            </span>
          )}
        </button>
      </div>

      {/* Portal popover — renders at document.body, escapes any stacking context */}
      {open && createPortal(popoverJsx, document.body)}
    </div>
  );
};

export default DateRangePicker;
