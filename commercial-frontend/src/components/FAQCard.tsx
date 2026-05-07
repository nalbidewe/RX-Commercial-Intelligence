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
  'What is the breakdown of the sales between Website and App in the last month?',
  'What is our ancillary revenue per ancillary passenger on direct bookings',
  'What is our direct sales value this month',
  'How many business class tickets were sold from 1st April to 30 April 2026 for London to Riyadh route',
  'What is our direct sales value this month, and how does it compare to last month and the same period last year?',
  'What percentage of our bookings are coming through direct and indirect channels',
];
