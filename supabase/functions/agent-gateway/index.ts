import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders } from "../_shared/cors.ts";

const agentUrl = Deno.env.get("AGENT_SERVICE_URL")!;
const edgeSecret = Deno.env.get("EDGE_SHARED_SECRET")!;

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  try {
    const auth = request.headers.get("Authorization");
    if (!auth?.startsWith("Bearer ")) throw new Error("Missing authentication");
    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
      global: { headers: { Authorization: auth } },
    });
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error || !user) return new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    const { data: allowed, error: limitError } = await supabase.rpc("check_rate_limit", { subject_key: user.id, max_requests: 30 });
    if (limitError || allowed === false) return new Response(JSON.stringify({ detail: "Rate limit exceeded" }), { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    const body = await request.json();
    const operation = body.operation ?? "chat";
    if (operation === "start_session" && typeof body.user_id !== "string") {
      return new Response(JSON.stringify({ detail: "Invalid user_id" }), { status: 422, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }
    if (operation === "chat" && (typeof body.message !== "string" || body.message.length < 1 || body.message.length > 8000)) {
      return new Response(JSON.stringify({ detail: "Invalid message" }), { status: 422, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }
    const upstream = await fetch(`${agentUrl}/${operation === "start_session" ? "session/start" : "chat"}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-edge-secret": edgeSecret, "x-correlation-id": crypto.randomUUID() },
      body: JSON.stringify(operation === "start_session"
        ? { user_id: user.id }
        : { session_id: body.session_id, message: body.message }),
    });
    return new Response(await upstream.text(), { status: upstream.status, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  } catch (error) {
    console.error("agent_gateway_error", error);
    return new Response(JSON.stringify({ detail: "Gateway error" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
});
