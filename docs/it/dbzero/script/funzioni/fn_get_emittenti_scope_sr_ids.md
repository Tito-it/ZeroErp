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
    v_pk_ids bigint[];
    v_sr_ids bigint[];
BEGIN
    -- 1. Delega tutti i guard alla fn canonica _pk_ids.
    v_pk_ids := script.fn_get_emittenti_scope_pk_ids(p_auth_user_id);

    -- 2. Pass-through dei sentinel.
    IF v_pk_ids IS NULL THEN
        -- Super admin: nessuna restrizione.
        RETURN NULL;
    END IF;

    IF cardinality(v_pk_ids) = 0 THEN
        -- No identita OPERATORE attiva: nessun accesso.
        RETURN '{}'::bigint[];
    END IF;

    -- 3. Mappatura PK -> SR id via JOIN su emittenti_fiscali.
    SELECT array_agg(ef.soggetto_ruolo_id)
      INTO v_sr_ids
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = ANY(v_pk_ids);

    RETURN v_sr_ids;
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
IS 'Wrapper su fn_get_emittenti_scope_pk_ids (refactor 2026-05-02). Mappa PK reali -> soggetto_ruolo_id per query su colonne <ruolo>_soggetto_ruolo_id (fatture, ordini, commesse, listini, BA scope, search universale). Semantica: NULL=tutto, ''{}''=nessuno, array=whitelist. Single source of truth dei guard nella fn _pk_ids. Vedi guida soggetti-e-ruoli §5b per quando usare _sr_ids vs _pk_ids.';
```

---
{% include-markdown "signature-core.md" %}
