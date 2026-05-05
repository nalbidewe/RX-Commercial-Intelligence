import { useEffect, useRef, useState } from 'react';
import * as AC from 'adaptivecards';
import ChartPanel from './ChartPanel';
import type { DerivedChart } from '../lib/deriveChart';

interface OutputCardProps {
  card: Record<string, unknown>;
  dax: string;
  summary: string;
  chart?: DerivedChart | null;
}

/**
 * Renders an Adaptive Card returned by /api/chat using the official
 * `adaptivecards` lib. Chart (if any) is rendered below the card content.
 */
export default function OutputCard({ card, dax, summary, chart }: OutputCardProps) {
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

  return (
    <div className="bg-white rounded-xl shadow-card border border-rx-purple/10 overflow-hidden">
      {/* Adaptive Card content */}
      <div ref={hostRef} className="p-4 [&_.ac-container]:!bg-transparent" />

      {/* Chart rendered after the summary text */}
      {chart && (
        <div className="px-4 pb-4">
          <ChartPanel chart={chart} />
        </div>
      )}

      {/* Copy buttons */}
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
