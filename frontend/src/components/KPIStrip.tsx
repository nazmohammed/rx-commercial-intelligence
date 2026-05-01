import { motion } from 'framer-motion';
import type { KpiTile } from '../sampleCard';

interface KPIStripProps {
  kpis: KpiTile[];
}

const TONE_CLASSES: Record<NonNullable<KpiTile['tone']>, string> = {
  good: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  warn: 'text-amber-700 bg-amber-50 border-amber-200',
  neutral: 'text-rx-subtle bg-rx-cream/60 border-rx-purple/10',
};

export default function KPIStrip({ kpis }: KPIStripProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {kpis.map((k, i) => (
        <motion.div
          key={k.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06, duration: 0.3 }}
          className="bg-white rounded-xl shadow-card border border-rx-purple/10 px-4 py-3"
        >
          <div className="text-[11px] uppercase tracking-wide text-rx-subtle font-semibold">
            {k.label}
          </div>
          <div className="text-2xl font-bold text-rx-ink mt-1 leading-none">
            {k.value}
          </div>
          {k.delta && (
            <div
              className={`mt-2 inline-block text-[11px] font-medium px-2 py-0.5 rounded-full border ${
                TONE_CLASSES[k.tone ?? 'neutral']
              }`}
            >
              {k.delta}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
