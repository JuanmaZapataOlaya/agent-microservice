export const corsHeaders = {
  "Access-Control-Allow-Origin": Deno.env.get("FRONTEND_ORIGIN") ?? "http://localhost:5173",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
