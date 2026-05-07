interface EmptyStateProps {
  onPick: (q: string) => void;
}

const STARTERS = [
  'What is the breakdown of the sales between Website and App in the last month?',
  'What is our ancillary revenue per ancillary passenger on direct bookings',
  'What is our direct sales value this month',
  'How many business class tickets were sold from 1st April to 30 April 2026 for London to Riyadh route',
  'What is our direct sales value this month, and how does it compare to last month and the same period last year?',
  'What percentage of our bookings are coming through direct and indirect channels',
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
      <div className="flex flex-col gap-2">
        {STARTERS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="text-left text-sm rounded-lg border border-rx-purple/30 px-3 py-2 text-rx-purple hover:bg-rx-purple/10 transition"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
