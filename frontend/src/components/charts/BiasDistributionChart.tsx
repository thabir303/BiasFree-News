import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { BarChart3 } from 'lucide-react';
import type { BiasDistributionBucket } from '../../services/api';
import { CHART_TOOLTIP_STYLE } from './chartConstants';

interface Props {
  data: BiasDistributionBucket[];
}

const BiasDistributionChart = ({ data }: Props) => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
    <div className="flex items-center gap-2 mb-1">
      <BarChart3 className="w-4 h-4 text-violet-400" />
      <h4 className="text-sm font-semibold text-white">Bias Score Distribution</h4>
    </div>
    <p className="text-[11px] text-gray-500 mb-5">Histogram of bias scores across processed articles</p>
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="range" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={index} fill={index < 4 ? '#10b981' : index < 7 ? '#f59e0b' : '#ef4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export default BiasDistributionChart;
