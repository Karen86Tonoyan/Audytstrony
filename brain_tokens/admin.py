#!/usr/bin/env python3
"""
ALFA Brain - Admin CLI dla tokenów dostępu
==========================================
Zarządzaj tokenami MCP z linii poleceń.

Wymagania:
    pip install httpx python-dotenv

Konfiguracja (.env lub zmienne środowiskowe):
    SUPABASE_URL=https://ocbwiopyscjdpjewsssx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...  (Settings → API → service_role key)

Użycie:
    python brain_tokens/admin.py create "Claude Desktop" --scope write --email karen@example.com
    python brain_tokens/admin.py list
    python brain_tokens/admin.py revoke <token_id>
    python brain_tokens/admin.py audit --limit 20
    python brain_tokens/admin.py test <raw_token>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Optional

try:
    import httpx
except ImportError:
    print("Brak httpx. Zainstaluj: pip install httpx python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_config() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("Ustaw SUPABASE_URL i SUPABASE_SERVICE_KEY w .env lub środowisku!")
        sys.exit(1)
    return url, key


def supabase_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def rpc(url: str, key: str, function: str, params: dict) -> dict:
    """Wywołaj funkcję PostgreSQL przez Supabase REST API."""
    resp = httpx.post(
        f"{url}/rest/v1/rpc/{function}",
        headers=supabase_headers(key),
        json=params,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def query(url: str, key: str, table: str, params: dict = None) -> list:
    """Zapytanie SELECT przez Supabase REST API."""
    resp = httpx.get(
        f"{url}/rest/v1/{table}",
        headers={**supabase_headers(key), "Prefer": "return=representation"},
        params=params or {},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Polecenia CLI
# ---------------------------------------------------------------------------

def cmd_create(
    label: str,
    scope: str = "read",
    email: Optional[str] = None,
    expires_days: Optional[int] = None,
) -> None:
    """Utwórz nowy token dostępu."""
    url, key = get_config()
    params = {
        "p_label": label,
        "p_owner_email": email,
        "p_scope": scope,
        "p_expires_days": expires_days,
    }
    result = rpc(url, key, "create_brain_token", params)

    # Supabase RPC zwraca listę wierszy
    if isinstance(result, list):
        result = result[0]

    raw_token = result["token"]
    token_id  = result["token_id"]

    print()
    print("=" * 60)
    print("  TOKEN WYGENEROWANY — zapisz go teraz, nie zobaczysz go ponownie!")
    print("=" * 60)
    print(f"  ID:     {token_id}")
    print(f"  Label:  {label}")
    print(f"  Scope:  {scope}")
    print(f"  Email:  {email or '—'}")
    print(f"  Expires: {'nigdy' if not expires_days else f'za {expires_days} dni'}")
    print()
    print(f"  TOKEN:  {raw_token}")
    print()
    print("  Konfiguracja Claude Desktop:")
    print('  {')
    print('    "mcpServers": {')
    print('      "alfa-knowledge": {')
    print(f'        "url": "{url.replace("supabase.co", "functions.supabase.co")}/mcp-server",')
    print('        "transport": "http",')
    print('        "headers": {')
    print(f'          "Authorization": "Bearer {raw_token}"')
    print('        }')
    print('      }')
    print('    }')
    print('  }')
    print("=" * 60)


def cmd_list(show_revoked: bool = False) -> None:
    """Wylistuj tokeny (przez widok brain_tokens_admin)."""
    url, key = get_config()

    params = {"select": "*", "order": "created_at.desc", "limit": "50"}
    if not show_revoked:
        params["status"] = "eq.active"

    try:
        rows = query(url, key, "brain_tokens_admin", params)
    except httpx.HTTPStatusError as e:
        # Widok może nie być jeszcze dostępny przez REST — fallback do tabeli
        rows = query(url, key, "brain_access_tokens", {
            "select": "id,label,owner_email,scope,created_at,expires_at,revoked,last_used_at,use_count",
            "order": "created_at.desc",
            "limit": "50",
        })
        if not show_revoked:
            rows = [r for r in rows if not r.get("revoked")]

    if not rows:
        print("Brak aktywnych tokenów.")
        return

    print(f"\n{'ID':<36}  {'Label':<25}  {'Scope':<6}  {'Użycia':>5}  {'Status'}")
    print("-" * 90)
    for r in rows:
        ts = r.get("last_used_at", "—")
        if ts and ts != "—":
            ts = ts[:16].replace("T", " ")
        status = r.get("status", "revoked" if r.get("revoked") else "active")
        print(
            f"{r['id']}  {r['label'][:25]:<25}  {r['scope']:<6}  {r.get('use_count', 0):>5}  {status}"
        )
    print(f"\nRazem: {len(rows)} tokenów")


def cmd_revoke(token_id: str) -> None:
    """Unieważnij token po ID."""
    url, key = get_config()
    result = rpc(url, key, "revoke_brain_token", {"p_token_id": token_id})
    if result is True or result == [True] or (isinstance(result, list) and result and result[0]):
        print(f"Token {token_id} unieważniony.")
    else:
        print(f"Nie znaleziono aktywnego tokenu {token_id}.")


def cmd_audit(limit: int = 20) -> None:
    """Pokaż log ostatnich akcji."""
    url, key = get_config()
    rows = query(url, key, "brain_token_audit", {
        "select": "created_at,action,token_label,tool_called,ip_address",
        "order": "created_at.desc",
        "limit": str(limit),
    })

    if not rows:
        print("Brak wpisów w audit log.")
        return

    print(f"\n{'Czas':<20}  {'Akcja':<8}  {'Token':<25}  {'Narzędzie'}")
    print("-" * 80)
    for r in rows:
        ts = (r.get("created_at") or "")[:16].replace("T", " ")
        print(
            f"{ts:<20}  {r.get('action',''):<8}  {(r.get('token_label') or '—')[:25]:<25}  "
            f"{r.get('tool_called') or '—'}"
        )


def cmd_test(raw_token: str) -> None:
    """Przetestuj token lokalnie (sprawdź hash i status w bazie)."""
    url, key = get_config()
    token_hash = hash_token(raw_token)
    print(f"SHA-256: {token_hash}")

    result = rpc(url, key, "validate_brain_token", {
        "p_token_hash": token_hash,
        "p_tool": "test",
    })
    if isinstance(result, list):
        result = result[0]

    if result.get("valid"):
        print(f"Token WAŻNY — label: {result['label']}, scope: {result['scope']}")
    else:
        print(f"Token NIEWAŻNY — powód: {result.get('reason')}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "create":
        if len(args) < 2:
            print("Użycie: admin.py create <label> [--scope read|write|admin] [--email x] [--days N]")
            sys.exit(1)
        label = args[1]
        scope = "read"
        email = None
        days  = None
        i = 2
        while i < len(args):
            if args[i] == "--scope" and i + 1 < len(args):
                scope = args[i + 1]; i += 2
            elif args[i] == "--email" and i + 1 < len(args):
                email = args[i + 1]; i += 2
            elif args[i] == "--days" and i + 1 < len(args):
                days = int(args[i + 1]); i += 2
            else:
                i += 1
        cmd_create(label, scope, email, days)

    elif cmd == "list":
        show_all = "--all" in args
        cmd_list(show_revoked=show_all)

    elif cmd == "revoke":
        if len(args) < 2:
            print("Użycie: admin.py revoke <token_id>")
            sys.exit(1)
        cmd_revoke(args[1])

    elif cmd == "audit":
        limit = 20
        if "--limit" in args:
            i = args.index("--limit")
            limit = int(args[i + 1])
        cmd_audit(limit)

    elif cmd == "test":
        if len(args) < 2:
            print("Użycie: admin.py test <raw_token>")
            sys.exit(1)
        cmd_test(args[1])

    else:
        print(f"Nieznane polecenie: {cmd}")
        print("Dostępne: create, list, revoke, audit, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
