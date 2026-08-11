interface ChatPayload {
  message: string;
  session_id: string | null;
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  calibrated: boolean;
  progress: number;
}

export async function sendMessage(
  message: string,
  sessionId: string | null,
): Promise<ChatResponse> {
  const payload: ChatPayload = {
    message,
    session_id: sessionId,
  };

  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    throw new Error(`Chat request failed: ${resp.status}`);
  }

  return resp.json();
}
