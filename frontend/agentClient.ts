import { supabase } from "./supabase";

export async function startSession(userId: string) {
  const { data, error } = await supabase.functions.invoke("agent-gateway", {
    body: { user_id: userId, operation: "start_session" },
  });
  if (error) throw error;
  return data as { session_id: string; expires_at: string };
}

export async function sendMessage(sessionId: string, message: string) {
  const { data, error } = await supabase.functions.invoke("agent-gateway", {
    body: { session_id: sessionId, message },
  });
  if (error) throw error;
  return data as {
    message: string;
    action: "FIND_PET" | "REPORT_PET" | "RUN_TUTORIAL" | null;
    payload: Record<string, unknown>;
    session_id: string;
    correlation_id: string;
  };
}

export function executeAction(response: { action: string | null; payload: Record<string, unknown> }) {
  switch (response.action) {
    case "FIND_PET":
      return { type: "FIND_PET", params: response.payload };
    case "REPORT_PET":
      return { type: "REPORT_PET", params: response.payload };
    case "RUN_TUTORIAL":
      return { type: "RUN_TUTORIAL", params: response.payload };
    default:
      return null;
  }
}
