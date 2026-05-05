import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { Layers } from 'lucide-react';
import type { SourceComparison } from '../../services/api';
import { SOURCE_LABELS } from '../../constants/sources';
import { CHART_TOOLTIP_STYLE } from './chartConstants';

interface Props {
  data: SourceComparison[];
}

const SourceBreakdownBarChart = ({ data }: Props) => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
    <div className="flex items-center gap-2 mb-1">
      <Layers className="w-4 h-4 text-sky-400" />
      <h4 className="text-sm font-semibold text-white">Articles by Source</h4>
    </div>
    <p className="text-[11px] text-gray-500 mb-5">Total, processed, and biased articles per source</p>
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data.map(s => ({
          source: SOURCE_LABELS[s.source] || s.source,
          Total: s.total,
          Processed: s.processed_count,
          Biased: s.biased_count,
        }))}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="source" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
          <Bar dataKey="Total" fill="#60a5fa" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Processed" fill="#10b981" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Biased" fill="#ef4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export default SourceBreakdownBarChart;
