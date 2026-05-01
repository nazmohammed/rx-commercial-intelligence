import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { motion } from 'framer-motion';
import type { DerivedChart } from '../lib/deriveChart';

interface ChartPanelProps {
  chart: DerivedChart;
}

const PURPLE = '#5B2C8B';

function formatNumber(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(2);
}

/**
 * Generic bar chart driven by deriveChart() output. Label on X, value on Y.
 * Used for any /api/chat response that has chartable structured data.
 */
export default function ChartPanel({ chart }: ChartPanelProps) {
  const data = chart.points.map((p) => ({ label: p.label, value: p.value }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="bg-white rounded-xl shadow-card border border-rx-purple/10 p-4"
    >
      <div className="flex items-baseline justify-between mb-3">
        <div>
          <div className="text-rx-ink font-semibold">
            {chart.valueName} by {chart.labelName}
          </div>
          <div className="text-xs text-rx-subtle">
            {chart.points.length} {chart.points.length === 1 ? 'row' : 'rows'}
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EDE6D8" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: '#6B6B6B' }}
              axisLine={false}
              tickLine={false}
              interval={0}
              angle={data.length > 8 ? -25 : 0}
              textAnchor={data.length > 8 ? 'end' : 'middle'}
              height={data.length > 8 ? 60 : 30}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#6B6B6B' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => formatNumber(v)}
            />
            <Tooltip
              contentStyle={{
                background: '#fff',
                border: '1px solid #E6DFD0',
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(v) => [formatNumber(Number(v)), chart.valueName]}
            />
            <Bar dataKey="value" fill={PURPLE} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
