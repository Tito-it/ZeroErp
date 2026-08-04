# ⚙️ Funzione `fn_admin_merge_stradario`

```sql
CREATE FUNCTION fn_admin_merge_stradario(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_admin_merge_stradario(p_id_orig integer, p_id_target integer, p_event_type character DEFAULT 'F'::bpchar, p_event_date date DEFAULT CURRENT_DATE, p_note text DEFAULT NULL::text)
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
    'admin_merge_stradario',
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
  PERFORM 1 FROM config.stradario WHERE id = p_id_orig;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Stradario % non trovato', p_id_orig;
  END IF;
  PERFORM 1 FROM config.stradario WHERE id = p_id_target;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Stradario % non trovato', p_id_target;
  END IF;

  -- Inserimento in storico.stradario_trasformazioni
  --
  -- rev 2026-08-04 (bonifica riferimenti morti, F2): due difetti, e il
  --   secondo era invisibile al controllo.
  --   1) I nomi: le colonne sono `via_id_orig` / `via_id_nuovo`, non
  --      `id_comune_orig` / `id_comune_nuovo`.
  --   2) ⚠️ I VALORI: si scriveva il `comune_id` delle due righe di
  --      stradario. Ma questa funzione fonde due **vie** — sposta
  --      anagrafiche.indirizzi_dettaglio.stradario_id da p_id_orig a
  --      p_id_target — e il comune non e' cio' che si sta trasformando.
  --      Riparare solo i nomi avrebbe prodotto record che dicono «la via 12
  --      e' diventata la via 47» riportando due id di comune: una
  --      trasformazione falsa, per giunta credibile. Si registrano gli id
  --      di stradario, gli stessi su cui agisce la UPDATE qui sotto.
  INSERT INTO storico.stradario_trasformazioni(
    via_id_orig,
    via_id_nuovo,
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

  -- Propagazione su indirizzi_dettaglio
  UPDATE anagrafiche.indirizzi_dettaglio
     SET stradario_id = p_id_target
   WHERE stradario_id = p_id_orig;

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
