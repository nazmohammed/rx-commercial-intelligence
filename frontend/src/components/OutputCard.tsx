import { useEffect, useRef, useState } from 'react';
import * as AC from 'adaptivecards';

interface OutputCardProps {
  question: string;
  card: Record<string, unknown>;
  dax: string;
  summary: string;
  timestamp: number;
}

/**
 * Renders an Adaptive Card returned by /api/chat using the official
 * `adaptivecards` lib. Wraps it in an RX-themed shell with copy buttons.
 */
export default function OutputCard({
  question,
  card,
  dax,
  summary,
  timestamp,
}: OutputCardProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [copyStatus, setCopyStatus] = useState<'' | 'dax' | 'summary'>('');

  useEffect(() => {
    if (!hostRef.current) return;
    hostRef.current.innerHTML = '';

    const adaptive = new AC.AdaptiveCard();
    adaptive.hostConfig = new AC.HostConfig({
      fontFamily: 'Segoe UI, system-ui, sans-serif',
      containerStyles: {
        default: {
          backgroundColor: '#ffffff',
          foregroundColors: {
            default: { default: '#1A1A1A', subtle: '#6B6B6B' },
            accent: { default: '#5B2C8B', subtle: '#8A5DB8' },
            warning: { default: '#B45309', subtle: '#92400E' },
            attention: { default: '#B91C1C', subtle: '#7F1D1D' },
            good: { default: '#15803D', subtle: '#166534' },
          },
        },
      },
    });

    try {
      adaptive.parse(card as object);
      const rendered = adaptive.render();
      if (rendered) hostRef.current.appendChild(rendered);
    } catch (err) {
      const div = document.createElement('div');
      div.textContent = `Failed to render Adaptive Card: ${(err as Error).message}`;
      div.className = 'text-red-700 text-sm';
      hostRef.current.appendChild(div);
    }
  }, [card]);

  async function copy(text: string, kind: 'dax' | 'summary') {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus(kind);
      setTimeout(() => setCopyStatus(''), 1500);
    } catch {
      /* clipboard blocked — ignore */
    }
  }

  const time = new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="bg-white rounded-xl shadow-card border border-rx-purple/10 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 bg-rx-purple/5 border-b border-rx-purple/10">
        <span className="text-xs font-medium text-rx-purple">Q</span>
        <span className="text-sm text-rx-ink flex-1 truncate" title={question}>
          {question}
        </span>
        <span className="text-xs text-rx-subtle">{time}</span>
      </div>

      <div ref={hostRef} className="p-4 [&_.ac-container]:!bg-transparent" />

      <div className="flex flex-wrap gap-2 px-4 py-2 bg-rx-cream/40 border-t border-rx-purple/10">
        {dax && (
          <button
            onClick={() => copy(dax, 'dax')}
            className="text-xs rounded-md border border-rx-purple/30 px-2 py-1 text-rx-purple hover:bg-rx-purple/10"
          >
            {copyStatus === 'dax' ? 'Copied!' : 'Copy DAX'}
          </button>
        )}
        {summary && (
          <button
            onClick={() => copy(summary, 'summary')}
            className="text-xs rounded-md border border-rx-purple/30 px-2 py-1 text-rx-purple hover:bg-rx-purple/10"
          >
            {copyStatus === 'summary' ? 'Copied!' : 'Copy summary'}
          </button>
        )}
      </div>
    </div>
  );
}
