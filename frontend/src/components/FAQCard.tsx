interface FAQCardProps {
  question: string;
  onPick: (question: string) => void;
}

/**
 * Suggested-question chip. Clicking populates the input (does NOT auto-send).
 */
export default function FAQCard({ question, onPick }: FAQCardProps) {
  return (
    <button
      type="button"
      onClick={() => onPick(question)}
      className="text-left bg-white rounded-lg shadow-card border border-rx-purple/10 px-3 py-2 hover:border-rx-purple/40 hover:shadow-md transition w-full"
    >
      <div className="text-xs uppercase tracking-wide text-rx-purple font-semibold mb-1">
        Suggested
      </div>
      <div className="text-sm text-rx-ink">{question}</div>
    </button>
  );
}

export const DEFAULT_FAQS: string[] = [
  'What was load factor on RUH–DXB last week?',
  'Top 5 routes by revenue in the last 30 days',
  'Yield trend for RUH–LHR over the last quarter',
  'Which routes underperformed budget last month?',
];
