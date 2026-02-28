{% include-markdown "it/dbzero/config/manual/fn_check_user_emittente_scope.md" %}
# ⚙️ Funzione `fn_check_user_emittente_scope`

```sql
CREATE FUNCTION fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_ruolo     config.ruolo_sistema;
  v_cnt       integer;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Verifica se un utente ha accesso a uno specifico
  --   emittente fiscale. Pensata per trigger defense-in-depth
  --   su tabelle operative (fatture, ordini, pagamenti).
  --   Funzione fn_check_*: puro boolean, no raise.
  --
  -- Regole:
  --   1. p_auth_user_id NULL → true (job batch, nessun filtro)
  --   2. ADMIN → true (vede tutto)
  --   3. Whitelist vuota → true (nessuna restrizione)
  --   4. Whitelist con righe → true solo se emittente presente
  -- =========================================================

  -- 1. Job batch (nessun utente)
  IF p_auth_user_id IS NULL THEN
    RETURN true;
  END IF;

  -- 2. Ruolo sistema
  v_ruolo := config.fn_get_ruolo_sistema(p_auth_user_id);

  IF v_ruolo = 'ADMIN' THEN
    RETURN true;
  END IF;

  -- 3. Conta righe whitelist
  SELECT count(*)
    INTO v_cnt
    FROM config.user_emittenti_fiscali uef
   WHERE uef.auth_user_id = p_auth_user_id;

  IF v_cnt = 0 THEN
    RETURN true;  -- nessuna restrizione
  END IF;

  -- 4. Verifica match specifico
  RETURN EXISTS (
    SELECT 1
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id       = p_auth_user_id
       AND uef.emittente_fiscale_id = p_emittente_fiscale_id
  );
END
$function$

COMMENT ON FUNCTION config.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Verifica accesso utente a emittente fiscale: NULL user/ADMIN/whitelist vuota → true.';
```

---
{% include-markdown "signature-core.md" %}
