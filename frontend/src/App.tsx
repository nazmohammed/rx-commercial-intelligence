import { useState } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import InputBar from './components/InputBar';
import OutputCard from './components/OutputCard';
import FAQCard, { DEFAULT_FAQS } from './components/FAQCard';
import LoadingCard from './components/LoadingCard';
import ChartPanel from './components/ChartPanel';
import EmptyState from './components/EmptyState';
import { postChat, ChatResponse } from './api/client';
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

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    setLoading(true);
    setError(null);
    setInput('');

    try {
      const resp = await postChat(question, conversationId);
      setConversationId(resp.conversation_id);
      setOutputs((prev) => [
        { ...resp, question, timestamp: Date.now() },
        ...prev,
      ]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const isEmpty = outputs.length === 0 && !loading && !error;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 mx-auto max-w-6xl w-full px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2 space-y-4">
            {loading && <LoadingCard />}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm">
                {error}
              </div>
            )}

            {isEmpty && <EmptyState onPick={setInput} />}

            {outputs.map((o) => {
              const chart = deriveChart(o.data);
              return (
                <motion.div
                  key={`${o.conversation_id}-${o.timestamp}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                  className="space-y-4"
                >
                  {chart && <ChartPanel chart={chart} />}
                  <OutputCard
                    question={o.question}
                    card={o.card}
                    dax={o.dax}
                    summary={o.summary}
                    timestamp={o.timestamp}
                  />
                </motion.div>
              );
            })}
          </section>

          <aside className="space-y-3">
            <div className="text-xs uppercase tracking-wide text-rx-subtle font-semibold">
              Try asking
            </div>
            {DEFAULT_FAQS.map((q) => (
              <FAQCard key={q} question={q} onPick={setInput} />
            ))}
          </aside>
        </div>
      </main>

      <InputBar
        value={input}
        onChange={setInput}
        onSubmit={handleSend}
        disabled={loading}
      />
    </div>
  );
}
