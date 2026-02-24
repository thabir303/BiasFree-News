import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Line, ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import type { TimeSeriesPoint } from '../../services/api';
import { CHART_TOOLTIP_STYLE } from './chartConstants';

interface Props {
  data: TimeSeriesPoint[];
}

const TimeTrendChart = ({ data }: Props) => (
  <div className="rounded-2xl border border-gray-800/60 bg-gray-900/40 backdrop-blur-sm p-6">
    <div className="flex items-center gap-2 mb-1">
      <TrendingUp className="w-4 h-4 text-emerald-400" />
      <h4 className="text-sm font-semibold text-white">Trends Over Time</h4>
    </div>
    <p className="text-[11px] text-gray-500 mb-5">Articles scraped per day &amp; bias rate over time</p>
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="vizTotalGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="vizBiasedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis yAxisId="left" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8', fontSize: 10 }} domain={[0, 100]} unit="%" />
          <Tooltip
            contentStyle={CHART_TOOLTIP_STYLE}
            labelFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          />
          <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
          <Area yAxisId="left" type="monotone" dataKey="total" name="Total Articles" stroke="#60a5fa" fill="url(#vizTotalGrad)" strokeWidth={2} />
          <Area yAxisId="left" type="monotone" dataKey="biased" name="Biased Articles" stroke="#ef4444" fill="url(#vizBiasedGrad)" strokeWidth={2} />
          <Line yAxisId="right" type="monotone" dataKey="bias_rate" name="Bias Rate (%)" stroke="#f59e0b" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export default TimeTrendChart;
