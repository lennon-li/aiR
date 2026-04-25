// api.ts
const API_BASE = "https://air-api-1035241559282.us-central1.run.app";

export const createSession = async (objective: string, slider: number) => {
  const resp = await fetch(`${API_BASE}/v1/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective, slider })
  });
  return resp.json();
};

export const sendChat = async (sessionId: string, message: string, slider: number) => {
  const resp = await fetch(`${API_BASE}/v1/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, slider_value: slider })
  });
  return resp.json();
};

export const executeR = async (sessionId: string, code: string) => {
  const resp = await fetch(`${API_BASE}/v1/sessions/${sessionId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  });
  return resp.json();
};
