import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Legend, Tooltip, ResponsiveContainer,
} from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';
import type { SourceComparison } from '../../services/api';
import { SOURCE_LABELS } from '../../constants/sources';
import { CHART_TOOLTIP_STYLE } from './chartConstants';

interface Props {
  data: SourceComparison[];
}

const SourceBiasRadarChart = ({ data }: Props) => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
    <div className="flex items-center gap-2 mb-1">
      <PieChartIcon className="w-4 h-4 text-amber-400" />
      <h4 className="text-sm font-semibold text-white">Source Bias Comparison</h4>
    </div>
    <p className="text-[11px] text-gray-500 mb-5">Average bias score &amp; bias rate per source</p>
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data.map(s => ({
          source: SOURCE_LABELS[s.source] || s.source,
          'Avg Bias': s.avg_bias,
          'Bias Rate (%)': s.bias_rate,
        }))}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="source" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <PolarRadiusAxis tick={{ fill: '#64748b', fontSize: 9 }} />
          <Radar name="Avg Bias" dataKey="Avg Bias" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
          <Radar name="Bias Rate (%)" dataKey="Bias Rate (%)" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} />
          <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export default SourceBiasRadarChart;
