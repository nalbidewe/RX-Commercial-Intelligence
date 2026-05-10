/**
 * Tiny API client for /api/chat.
 *
 * When running inside the Chainlit deployment (no Easy Auth sidecar), we
 * resolve the signed-in user's UPN from /api/commercial/me and include it as
 * X-User-UPN on every request so Power BI RLS works correctly.
 */

export interface ChatResponse {
  card: Record<string, unknown>;
  dax: string;
  summary: string;
  /** Raw rows from Power BI — shape depends on the DAX query. */
  data: Record<string, unknown>[];
  conversation_id: string;
  user: string;
  // [DEBUG] only present when COMMERCIAL_DEBUG=true on the backend
  debug_info?: { error_type: string; error_message: string; traceback: string } | null;
}

let _upnPromise: Promise<string> | null = null;

export function resolveUpn(): Promise<string> {
  if (!_upnPromise) {
    _upnPromise = fetch('/api/commercial/me', { credentials: 'include' })
      .then((r) => r.json())
      .then((body) => (body as { upn: string }).upn ?? '')
      .catch(() => '');
  }
  return _upnPromise;
}

export async function postChat(
  question: string,
  conversationId: string | null,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const upn = await resolveUpn();

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (upn) headers['X-User-UPN'] = upn;

  const res = await fetch('/api/chat', {
    method: 'POST',
    headers,
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
