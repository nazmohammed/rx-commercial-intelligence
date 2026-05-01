import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { motion } from 'framer-motion';
import type { SampleRow } from '../sampleCard';

interface ChartPanelProps {
  rows: SampleRow[];
}

const PURPLE = '#5B2C8B';
const PURPLE_LIGHT = '#8A5DB8';
const AMBER = '#D97706';

/**
 * Composed chart: revenue bars (left axis, SAR M) + load factor line
 * (right axis, %). Bars below 75% LF are highlighted amber.
 */
export default function ChartPanel({ rows }: ChartPanelProps) {
  const data = rows.map((r) => ({
    route: r.route,
    revenue: r.revenue,
    loadFactor: Math.round(r.loadFactor * 100),
    yieldPerRpk: r.yieldPerRpk,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-white rounded-xl shadow-card border border-rx-purple/10 p-4"
    >
      <div className="flex items-baseline justify-between mb-3">
        <div>
          <div className="text-rx-ink font-semibold">Revenue & load factor by route</div>
          <div className="text-xs text-rx-subtle">Last 30 days</div>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-rx-subtle">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: PURPLE }} /> Revenue (SAR M)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: AMBER }} /> Load factor (%)
          </span>
        </div>
      </div>

      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EDE6D8" />
            <XAxis dataKey="route" tick={{ fontSize: 12, fill: '#6B6B6B' }} axisLine={false} tickLine={false} />
            <YAxis
              yAxisId="rev"
              orientation="left"
              tick={{ fontSize: 11, fill: '#6B6B6B' }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'SAR M', angle: -90, position: 'insideLeft', offset: 16, style: { fontSize: 11, fill: '#6B6B6B' } }}
            />
            <YAxis
              yAxisId="lf"
              orientation="right"
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: '#6B6B6B' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                background: '#fff',
                border: '1px solid #E6DFD0',
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value: number, name: string) => {
                if (name === 'Revenue') return [`SAR ${value.toFixed(1)}M`, name];
                if (name === 'Load factor') return [`${value}%`, name];
                return [value, name];
              }}
            />
            <Legend wrapperStyle={{ display: 'none' }} />
            <Bar yAxisId="rev" dataKey="revenue" name="Revenue" radius={[6, 6, 0, 0]}>
              {data.map((d) => (
                <Cell key={d.route} fill={d.loadFactor < 75 ? AMBER : PURPLE} />
              ))}
            </Bar>
            <Line
              yAxisId="lf"
              type="monotone"
              dataKey="loadFactor"
              name="Load factor"
              stroke={PURPLE_LIGHT}
              strokeWidth={2.5}
              dot={{ r: 4, fill: PURPLE_LIGHT, strokeWidth: 0 }}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
