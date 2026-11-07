{% include-markdown "it/dbzero/dbops/manual/fn_admin_merge_stradario.md" %}
# ⚙️ Funzione `fn_admin_merge_stradario`

```sql
CREATE FUNCTION fn_admin_merge_stradario(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_admin_merge_stradario(p_id_orig integer, p_id_target integer, p_event_type character DEFAULT 'F'::bpchar, p_event_date date DEFAULT script.fn_data_operativa(), p_note text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: fondere due vie (config.stradario): registra la trasformazione
--   in storico.stradario_trasformazioni e ripunta sulla destinazione
--   tutto cio' che riferiva l'origine. Strumento DBA.
DECLARE
    v_chi          dbops.error_log.function_name%TYPE := 'dbops.fn_admin_merge_stradario';
    v_inizio       timestamptz := clock_timestamp();   -- solo per misurare la durata
    v_manutenzione text;                               -- un parametro di sessione, non una colonna
    v_ripuntati    dbops.audit_log.result%TYPE;
    v_soppressa_id  config.stradario.id%TYPE;
    v_soppressa_dal config.stradario.obsoleto_dal%TYPE;
    v_params       dbops.audit_log.params%TYPE := jsonb_build_object(
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
    IF NOT EXISTS (SELECT 1 FROM config.stradario s WHERE s.id = p_id_orig) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_STRADARIO_NON_TROVATO',
            jsonb_build_object('campo', 'p_id_orig', 'id', p_id_orig),
            NULL::uuid,
            p_id_orig::text);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM config.stradario s WHERE s.id = p_id_target) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_STRADARIO_NON_TROVATO',
            jsonb_build_object('campo', 'p_id_target', 'id', p_id_target),
            NULL::uuid,
            p_id_target::text);
    END IF;

    -- Una via soppressa non si fonde piu' (Q16): ne' come origine
    -- ne' come destinazione.
    SELECT s.id, s.obsoleto_dal
      INTO v_soppressa_id, v_soppressa_dal
      FROM config.stradario s
     WHERE s.id IN (p_id_orig, p_id_target)
       AND s.obsoleto_dal IS NOT NULL
     ORDER BY s.id = p_id_orig DESC
     LIMIT 1;
    IF v_soppressa_id IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_STRADARIO_SOPPRESSO',
            jsonb_build_object('campo', CASE WHEN v_soppressa_id = p_id_orig THEN 'p_id_orig' ELSE 'p_id_target' END,
                               'id', v_soppressa_id,
                               'obsoleto_dal', v_soppressa_dal),
            NULL::uuid,
            v_soppressa_id::text, to_char(v_soppressa_dal, 'DD/MM/YYYY'));
    END IF;

    -- La trasformazione, nel suo registro (non e' una shadow: e' il
    -- registro delle fusioni).
    INSERT INTO storico.stradario_trasformazioni(via_id_orig, via_id_nuovo, tipo_evento, data_evento, note)
    VALUES (p_id_orig, p_id_target, p_event_type, p_event_date, p_note);

    -- La porta degli indirizzi, aperta solo per il ripuntamento e
    -- richiusa al valore di prima. Se il ripuntamento solleva, il
    -- parametro torna da solo al valore di prima con l'annullamento.
    v_manutenzione := current_setting('zeroerp.maintenance_indirizzi_dettaglio', true);
    PERFORM set_config('zeroerp.maintenance_indirizzi_dettaglio', 'on', true);

    v_ripuntati := dbops.fn_fusione_ripunta_figlie(
        'config.stradario'::regclass, p_id_orig, p_id_target, v_chi);

    PERFORM set_config('zeroerp.maintenance_indirizzi_dettaglio',
                       COALESCE(v_manutenzione, ''), true);

    -- La via d'origine resta, soppressa (Q16): ora nessuno la riferisce.
    UPDATE config.stradario s
       SET obsoleto_dal = LEAST(p_event_date, script.fn_data_operativa())
     WHERE s.id = p_id_orig;

    PERFORM dbops.fn_audit_log_once(
        p_function_name => v_chi,
        p_status        => 'OK',
        p_params        => v_params,
        p_rows_affected => (SELECT COALESCE(sum(v::int), 0)::int
                              FROM jsonb_each_text(v_ripuntati) AS e(k, v)),
        p_result        => jsonb_build_object('ripuntati', v_ripuntati),
        p_message       => format('Via %s fusa in %s', p_id_orig, p_id_target),
        p_duration_ms   => floor(extract(epoch FROM clock_timestamp() - v_inizio) * 1000)::int);
END;
$function$

COMMENT ON FUNCTION dbops.fn_admin_merge_stradario(p_id_orig integer, p_id_target integer, p_event_type character, p_event_date date, p_note text)
IS 'Strumento DBA: fonde la via p_id_orig in p_id_target (config.stradario). Registra la trasformazione in storico.stradario_trasformazioni (il registro delle fusioni, non una shadow) e ripunta sulla destinazione tutte le tabelle che riferivano l''origine, lette dal catalogo (dbops.fn_fusione_ripunta_figlie). Per gli indirizzi (anagrafiche.indirizzi_dettaglio) apre la porta zeroerp.maintenance_indirizzi_dettaglio solo attorno al ripuntamento e la richiude subito dopo. Poi segna la via d''origine come soppressa (obsoleto_dal, con la data dell''evento e mai oltre la data operativa): resta, come radice della catena delle trasformazioni, ma non si sceglie piu'' per il nuovo. Una via gia'' soppressa non si fonde, ne'' come origine ne'' come destinazione (E_STRADARIO_SOPPRESSO). Se due righe diventerebbero uguali si ferma prima di scrivere, con E_MERGE_RIGHE_DOPPIE e l''elenco dei doppi: nessuna unione automatica. Rifiuta anche con E_MERGE_ORIGINE_UGUALE_DESTINAZIONE, E_STRADARIO_NON_TROVATO ed E_DBOPS_CHIAMATA_NON_VALIDA. Scrive una riga di dbops.audit_log con le righe ripuntate per tabella e la durata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
