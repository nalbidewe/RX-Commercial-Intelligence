import { FormEvent, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface InputBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  suggestions?: string[];
  onSuggest?: (q: string) => void;
}

/**
 * Sticky bottom prompt bar.
 * When `suggestions` are provided they appear as a scrollable pill row
 * above the textarea — only shown after the first exchange so they don't
 * duplicate the EmptyState chips.
 */
export default function InputBar({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder,
  suggestions,
  onSuggest,
}: InputBarProps) {
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 168)}px`;
  }, [value]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!disabled && value.trim()) onSubmit();
  }

  const showSuggestions = suggestions && suggestions.length > 0 && onSuggest;

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 bg-rx-cream border-t border-rx-purple/10"
    >
      {/* Suggestion pills — fade in after first message */}
      <AnimatePresence>
        {showSuggestions && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="mx-auto max-w-3xl px-6 pt-2 overflow-hidden"
          >
            <p className="text-[11px] uppercase tracking-wide text-rx-subtle font-semibold mb-1.5">
              Suggested questions
            </p>
            <div className="flex flex-col gap-1.5 max-h-16 overflow-y-auto pr-1 [scrollbar-width:thin] [scrollbar-color:theme(colors.rx-purple/30)_transparent]">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSuggest(s)}
                  className="text-left text-xs rounded-lg border border-rx-purple/30 bg-white px-3 py-1.5 text-rx-purple hover:bg-rx-purple/10 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input row */}
      <div className="mx-auto max-w-3xl flex items-end gap-2 px-6 py-3">
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (!disabled && value.trim()) onSubmit();
            }
          }}
          rows={1}
          disabled={disabled}
          placeholder={placeholder ?? 'Ask about routes, revenue, load factor…'}
          className="flex-1 resize-none rounded-lg border border-rx-purple/20 bg-white px-3 py-2 text-rx-ink placeholder:text-rx-subtle focus:outline-none focus:ring-2 focus:ring-rx-purple/40 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-lg bg-rx-purple px-4 py-2 text-rx-cream font-medium hover:bg-rx-purpleDark disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </form>
  );
}
