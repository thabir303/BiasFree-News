import { Layers } from 'lucide-react';
import type { CategoryBreakdown } from '../../services/api';
import { VIZ_COLORS } from './chartConstants';

interface Props {
  data: CategoryBreakdown[];
}

const CategoryBreakdownChart = ({ data }: Props) => {
  if (data.length === 0) return null;

  return (
    <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
      <div className="flex items-center gap-2 mb-1">
        <Layers className="w-4 h-4 text-rose-400" />
        <h4 className="text-sm font-semibold text-white">Category Breakdown</h4>
      </div>
      <p className="text-[11px] text-gray-500 mb-5">Articles, bias rate, and average bias score per category</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {data.map((cat, i) => (
          <div key={cat.category} className="rounded-xl border border-gray-800/50 bg-gray-800/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: VIZ_COLORS[i % VIZ_COLORS.length] }} />
              <h5 className="text-sm font-semibold text-white truncate">{cat.category}</h5>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-xs text-gray-500">Total</span>
                <span className="text-xs font-bold text-white">{cat.total.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-gray-500">Biased</span>
                <span className="text-xs font-bold text-red-400">{cat.biased.toLocaleString()} ({cat.bias_rate}%)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-gray-500">Avg Bias</span>
                <span className="text-xs font-bold text-amber-400">{cat.avg_bias.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-gray-500">Processed</span>
                <span className="text-xs font-bold text-emerald-400">{cat.processed.toLocaleString()}</span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-700/60 overflow-hidden mt-1">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-red-500 to-amber-500 transition-all"
                  style={{ width: `${Math.min(cat.bias_rate, 100)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CategoryBreakdownChart;
