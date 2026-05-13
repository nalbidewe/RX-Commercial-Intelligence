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
  "Provide a report of all the metrics where I am not meeting the targets in April'26",
  'Are our direct and indirect channels revenue converting as they should? Compared to Target',
  'Which days of the week do we have the most revenue?',
  'What are the top indirect distributors last week?',
  'What is the Guest Satisfaction Score for the past month?',
  'How many surveys do we receive from Jamila and what is the percentage of the sentiment?',
];
