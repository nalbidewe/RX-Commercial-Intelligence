interface EmptyStateProps {
  onPick: (q: string) => void;
}

const STARTERS = [
  "Provide a report of all the metrics where I am not meeting the targets in April'26",
  'Are our direct and indirect channels revenue converting as they should? Compared to Target',
  'Which days of the week do we have the most revenue?',
  'What are the top indirect distributors last week?',
  'What is the Guest Satisfaction Score for the past month?',
  'How many surveys do we receive from Jamila and what is the percentage of the sentiment?',
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
        Ask about commercial performance or guest experience — revenue, load factor,
        yield, CSAT, guest satisfaction, sentiment, and more.
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
