/**
 * Tiny API client for /api/chat. The browser sends Easy Auth cookies
 * automatically (same-origin), so no auth handling is needed here.
 */

export interface ChatResponse {
  card: Record<string, unknown>;
  dax: string;
  summary: string;
  /** Raw rows from Power BI — shape depends on the DAX query. */
  data: Record<string, unknown>[];
  conversation_id: string;
  user: string;
}

export async function postChat(
  question: string,
  conversationId: string | null,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
    credentials: 'include',
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }

  return (await res.json()) as ChatResponse;
}
