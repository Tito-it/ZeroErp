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
    v_cnt integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se un utente ha accesso a uno specifico
    --   emittente fiscale. Usata in trigger defense-in-depth
    --   su tabelle operative (fatture, ordini, pagamenti).
    --
    -- Regole (refactor §4.6.B.5):
    --   1. p_auth_user_id NULL -> true (job batch)
    --   2. fn_is_super_admin -> true (vede tutto)
    --   3. Assenza identita OPERATORE attiva -> false
    --      (defensive: utente disabilitato non accede)
    --   4. Whitelist vuota -> true (nessuna restrizione)
    --   5. Whitelist popolata -> EXISTS match
    -- =========================================================

    -- 1. Job batch (nessun utente)
    IF p_auth_user_id IS NULL THEN
        RETURN true;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN true;
    END IF;

    -- 3. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN false;
    END IF;

    -- 4. Conta righe whitelist
    SELECT count(*)
      INTO v_cnt
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id;

    IF v_cnt = 0 THEN
        RETURN true;  -- nessuna restrizione
    END IF;

    -- 5. Verifica match specifico
    RETURN EXISTS (
        SELECT 1
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id         = p_auth_user_id
           AND uef.emittente_fiscale_id = p_emittente_fiscale_id
    );
END
$function$

COMMENT ON FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Verifica accesso utente a emittente fiscale. Refactor §4.6.B.5: NULL user/SUPER_ADMIN -> true; identita OPERATORE mancante -> false; whitelist vuota -> true; altrimenti match EXISTS.';
```

---
{% include-markdown "signature-core.md" %}
