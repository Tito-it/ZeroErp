{% include-markdown "it/dbzero/vendite/manual/fn_log_event.md" %}
# ⚙️ Funzione `fn_log_event`

```sql
CREATE FUNCTION fn_log_event(p_entity_type text, p_entity_id bigint, p_event_code text, p_severity text, p_correlation_id uuid, p_payload jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_event(p_entity_type text, p_entity_id bigint, p_event_code text, p_severity text DEFAULT 'INFO'::text, p_correlation_id uuid DEFAULT NULL::uuid, p_payload jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_event_id vendite.event_log.id%TYPE;
    v_severity vendite.event_log.severity%TYPE;
    v_payload  vendite.event_log.payload%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Inserire un evento append-only in vendite.event_log
    --   e restituire l'identificativo generato.
    --
    -- Regole:
    --   - nessuna logica di orchestrazione interna
    --   - validazioni di severita' delegate al CHECK su tabella
    --   - ⭐ PERIMETRO, CHI e SCADENZA non si passano: li scrive
    --     trg_event_log_a10_deriva_scope_ins, perche' sono fatti
    --     che il database conosce e il chiamante no.
    --   - ⭐ E nemmeno il DOMINIO: e' una proprieta' del codice
    --     evento (config.eventi_dominio). Chiederlo al chiamante
    --     vorrebbe dire permettergli di scriverne uno diverso da
    --     quello del codice, cioe' due verita'.
    --
    -- ⚠️ Rev 2026-08-22 (L4): via p_domain, e la colonna con lui.
    --   Rev precedente (L1): via p_actor e p_source, che
    --   riempivano due colonne costanti — «chi» e' user_insert.
    -- =========================================================
    v_severity := COALESCE(p_severity, 'INFO');
    v_payload  := COALESCE(p_payload, '{}'::jsonb);

    INSERT INTO vendite.event_log (
        entity_type,
        entity_id,
        event_code,
        severity,
        correlation_id,
        payload
    )
    VALUES (
        p_entity_type,
        p_entity_id,
        p_event_code,
        v_severity,
        p_correlation_id,
        v_payload
    )
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_log_event(p_entity_type text, p_entity_id bigint, p_event_code text, p_severity text, p_correlation_id uuid, p_payload jsonb)
IS 'Inserisce un evento append-only in vendite.event_log e ritorna id evento. ⭐ Perimetro (emittente_soggetto_ruolo_id), identita'' (auth_user_id) e scadenza (cleanup_at) NON sono parametri: li deriva trg_event_log_a10_deriva_scope_ins, perche'' sono fatti del database. ⭐ E nemmeno il DOMINIO: e'' una proprieta'' del codice evento e vive in config.eventi_dominio — chiederlo al chiamante gli permetterebbe di scriverne uno diverso da quello del codice, cioe'' due verita''. ⚠️ Rev 2026-08-22 (L4): tolto p_domain, sei parametri. Rev precedente dello stesso giorno (L1): tolti p_actor e p_source. Entrambe le volte la firma vecchia e'' stata DROPpata esplicitamente: con i DEFAULT due firme rendono ambigua ogni chiamata. ⭐ §9.4 del brief dichiara questa come la forma FINALE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
