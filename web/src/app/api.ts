// web/src/app/api.ts
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "https://air-api-652486026072.us-central1.run.app";
const API_SECRET = process.env.NEXT_PUBLIC_API_SECRET;

const getApiHeaders = (): HeadersInit => ({
  'Content-Type': 'application/json',
  ...(API_SECRET ? { Authorization: `Bearer ${API_SECRET}` } : {}),
});

export interface ObjectSummary {
  name: string;
  type: string;
  details: string;
}

export interface ExecuteResponse {
  status: string;
  stdout: string;
  error?: string | string[];
  plots: string[];
  environment: ObjectSummary[];
}

export interface ProposedOption {
  id: string;
  label: string;
  prompt: string;
}

export interface StructuredAnalysisResponse {
  response_type: string;
  summary: string;
  what: string;
  why: string;
  code: string;
  interpretation: string;
  next_step: string;
  options: ProposedOption[];
  uses_objects: string[];
  should_autorun: boolean;
}

export interface ChatResponse {
  response: string;
  structured_response?: StructuredAnalysisResponse;
  grounded: boolean;
  g_type?: string;
  intent?: string;
}

export type SessionMode = 'guided' | 'balanced' | 'autonomous';

export const createSession = async (objective: string, mode: SessionMode, plan?: string | null): Promise<{ session_id: string }> => {
  const resp = await fetch(`${API_BASE}/v1/sessions`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({ objective, analysis_mode: mode, analysis_plan: plan })
  });
  return resp.json();
};
export const sendAgentChat = async (
  sessionId: string, 
  message?: string, 
  context?: {
    objective?: string;
    guidance_depth?: string;
    dataset_summary?: string;
  },
  event?: string
): Promise<{
  reply: string;
  code: string;
  executed: boolean;
  execution_output?: string;
  execution_error?: string;
  plots?: string[];
  environment?: ObjectSummary[];
  session_id: string;
  agent: string;
  intent?: string;
  mode: string;
}> => {
  const response = await fetch(`${API_BASE}/v1/agent/chat`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({
      session_id: sessionId,
      message,
      event,
      context
    }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Conversation Agent call failed");
  }
  return response.json();
};

export const sendChat = async (
  sessionId: string, 
  message: string, 
  mode: SessionMode, 
  context: {
    objective?: string,
    file_names?: string[],
    env_summary?: ObjectSummary[],
    recent_history?: string[],
    last_error?: string,
    coaching_depth?: number
  } = {}
): Promise<ChatResponse> => {
  const resp = await fetch(`${API_BASE}/v1/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({ 
      message, 
      analysis_mode: mode, 
      objective: context.objective,
      file_names: context.file_names,
      env_summary: context.env_summary,
      recent_history: context.recent_history,
      last_error: context.last_error,
      coaching_depth: context.coaching_depth
    })
  });
  return resp.json();
};

export const sendChatStream = async (
  sessionId: string, 
  message: string, 
  analysisMode: string, 
  context: any,
  onEvent: (event: {type: string, message?: string, content?: string, full_content?: string}) => void
) => {
  const resp = await fetch(`${API_BASE}/v1/sessions/${sessionId}/chat_stream`, {
      method: 'POST',
      headers: getApiHeaders(),
      body: JSON.stringify({ 
        message, 
        analysis_mode: analysisMode, 
        objective: context.objective,
        file_names: context.file_names,
        env_summary: context.env_summary,
        recent_history: context.recent_history,
        last_error: context.last_error,
        coaching_depth: context.coaching_depth
      })
  });

  if (!resp.body) throw new Error("No response body");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
          if (line.startsWith("data: ")) {
              try {
                  const data = JSON.parse(line.slice(6));
                  onEvent(data);
              } catch (e) {
                  console.error("Error parsing SSE line", line, e);
              }
          }
      }
  }
};

export const refreshSession = async (sessionId: string, mode: SessionMode, depth?: number) => {
  const resp = await fetch(`${API_BASE}/v1/sessions/${sessionId}/refresh`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({ analysis_mode: mode, coaching_depth: depth })
  });
  return resp.json();
};

export const executeR = async (sessionId: string, code: string, isAgentCode: boolean = false, provenance: string = "You"): Promise<ExecuteResponse> => {
  const resp = await fetch(`${API_BASE}/v1/sessions/${sessionId}/execute`, {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({ code, is_agent_code: isAgentCode, provenance })
  });
  return resp.json();
};

export const reportTelemetry = async (sessionId: string, eventType: string, data: Record<string, unknown>) => {
  try {
    await fetch(`${API_BASE}/v1/sessions/${sessionId}/telemetry`, {
      method: 'POST',
      headers: getApiHeaders(),
      body: JSON.stringify({ event_type: eventType, data })
    });
  } catch (e) {
    console.error("Telemetry failed", e);
  }
};
