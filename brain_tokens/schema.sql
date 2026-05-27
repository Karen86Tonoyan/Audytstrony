-- =======================================================
-- ALFA Brain - Token Admin Schema
-- Wdrożenie: Supabase SQL Editor → Run
-- =======================================================

-- Tabela tokenów dostępu do Brain/MCP
CREATE TABLE IF NOT EXISTS brain_access_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash  TEXT NOT NULL UNIQUE,       -- SHA-256 tokenu (nigdy plaintext)
    label       TEXT NOT NULL,              -- np. "Claude Desktop Karen", "Cursor Biuro"
    owner_email TEXT,                       -- opcjonalnie - właściciel tokenu
    scope       TEXT NOT NULL DEFAULT 'read',  -- 'read' | 'write' | 'admin'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,               -- NULL = nie wygasa
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at  TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    use_count   INTEGER NOT NULL DEFAULT 0
);

-- Indeks do szybkiego lookup po hash
CREATE INDEX IF NOT EXISTS idx_brain_tokens_hash
    ON brain_access_tokens (token_hash)
    WHERE NOT revoked;

-- Indeks do filtrowania po właścicielu
CREATE INDEX IF NOT EXISTS idx_brain_tokens_owner
    ON brain_access_tokens (owner_email)
    WHERE NOT revoked;

-- Log użycia tokenów (audit trail)
CREATE TABLE IF NOT EXISTS brain_token_audit (
    id          BIGSERIAL PRIMARY KEY,
    token_id    UUID REFERENCES brain_access_tokens(id) ON DELETE SET NULL,
    token_label TEXT,
    action      TEXT NOT NULL,   -- 'access' | 'denied' | 'revoked' | 'created'
    tool_called TEXT,            -- np. 'add_memory', 'search_notes'
    ip_address  TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Widok dla panelu admin (bez hash)
CREATE OR REPLACE VIEW brain_tokens_admin AS
SELECT
    id,
    label,
    owner_email,
    scope,
    created_at,
    expires_at,
    revoked,
    revoked_at,
    last_used_at,
    use_count,
    CASE
        WHEN revoked THEN 'revoked'
        WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 'expired'
        ELSE 'active'
    END AS status
FROM brain_access_tokens
ORDER BY created_at DESC;

-- Funkcja walidacji tokenu (wywoływana przez Edge Function)
CREATE OR REPLACE FUNCTION validate_brain_token(p_token_hash TEXT, p_tool TEXT DEFAULT NULL)
RETURNS TABLE (
    valid       BOOLEAN,
    token_id    UUID,
    label       TEXT,
    scope       TEXT,
    reason      TEXT
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_row brain_access_tokens%ROWTYPE;
BEGIN
    SELECT * INTO v_row
    FROM brain_access_tokens
    WHERE token_hash = p_token_hash;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, NULL::TEXT, NULL::TEXT, 'Token nie istnieje';
        RETURN;
    END IF;

    IF v_row.revoked THEN
        RETURN QUERY SELECT FALSE, v_row.id, v_row.label, v_row.scope, 'Token unieważniony';
        RETURN;
    END IF;

    IF v_row.expires_at IS NOT NULL AND v_row.expires_at < NOW() THEN
        RETURN QUERY SELECT FALSE, v_row.id, v_row.label, v_row.scope, 'Token wygasł';
        RETURN;
    END IF;

    -- Zaktualizuj statystyki użycia
    UPDATE brain_access_tokens
    SET last_used_at = NOW(),
        use_count = use_count + 1
    WHERE id = v_row.id;

    -- Zapisz do audit log
    INSERT INTO brain_token_audit (token_id, token_label, action, tool_called)
    VALUES (v_row.id, v_row.label, 'access', p_tool);

    RETURN QUERY SELECT TRUE, v_row.id, v_row.label, v_row.scope, 'OK';
END;
$$;

-- Funkcja tworzenia tokenu (admin)
CREATE OR REPLACE FUNCTION create_brain_token(
    p_label       TEXT,
    p_owner_email TEXT DEFAULT NULL,
    p_scope       TEXT DEFAULT 'read',
    p_expires_days INTEGER DEFAULT NULL
)
RETURNS TABLE (token TEXT, token_id UUID)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_raw_token TEXT;
    v_hash      TEXT;
    v_id        UUID;
    v_expires   TIMESTAMPTZ;
BEGIN
    -- Wygeneruj kryptograficznie losowy token (32 bajty = 64 hex)
    v_raw_token := encode(gen_random_bytes(32), 'hex');
    v_hash := encode(digest(v_raw_token, 'sha256'), 'hex');

    IF p_expires_days IS NOT NULL THEN
        v_expires := NOW() + (p_expires_days || ' days')::INTERVAL;
    END IF;

    INSERT INTO brain_access_tokens (token_hash, label, owner_email, scope, expires_at)
    VALUES (v_hash, p_label, p_owner_email, p_scope, v_expires)
    RETURNING id INTO v_id;

    -- Audit
    INSERT INTO brain_token_audit (token_id, token_label, action)
    VALUES (v_id, p_label, 'created');

    -- Zwróć TYLKO raz plaintext token (potem nie do odtworzenia)
    RETURN QUERY SELECT v_raw_token, v_id;
END;
$$;

-- Funkcja unieważniania tokenu
CREATE OR REPLACE FUNCTION revoke_brain_token(p_token_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    UPDATE brain_access_tokens
    SET revoked = TRUE, revoked_at = NOW()
    WHERE id = p_token_id AND NOT revoked;

    IF FOUND THEN
        INSERT INTO brain_token_audit (token_id, action)
        VALUES (p_token_id, 'revoked');
        RETURN TRUE;
    END IF;
    RETURN FALSE;
END;
$$;

-- RLS: tylko service_role może czytać/pisać (Edge Function używa service_role key)
ALTER TABLE brain_access_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE brain_token_audit   ENABLE ROW LEVEL SECURITY;

-- Brak policy dla anon/authenticated → dostęp tylko przez SECURITY DEFINER functions
-- Edge Function używa service_role key, więc bypass RLS

COMMENT ON TABLE brain_access_tokens IS
    'Tokeny dostępu do ALFA Brain MCP API. Przechowuje tylko hash, nigdy plaintext.';
COMMENT ON TABLE brain_token_audit IS
    'Audit log każdego użycia / odmowy / unieważnienia tokenu.';
