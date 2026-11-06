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
-- Scopo: fondere due comuni (config.comuni): registra la trasformazione
--   in storico.comune_trasformazioni e ripunta sulla destinazione
--   tutto cio' che riferiva l'origine. Strumento DBA.
DECLARE
    v_chi       dbops.error_log.function_name%TYPE := 'dbops.fn_admin_merge_comune';
    v_inizio    timestamptz := clock_timestamp();   -- solo per misurare la durata
    v_ripuntati dbops.audit_log.result%TYPE;
    v_params    dbops.audit_log.params%TYPE := jsonb_build_object(
        'p_id_orig',    p_id_orig,
        'p_id_target',  p_id_target,
        'p_event_type', p_event_type,
        'p_event_date', p_event_date,
        'p_note',       p_note);
BEGIN
    IF p_id_orig IS NULL OR p_id_target IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', CASE WHEN p_id_orig IS NULL THEN 'p_id_orig' ELSE 'p_id_target' END),
            NULL::uuid,
            v_chi, 'origine e destinazione sono obbligatorie');
    END IF;
    IF p_id_orig = p_id_target THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_MERGE_ORIGINE_UGUALE_DESTINAZIONE',
            jsonb_build_object('campo', 'p_id_target', 'id', p_id_orig),
            NULL::uuid,
            p_id_orig::text);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM config.comuni c WHERE c.id = p_id_orig) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_COMUNE_NON_TROVATO',
            jsonb_build_object('campo', 'p_id_orig', 'id', p_id_orig),
            NULL::uuid,
            p_id_orig::text);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM config.comuni c WHERE c.id = p_id_target) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_COMUNE_NON_TROVATO',
            jsonb_build_object('campo', 'p_id_target', 'id', p_id_target),
            NULL::uuid,
            p_id_target::text);
    END IF;

    -- La trasformazione, nel suo registro (non e' una shadow: e' il
    -- registro delle fusioni).
    INSERT INTO storico.comune_trasformazioni(id_comune_orig, id_comune_nuovo, tipo_evento, data_evento, note)
    VALUES (p_id_orig, p_id_target, p_event_type, p_event_date, p_note);

    v_ripuntati := dbops.fn_fusione_ripunta_figlie(
        'config.comuni'::regclass, p_id_orig, p_id_target, v_chi);

    PERFORM dbops.fn_audit_log_once(
        p_function_name => v_chi,
        p_status        => 'OK',
        p_params        => v_params,
        p_rows_affected => (SELECT COALESCE(sum(v::int), 0)::int
                              FROM jsonb_each_text(v_ripuntati) AS e(k, v)),
        p_result        => jsonb_build_object('ripuntati', v_ripuntati),
        p_message       => format('Comune %s fuso in %s', p_id_orig, p_id_target),
        p_duration_ms   => floor(extract(epoch FROM clock_timestamp() - v_inizio) * 1000)::int);
END;
$function$

COMMENT ON FUNCTION dbops.fn_admin_merge_comune(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
IS 'Strumento DBA: fonde il comune p_id_orig in p_id_target (config.comuni). Registra la trasformazione in storico.comune_trasformazioni (il registro delle fusioni, non una shadow) e ripunta sulla destinazione tutte le tabelle che riferivano l''origine, lette dal catalogo (dbops.fn_fusione_ripunta_figlie): stradario, codici postali, indirizzi, soggetti, aree di fatturazione e ogni FK che verra''. Se due righe diventerebbero uguali si ferma prima di scrivere, con E_MERGE_RIGHE_DOPPIE e l''elenco dei doppi: per lo stradario, la stessa via viva presente nei due comuni, che si risolve fondendo prima le due vie (una via soppressa e'' fuori dalla chiave unica delle vie e si sposta con le altre). Rifiuta con E_MERGE_ORIGINE_UGUALE_DESTINAZIONE, E_COMUNE_NON_TROVATO ed E_DBOPS_CHIAMATA_NON_VALIDA. Scrive una riga di dbops.audit_log con le righe ripuntate per tabella e la durata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
