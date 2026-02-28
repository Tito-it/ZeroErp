{% include-markdown "it/dbzero/vendite/manual/fn_log_event.md" %}
# ⚙️ Funzione `fn_log_event`

```sql
CREATE FUNCTION fn_log_event(p_domain text, p_entity_type text, p_entity_id bigint, p_event_code text, p_severity text, p_correlation_id uuid, p_actor text, p_source text, p_payload jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_event(p_domain text, p_entity_type text, p_entity_id bigint, p_event_code text, p_severity text DEFAULT 'INFO'::text, p_correlation_id uuid DEFAULT NULL::uuid, p_actor text DEFAULT NULL::text, p_source text DEFAULT NULL::text, p_payload jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_event_id vendite.event_log.id%TYPE;
  v_severity vendite.event_log.severity%TYPE;
  v_payload vendite.event_log.payload%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Inserire un evento append-only in vendite.event_log
  --   e restituire l'identificativo generato.
  --
  -- Regole:
  --   - nessuna logica di orchestrazione interna
  --   - validazioni di severita` delegate a CHECK su tabella
  -- =========================================================
  v_severity := COALESCE(p_severity, 'INFO');
  v_payload := COALESCE(p_payload, '{}'::jsonb);

  INSERT INTO vendite.event_log (
    domain,
    entity_type,
    entity_id,
    event_code,
    severity,
    correlation_id,
    actor,
    source,
    payload
  )
  VALUES (
    p_domain,
    p_entity_type,
    p_entity_id,
    p_event_code,
    v_severity,
    p_correlation_id,
    p_actor,
    p_source,
    v_payload
  )
  RETURNING id INTO v_event_id;

  RETURN v_event_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_log_event(p_domain text, p_entity_type text, p_entity_id bigint, p_event_code text, p_severity text, p_correlation_id uuid, p_actor text, p_source text, p_payload jsonb)
IS 'Inserisce un evento append-only in vendite.event_log e ritorna id evento.';
```

---
{% include-markdown "signature-core.md" %}
