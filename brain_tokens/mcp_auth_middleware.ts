/**
 * ALFA Brain - MCP Auth Middleware
 * =================================
 * Wklej ten kod do Edge Function mcp-server na Supabase.
 *
 * Jak używać:
 *   1. Otwórz Supabase Dashboard → Edge Functions → mcp-server → Edit
 *   2. Dodaj import i wywołanie validateBrainToken() przed główną logiką
 *   3. Deploy
 *
 * Klienci MCP muszą wysyłać:
 *   Authorization: Bearer <token>
 *
 * Supabase config.toml (dodaj do [functions.mcp-server]):
 *   verify_jwt = false  (my weryfikujemy sami przez token_hash)
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// Opcjonalna lista narzędzi wymagających scope=write lub admin
const WRITE_TOOLS = new Set(["add_memory"]);
const ADMIN_TOOLS = new Set(["delete_memory", "admin_stats"]);

/** Wynik walidacji tokenu */
interface AuthResult {
  valid: boolean;
  tokenId?: string;
  label?: string;
  scope?: string;
  reason?: string;
}

/**
 * Hashuje Bearer token do SHA-256 hex — identycznie jak baza danych.
 * Supabase przechowuje tylko hash, nigdy plaintext.
 */
async function hashToken(raw: string): Promise<string> {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(raw),
  );
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Wyciągnij Bearer token z nagłówka Authorization.
 * Obsługuje też ?token=... w query string (dla klientów bez nagłówków).
 */
function extractToken(req: Request): string | null {
  const auth = req.headers.get("Authorization") ?? "";
  if (auth.toLowerCase().startsWith("bearer ")) {
    return auth.slice(7).trim();
  }
  const url = new URL(req.url);
  return url.searchParams.get("token");
}

/**
 * Główna funkcja walidacji — wywołaj ją na początku handlera MCP.
 *
 * @param req     Przychodzące żądanie HTTP
 * @param tool    Nazwa wywoływanego narzędzia MCP (jeśli znana)
 * @returns       AuthResult z valid=true lub valid=false + reason
 */
export async function validateBrainToken(
  req: Request,
  tool?: string,
): Promise<AuthResult> {
  const rawToken = extractToken(req);

  if (!rawToken) {
    return { valid: false, reason: "Brak tokenu. Wyślij: Authorization: Bearer <token>" };
  }

  const tokenHash = await hashToken(rawToken);

  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: { persistSession: false },
  });

  const { data, error } = await supabase
    .rpc("validate_brain_token", {
      p_token_hash: tokenHash,
      p_tool: tool ?? null,
    })
    .single();

  if (error || !data) {
    console.error("[BrainAuth] Błąd walidacji tokenu:", error?.message);
    return { valid: false, reason: "Błąd walidacji - spróbuj ponownie" };
  }

  if (!data.valid) {
    return { valid: false, reason: data.reason };
  }

  // Sprawdź uprawnienia scope dla danego narzędzia
  if (tool && WRITE_TOOLS.has(tool) && data.scope === "read") {
    return {
      valid: false,
      reason: `Narzędzie '${tool}' wymaga scope=write lub admin. Twój scope: read`,
    };
  }
  if (tool && ADMIN_TOOLS.has(tool) && data.scope !== "admin") {
    return {
      valid: false,
      reason: `Narzędzie '${tool}' wymaga scope=admin. Twój scope: ${data.scope}`,
    };
  }

  return {
    valid: true,
    tokenId: data.token_id,
    label: data.label,
    scope: data.scope,
  };
}

/**
 * Pomocnicza funkcja — zwróć gotową odpowiedź 401/403.
 */
export function unauthorizedResponse(reason: string, status = 401): Response {
  return new Response(
    JSON.stringify({
      jsonrpc: "2.0",
      error: {
        code: status === 403 ? -32003 : -32001,
        message: reason,
      },
      id: null,
    }),
    {
      status,
      headers: {
        "Content-Type": "application/json",
        "WWW-Authenticate": 'Bearer realm="ALFA Brain MCP"',
      },
    },
  );
}

// =============================================================
// PRZYKŁAD INTEGRACJI — jak wkleić do Deno serve() w mcp-server
// =============================================================
/*

import { validateBrainToken, unauthorizedResponse } from "./mcp_auth_middleware.ts";

Deno.serve(async (req: Request) => {

  // --- Przepuść health-check bez auth ---
  const url = new URL(req.url);
  if (url.pathname.endsWith("/health")) {
    return new Response(JSON.stringify({ status: "ok" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // --- Wyciągnij nazwę narzędzia z body (opcjonalnie) ---
  let tool: string | undefined;
  try {
    const body = await req.clone().json();
    tool = body?.params?.name ?? body?.method;
  } catch (_) {}

  // --- Waliduj token ---
  const auth = await validateBrainToken(req, tool);
  if (!auth.valid) {
    return unauthorizedResponse(auth.reason!);
  }

  console.log(`[BrainAuth] Dostęp OK: ${auth.label} (scope=${auth.scope}, tool=${tool})`);

  // --- Tutaj dalsza logika MCP serwera ---
  // ...
});

*/
