export const corsHeaders = {
  "Access-Control-Allow-Origin": Deno.env.get("FRONTEND_ORIGIN") ?? "http://localhost:5173",
  "Access-Control-Allow-Headers": "authorization, content-type",
};
