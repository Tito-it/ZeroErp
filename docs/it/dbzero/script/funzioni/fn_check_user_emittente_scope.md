{% include-markdown "it/dbzero/script/manual/fn_check_user_emittente_scope.md" %}
# ⚙️ Funzione `fn_check_user_emittente_scope`

```sql
CREATE FUNCTION fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_cnt    integer;
    v_attivo bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se un utente ha accesso a uno specifico
    --   emittente fiscale. Sede unica read+write: la usano gli
    --   adapter RLS e i trigger di guardia.
    --
    -- Regole (refactor §4.6.B.5, + emittente attivo 2026-08-04):
    --   1. p_auth_user_id NULL -> true (job batch)
    --   2. Emittente attivo diverso da quello richiesto -> false
    --      (restringe CHIUNQUE, anche il super admin)
    --   3. fn_is_super_admin -> true (vede tutto)
    --   4. Assenza identita OPERATORE attiva -> false
    --      (defensive: utente disabilitato non accede)
    --   5. Whitelist vuota -> true (nessuna restrizione)
    --   6. Whitelist popolata -> EXISTS match
    -- =========================================================

    -- 1. Job batch (nessun utente)
    IF p_auth_user_id IS NULL THEN
        RETURN true;
    END IF;

    -- 2. Emittente attivo (impersonazione di scope).
    --    Deve precedere il ramo super admin: e' l'unico punto in
    --    cui la selezione puo' restringere chi vede tutto.
    --    IS DISTINCT FROM: con p_emittente_fiscale_id NULL
    --    (riferimento non risolto dagli adapter) resta fail-closed.
    v_attivo := NULLIF(
                    current_setting('app.current_emittente_id', true),
                    ''
                )::bigint;

    IF v_attivo IS NOT NULL
       AND p_emittente_fiscale_id IS DISTINCT FROM v_attivo THEN
        RETURN false;
    END IF;

    -- 3. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN true;
    END IF;

    -- 4. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN false;
    END IF;

    -- 5. Conta righe whitelist
    SELECT count(*)
      INTO v_cnt
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id;

    IF v_cnt = 0 THEN
        RETURN true;  -- nessuna restrizione
    END IF;

    -- 6. Verifica match specifico
    RETURN EXISTS (
        SELECT 1
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id         = p_auth_user_id
           AND uef.emittente_fiscale_id = p_emittente_fiscale_id
    );
END
$function$

COMMENT ON FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Verifica accesso utente a emittente fiscale. Refactor §4.6.B.5: NULL user/SUPER_ADMIN -> true; identita OPERATORE mancante -> false; whitelist vuota -> true; altrimenti match EXISTS. Post 2026-08-04: se la GUC app.current_emittente_id e'' valorizzata e diversa dall''emittente richiesto -> false, PRIMA del bypass super admin (impersonazione di scope: solo restringente, mai allargante).';
```

---
{% include-markdown "signature-core.md" %}
