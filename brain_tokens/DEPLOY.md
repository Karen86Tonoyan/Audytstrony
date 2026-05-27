# ALFA Brain — Wdrożenie tokenów dostępu

## Krok 1 — Dodaj tabele do Supabase

1. Otwórz **Supabase Dashboard** → **SQL Editor**
2. Wklej i uruchom plik `schema.sql`
3. Sprawdź czy powstały tabele `brain_access_tokens` i `brain_token_audit`

## Krok 2 — Zaktualizuj Edge Function mcp-server

Otwórz **Edge Functions → mcp-server → Edit** i dodaj na początku pliku:

```typescript
import { validateBrainToken, unauthorizedResponse } from "./mcp_auth_middleware.ts";
```

Następnie w `Deno.serve(async (req) => {` dodaj zaraz po sprawdzeniu `/health`:

```typescript
// Waliduj token (pomiń health-check)
if (!req.url.endsWith("/health")) {
  let tool: string | undefined;
  try { tool = (await req.clone().json())?.params?.name; } catch (_) {}

  const auth = await validateBrainToken(req, tool);
  if (!auth.valid) return unauthorizedResponse(auth.reason!);
}
```

## Krok 3 — Konfiguracja .env (lokalny admin)

```
SUPABASE_URL=https://ocbwiopyscjdpjewsssx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Settings → API → service_role secret key
```

## Krok 4 — Tworzenie tokenów

```bash
# Token tylko do odczytu (dla kogoś innego)
python brain_tokens/admin.py create "Jan Kowalski - Claude Desktop" --scope read --email jan@firma.pl

# Token do zapisu (dla siebie)
python brain_tokens/admin.py create "Karen - Cursor" --scope write

# Token admin (pełny dostęp)
python brain_tokens/admin.py create "Karen - Admin" --scope admin

# Z datą wygaśnięcia (30 dni)
python brain_tokens/admin.py create "Gość testowy" --scope read --days 30
```

## Zarządzanie tokenami

```bash
# Lista aktywnych tokenów
python brain_tokens/admin.py list

# Lista wszystkich (też unieważnione)
python brain_tokens/admin.py list --all

# Unieważnij token
python brain_tokens/admin.py revoke <token_id>

# Audit log (ostatnie 20 użyć)
python brain_tokens/admin.py audit

# Przetestuj token
python brain_tokens/admin.py test <raw_token>
```

## Konfiguracja klientów MCP

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "alfa-knowledge": {
      "url": "https://ocbwiopyscjdpjewsssx.functions.supabase.co/mcp-server",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer <twój_token>"
      }
    }
  }
}
```

### Cursor / Cline
W ustawieniach MCP dodaj nagłówek:
```
Authorization: Bearer <twój_token>
```

## Zakresy dostępu (scope)

| Scope   | search_notes | get_note | search_nodes | get_neighbors | add_memory |
|---------|:---:|:---:|:---:|:---:|:---:|
| `read`  | ✅ | ✅ | ✅ | ✅ | ❌ |
| `write` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ |
