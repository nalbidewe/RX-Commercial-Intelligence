import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import InputBar from './components/InputBar';
import OutputCard from './components/OutputCard';
import LoadingCard from './components/LoadingCard';
import EmptyState from './components/EmptyState';
import LoginScreen from './components/LoginScreen';
import { DEFAULT_FAQS } from './components/FAQCard';
import { postChat, ChatResponse } from './api/client';
import { deriveChart } from './lib/deriveChart';

interface OutputEntry extends ChatResponse {
  question: string;
  timestamp: number;
}

// Auth states: checking /api/commercial/me → authenticated or needs login
type AuthState = 'checking' | 'authenticated' | 'unauthenticated';

export default function App() {
  // ── All hooks must be declared before any early return ──
  const [authState, setAuthState] = useState<AuthState>('checking');
  const [input, setInput] = useState('');
  const [outputs, setOutputs] = useState<OutputEntry[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Check authentication via Easy Auth /me endpoint on mount
  useEffect(() => {
    fetch('/api/commercial/me', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data: { upn?: string }) => {
        setAuthState(data.upn ? 'authenticated' : 'unauthenticated');
      })
      .catch(() => setAuthState('unauthenticated'));
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

  // ── Auth gates — safe to early-return after all hooks ──
  if (authState === 'checking') {
    return <div className="min-h-screen bg-rx-cream" />;
  }

  if (authState === 'unauthenticated') {
    return <LoginScreen onLocalDevBypass={() => setAuthState('authenticated')} />;
  }

  // ── Main app ──
  const isEmpty = outputs.length === 0 && !loading && !error;
  const showSuggestions = outputs.length > 0 || loading;

  return (
    <div className="min-h-screen flex flex-col">
      <Header onLogout={() => setAuthState('unauthenticated')} />

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
                <div className="flex justify-end">
                  <div className="max-w-[75%] bg-rx-purple text-white rounded-2xl rounded-tr-sm px-4 py-3">
                    <p className="text-sm leading-relaxed">{o.question}</p>
                    <p className="text-xs text-white/60 mt-1 text-right">{time}</p>
                  </div>
                </div>

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
