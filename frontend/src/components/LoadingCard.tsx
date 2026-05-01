import { useEffect, useState } from 'react';

const STEPS = [
  'Understanding question',
  'Generating DAX',
  'Querying Power BI',
  'Interpreting results',
];

/**
 * 4-step progress card shown while the agent pipeline is running.
 *
 * The UI doesn't get real-time progress events from the backend yet, so we
 * advance steps on a fixed cadence to give the user *something* to watch.
 * The final step holds until the response actually arrives.
 */
export default function LoadingCard() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setActive((s) => (s < STEPS.length - 1 ? s + 1 : s));
    }, 1200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-card border border-rx-purple/10 p-4">
      <div className="text-rx-purple font-semibold mb-3">Working on it…</div>
      <ol className="space-y-2">
        {STEPS.map((label, i) => {
          const done = i < active;
          const current = i === active;
          return (
            <li key={label} className="flex items-center gap-2 text-sm">
              <span
                className={[
                  'inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-semibold',
                  done
                    ? 'bg-rx-purple text-rx-cream'
                    : current
                      ? 'bg-rx-purple/20 text-rx-purple animate-pulse'
                      : 'bg-rx-purple/10 text-rx-subtle',
                ].join(' ')}
              >
                {done ? '✓' : i + 1}
              </span>
              <span
                className={
                  done
                    ? 'text-rx-ink'
                    : current
                      ? 'text-rx-ink font-medium'
                      : 'text-rx-subtle'
                }
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
