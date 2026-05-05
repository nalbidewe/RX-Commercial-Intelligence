import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import InputBar from './components/InputBar';
import OutputCard from './components/OutputCard';
import LoadingCard from './components/LoadingCard';
import EmptyState from './components/EmptyState';
import { DEFAULT_FAQS } from './components/FAQCard';
import { postChat, resolveUpn, ChatResponse } from './api/client';
import { deriveChart } from './lib/deriveChart';

interface OutputEntry extends ChatResponse {
  question: string;
  timestamp: number;
}

export default function App() {
  const [input, setInput] = useState('');
  const [outputs, setOutputs] = useState<OutputEntry[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Redirect to Chainlit login if the session has expired or is missing
  useEffect(() => {
    resolveUpn().then((upn) => {
      if (!upn) window.location.href = '/login';
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [outputs, loading]);

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    setLoading(true);
    setError(null);
    setInput('');

    try {
      const resp = await postChat(question, conversationId);
      setConversationId(resp.conversation_id);
      setOutputs((prev) => [...prev, { ...resp, question, timestamp: Date.now() }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const isEmpty = outputs.length === 0 && !loading && !error;
  // Only surface suggestion pills after the first exchange — the EmptyState
  // already shows them on the initial screen so showing them twice is redundant.
  const showSuggestions = outputs.length > 0 || loading;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      {/* Single centred column — no sidebar once chat starts */}
      <main className="flex-1 mx-auto max-w-3xl w-full px-6 py-6">
        <div className="space-y-6">
          {isEmpty && <EmptyState onPick={setInput} />}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          {outputs.map((o) => {
            const chart = deriveChart(o.data);
            const time = new Date(o.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            });

            return (
              <motion.div
                key={`${o.conversation_id}-${o.timestamp}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="space-y-3"
              >
                {/* User bubble — right aligned */}
                <div className="flex justify-end">
                  <div className="max-w-[75%] bg-rx-purple text-white rounded-2xl rounded-tr-sm px-4 py-3">
                    <p className="text-sm leading-relaxed">{o.question}</p>
                    <p className="text-xs text-white/60 mt-1 text-right">{time}</p>
                  </div>
                </div>

                {/* AI response — left aligned */}
                <div className="flex justify-start">
                  <div className="w-full">
                    <OutputCard
                      card={o.card}
                      dax={o.dax}
                      summary={o.summary}
                      chart={chart}
                    />
                  </div>
                </div>
              </motion.div>
            );
          })}

          {loading && (
            <div className="space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[75%] bg-rx-purple/80 text-white rounded-2xl rounded-tr-sm px-4 py-3">
                  <p className="text-sm opacity-70">Sending…</p>
                </div>
              </div>
              <LoadingCard />
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      <InputBar
        value={input}
        onChange={setInput}
        onSubmit={handleSend}
        disabled={loading}
        suggestions={showSuggestions ? DEFAULT_FAQS : undefined}
        onSuggest={setInput}
      />
    </div>
  );
}
