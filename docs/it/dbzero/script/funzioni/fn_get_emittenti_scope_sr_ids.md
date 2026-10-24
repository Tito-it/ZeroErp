{% include-markdown "it/dbzero/script/manual/fn_get_emittenti_scope_sr_ids.md" %}
# ⚙️ Funzione `fn_get_emittenti_scope_sr_ids`

```sql
CREATE FUNCTION fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
 RETURNS bigint[]
 LANGUAGE plpgsql
 STABLE COST 5000
AS $function$
DECLARE
    v_pk_ids bigint[];
    v_sr_ids bigint[];
BEGIN
    -- 1. Delega tutti i guard alla fn canonica _pk_ids
    --    (compresa l'intersezione con l'emittente attivo).
    v_pk_ids := script.fn_get_emittenti_scope_pk_ids(p_auth_user_id);

    -- 2. Pass-through dei sentinel.
    IF v_pk_ids IS NULL THEN
        -- Nessuna restrizione.
        RETURN NULL;
    END IF;

    IF cardinality(v_pk_ids) = 0 THEN
        -- No identita OPERATORE attiva, oppure emittente attivo
        -- fuori dalla whitelist: nessun accesso.
        RETURN '{}'::bigint[];
    END IF;

    -- 3. Mappatura PK -> SR id via JOIN su emittenti_fiscali.
    --    coalesce OBBLIGATORIO: array_agg su zero righe ritorna
    --    NULL, che qui significherebbe "vede tutto". Prima dei PK
    --    provenienti dalla GUC il caso era irraggiungibile (FK su
    --    user_emittenti_fiscali); ora un id inesistente
    --    allargherebbe invece di restringere. Fail-closed.
    SELECT coalesce(array_agg(ef.soggetto_ruolo_id), '{}'::bigint[])
      INTO v_sr_ids
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = ANY(v_pk_ids);

    RETURN v_sr_ids;
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
IS '⭐ rev 2026-10-18 (20261018-51, D-3b-2 ondata 2): COST 5000. Legge tabelle ed e'' nominata dalle policy ef_whitelist del billing account (20261018-50). Wrapper su fn_get_emittenti_scope_pk_ids (refactor 2026-05-02). Mappa PK reali -> soggetto_ruolo_id per query su colonne <ruolo>_soggetto_ruolo_id (fatture, ordini, commesse, listini, BA scope, search universale). Semantica: NULL=tutto, ''{}''=nessuno, array=whitelist. Single source of truth dei guard nella fn _pk_ids. Post 2026-08-04: mappatura a vuoto -> ''{}'' e non NULL (fail-closed su emittente attivo inesistente). Vedi guida soggetti-e-ruoli §5b per quando usare _sr_ids vs _pk_ids.';
```

</div>

---
{% include-markdown "signature-core.md" %}
