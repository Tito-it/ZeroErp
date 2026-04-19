{% include-markdown "it/dbzero/script/manual/fn_get_emittenti_scope_sr_ids.md" %}
# ⚙️ Funzione `fn_get_emittenti_scope_sr_ids`

```sql
CREATE FUNCTION fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
 RETURNS bigint[]
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ids bigint[];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Restituisce i soggetto_ruolo_id degli emittenti fiscali
    --   autorizzati per un utente. Le tabelle vendite usano
    --   emittente_soggetto_ruolo_id (FK a soggetti_ruoli),
    --   non emittente_fiscale_id: serve questa mappatura.
    --
    -- Semantica:
    --   NULL             = nessuna restrizione (vede tutto)
    --   '{}'::bigint[]   = nessun accesso
    --   array di ID      = limitato
    --
    -- Catena (refactor §4.6.B.6):
    --   1. Assenza identita OPERATORE attiva -> '{}' (no access)
    --   2. fn_is_super_admin -> NULL (nessuna restrizione)
    --   3. OPERATIVO: whitelist (NULL se vuota = all)
    -- =========================================================

    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN '{}'::bigint[];
    END IF;

    -- 2. Super admin? Nessuna restrizione.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN NULL;
    END IF;

    -- 3. OPERATIVO: mappa whitelist a soggetto_ruolo_id
    SELECT array_agg(ef.soggetto_ruolo_id)
      INTO v_ids
      FROM config.user_emittenti_fiscali uef
      JOIN anagrafiche.emittenti_fiscali ef
        ON ef.id = uef.emittente_fiscale_id
     WHERE uef.auth_user_id = p_auth_user_id;

    -- NULL (whitelist vuota) = nessuna restrizione
    RETURN v_ids;
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
IS 'Mappa emittenti autorizzati a soggetto_ruolo_id per query vendite. Refactor §4.6.B.6: identita OPERATORE mancante -> [] (no access); SUPER_ADMIN -> NULL (nessuna restrizione); altrimenti whitelist (NULL se vuota).';
```

---
{% include-markdown "signature-core.md" %}
