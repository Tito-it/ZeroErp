{% include-markdown "it/dbzero/dbops/manual/fn_admin_merge_comune.md" %}
# ⚙️ Funzione `fn_admin_merge_comune`

```sql
CREATE FUNCTION fn_admin_merge_comune(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_admin_merge_comune(p_id_orig integer, p_id_target integer, p_event_type character DEFAULT 'F'::bpchar, p_event_date date DEFAULT script.fn_data_operativa(), p_note text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: fondere due comuni (config.comuni): registra la trasformazione in
--   storico.comune_trasformazioni e ripunta chi riferiva l'origine sulla
--   destinazione. Strumento DBA.
--
-- rev 2026-09-12 (brief-db-rls-storico-scope-congelato §4d, decisione a): il
--   registro dbops.audit_log si scrive dalla PORTA fn_audit_log_once, una volta
--   a fine lavoro, come le altre funzioni di dbops. Prima: INSERT diretto con
--   status 'STARTED' — che chk_audit_status NON ammette, quindi la funzione
--   falliva alla prima riga — e UPDATE di chiusura, che l'applicazione non puo'
--   piu' fare (REVOKE del 2026-09-11) e che nel ramo ERROR veniva comunque
--   annullato dal RAISE. Il ramo ERROR resta per la scrittura fuori transazione
--   (dblink), dove ha senso; in transazione si annulla col resto, com'era.
DECLARE
  v_start_ts  timestamptz := clock_timestamp();
  v_ripuntati integer := 0;
  v_params    jsonb := jsonb_build_object(
      'p_id_orig',    p_id_orig,
      'p_id_target',  p_id_target,
      'p_event_type', p_event_type,
      'p_event_date', p_event_date,
      'p_note',       p_note);
BEGIN
  -- Validazioni. ⚠️ Messaggi in chiaro, senza codice registrato: e' uno
  -- strumento DBA che oggi nessuno chiama dall'applicazione. Quando lo fara',
  -- i tre motivi vanno a catalogo (debito registrato nel brief).
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

  -- La trasformazione, nel suo registro (non e' una shadow: e' il registro
  -- delle fusioni, letto da script.fn_get_vie_discendenti).
  INSERT INTO storico.comune_trasformazioni(id_comune_orig, id_comune_nuovo, tipo_evento, data_evento, note)
  VALUES (p_id_orig, p_id_target, p_event_type, p_event_date, p_note);

  -- Propagazione: chi riferiva l'origine ora riferisce la destinazione.
  UPDATE config.stradario
     SET comune_id = p_id_target
   WHERE comune_id = p_id_orig;
  GET DIAGNOSTICS v_ripuntati = ROW_COUNT;

  -- Audit dalla porta, una volta, con esito e conteggi.
  PERFORM dbops.fn_audit_log_once(
    p_function_name => 'fn_admin_merge_comune',
    p_status        => 'OK',
    p_params        => v_params,
    p_rows_affected => v_ripuntati,
    p_result        => jsonb_build_object('stradario_ripuntati', v_ripuntati,
                                          'duration_ms', floor(extract(epoch from clock_timestamp() - v_start_ts) * 1000)),
    p_message       => format('Comune %s fuso in %s', p_id_orig, p_id_target));
EXCEPTION WHEN OTHERS THEN
  -- In transazione questa riga si annulla col RAISE, com'era gia'; con il
  -- canale dblink acceso sopravvive, ed e' l'unico caso in cui serve.
  PERFORM dbops.fn_audit_log_once(
    p_function_name => 'fn_admin_merge_comune',
    p_status        => 'ERROR',
    p_params        => v_params,
    p_message       => SQLERRM,
    p_sqlstate      => SQLSTATE);
  RAISE;
END;
$function$

COMMENT ON FUNCTION dbops.fn_admin_merge_comune(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
IS 'Strumento DBA: fonde due comuni di config.comuni — registra la trasformazione in storico.comune_trasformazioni (il registro delle fusioni, non una shadow) e ripunta sulla destinazione chi riferiva l''origine. Rev 2026-09-12: l''audit si scrive dalla porta dbops.fn_audit_log_once, una volta a fine lavoro (prima: INSERT con status STARTED, non ammesso dal CHECK, e UPDATE di chiusura che l''app non puo'' piu'' fare). Le validazioni sollevano ancora messaggi in chiaro senza codice registrato: debito dichiarato, da saldare quando la funzione sara'' chiamata dall''applicazione. Brief: brief-db-rls-storico-scope-congelato §4d.';
```

</div>

---
{% include-markdown "signature-core.md" %}
