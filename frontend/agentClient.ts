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
  return data as { message: string; action: string | null; payload: Record<string, unknown> };
}

export function executeAction(response: { action: string | null; payload: Record<string, unknown> }) {
  switch (response.action) {
    case "OPEN_HOTEL_MODULE":
      return { route: "/hotels", params: response.payload };
    case "OPEN_PET_PROFILE":
      return { route: "/pets/profile", params: response.payload };
    case "CONTACT_SUPPORT":
      return { route: "/support", params: response.payload };
    default:
      return null;
  }
}
