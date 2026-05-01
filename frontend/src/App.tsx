import { useState } from 'react';
import Header from './components/Header';
import InputBar from './components/InputBar';
import OutputCard from './components/OutputCard';
import FAQCard, { DEFAULT_FAQS } from './components/FAQCard';
import LoadingCard from './components/LoadingCard';
import { postChat, ChatResponse } from './api/client';
import {
  SAMPLE_CARD,
  SAMPLE_DAX,
  SAMPLE_QUESTION,
  SAMPLE_SUMMARY,
} from './sampleCard';

interface OutputEntry extends ChatResponse {
  question: string;
  timestamp: number;
}

// In dev mode, seed a sample Adaptive Card so the UI can be previewed
// without the FastAPI backend running. Real backend calls still work
// when uvicorn is up — this is just the initial state.
const INITIAL_OUTPUTS: OutputEntry[] = import.meta.env.DEV
  ? [
      {
        card: SAMPLE_CARD,
        dax: SAMPLE_DAX,
        summary: SAMPLE_SUMMARY,
        conversation_id: 'sample',
        user: 'preview@vendor.riyadhair.com',
        question: SAMPLE_QUESTION,
        timestamp: Date.now(),
      },
    ]
  : [];

export default function App() {
  const [input, setInput] = useState('');
  const [outputs, setOutputs] = useState<OutputEntry[]>(INITIAL_OUTPUTS);
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
      const entry: OutputEntry = {
        ...resp,
        question,
        timestamp: Date.now(),
      };
      // newest on top
      setOutputs((prev) => [entry, ...prev]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 mx-auto max-w-5xl w-full px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Outputs feed (2/3 width on desktop, full on mobile) */}
          <section className="lg:col-span-2 space-y-4">
            {loading && <LoadingCard />}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm">
                {error}
              </div>
            )}

            {outputs.length === 0 && !loading && !error && (
              <div className="bg-white rounded-xl shadow-card border border-rx-purple/10 p-6 text-rx-subtle">
                Ask a question to get started, or pick a suggestion on the right.
              </div>
            )}

            {outputs.map((o) => (
              <OutputCard
                key={`${o.conversation_id}-${o.timestamp}`}
                question={o.question}
                card={o.card}
                dax={o.dax}
                summary={o.summary}
                timestamp={o.timestamp}
              />
            ))}
          </section>

          {/* FAQ chips */}
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
