interface EmptyStateProps {
  onPick: (q: string) => void;
}

const STARTERS = [
  'What was load factor on RUH–DXB last week?',
  'Top 5 routes by revenue in the last 30 days',
  'Yield trend for RUH–LHR over the last quarter',
  'Which routes underperformed budget last month?',
];

/**
 * First-run hero. Replaces the old sample card with a real empty state —
 * no fabricated numbers shown to the user.
 */
export default function EmptyState({ onPick }: EmptyStateProps) {
  return (
    <div className="bg-white rounded-2xl shadow-card border border-rx-purple/10 p-8">
      <div className="text-rx-purple text-3xl font-bold tracking-tight mb-2">
        Hi 👋
      </div>
      <div className="text-rx-ink text-base mb-1">
        Ask about routes, revenue, load factor, yield — anything in the
        Routes Insights model.
      </div>
      <div className="text-rx-subtle text-sm mb-6">
        Answers stream live from Power BI under your own RLS permissions.
      </div>

      <div className="text-[11px] uppercase tracking-wide text-rx-subtle font-semibold mb-2">
        Try one of these
      </div>
      <div className="flex flex-wrap gap-2">
        {STARTERS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="text-sm rounded-full border border-rx-purple/30 px-3 py-1.5 text-rx-purple hover:bg-rx-purple/10 transition"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
