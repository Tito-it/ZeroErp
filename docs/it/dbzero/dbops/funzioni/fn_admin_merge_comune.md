{% include-markdown "it/dbzero/dbops/manual/fn_admin_merge_comune.md" %}
# ⚙️ Funzione `fn_admin_merge_comune`

```sql
CREATE FUNCTION fn_admin_merge_comune(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_admin_merge_comune(p_id_orig integer, p_id_target integer, p_event_type character DEFAULT 'F'::bpchar, p_event_date date DEFAULT CURRENT_DATE, p_note text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_audit_id  BIGINT;
  v_start_ts  TIMESTAMPTZ := clock_timestamp();
BEGIN
  -- Audit log: inserimento iniziale
  INSERT INTO dbops.audit_log(function_name, params, status)
  VALUES(
    'admin_merge_comune',
    json_build_object(
      'p_id_orig', p_id_orig,
      'p_id_target', p_id_target,
      'p_event_type', p_event_type,
      'p_event_date', p_event_date,
      'p_note', p_note
    ),
    'STARTED'
  ) RETURNING id INTO v_audit_id;

  -- Validazioni
  IF p_id_orig = p_id_target THEN
    RAISE EXCEPTION 'Origine e destinazione devono differire';
  END IF;
  PERFORM 1 FROM config.comuni WHERE id = p_id_orig;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Comune % non trovato', p_id_orig;
  END IF;
  PERFORM 1 FROM config.comuni WHERE id = p_id_target;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Comune % non trovato', p_id_target;
  END IF;

  -- Inserimento in storico.comune_trasformazioni
  INSERT INTO storico.comune_trasformazioni(
    id_comune_orig,
    id_comune_nuovo,
    tipo_evento,
    data_evento,
    note
  ) VALUES (
    p_id_orig,
    p_id_target,
    p_event_type,
    p_event_date,
    p_note
  );

  -- Propagazione su config.stradario
  UPDATE config.stradario
     SET comune_id = p_id_target
   WHERE comune_id = p_id_orig;

  -- Audit log: success
  UPDATE dbops.audit_log
     SET status     = 'OK',
         duration_ms = FLOOR(EXTRACT(EPOCH FROM clock_timestamp() - v_start_ts) * 1000)
   WHERE id = v_audit_id;

EXCEPTION WHEN OTHERS THEN
  -- Audit log: errore
  UPDATE dbops.audit_log
     SET status     = 'ERROR',
         message    = SQLERRM,
         duration_ms = FLOOR(EXTRACT(EPOCH FROM clock_timestamp() - v_start_ts) * 1000)
   WHERE id = v_audit_id;
  RAISE;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
