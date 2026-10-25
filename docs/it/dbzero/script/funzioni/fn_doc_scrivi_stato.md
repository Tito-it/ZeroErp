{% include-markdown "it/dbzero/script/manual/fn_doc_scrivi_stato.md" %}
# ⚙️ Funzione `fn_doc_scrivi_stato`

```sql
CREATE FUNCTION fn_doc_scrivi_stato(p_testata regclass, p_id bigint, p_stato_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_scrivi_stato(p_testata regclass, p_id bigint, p_stato_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Uso, nel verbo DEFINER, dopo la prima riga (script.fn_guard_passaggio):
--   PERFORM script.fn_doc_scrivi_stato('vendite.ddt', p_ddt_id, v_stato_a_id);
DECLARE
    -- Testata, id e stato di uno qualunque dei documenti della
    -- mappa: bigint in tutti, nessuna colonna comune a cui
    -- ancorarli. Colonna e porta sono testo.
    v_col   text;
    v_porta text;
    v_prima text;
    v_n     integer;   -- righe toccate (ROW_COUNT): un conteggio
BEGIN
    SELECT m.colonna_stato INTO v_col
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_col IS NULL OR p_id IS NULL OR p_id <= 0 OR p_stato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_scrivi_stato', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text, 'id', p_id,
                               'stato_id', p_stato_id),
            NULL::uuid,
            'script.fn_doc_scrivi_stato',
            'p_testata (una testata della mappa del modello), p_id (maggiore di zero), p_stato_id (obbligatorio)');
    END IF;

    -- La porta per QUESTA testata e QUESTO documento: l'oid, non il
    -- nome, che dipende dal search_path di chi lo stampa.
    v_porta := p_testata::oid::text || ':' || p_id::text;
    v_prima := current_setting('zeroerp.doc_cambio_stato', true);
    PERFORM set_config('zeroerp.doc_cambio_stato', v_porta, true);

    EXECUTE format('UPDATE %s t SET %I = $1 WHERE t.id = $2', p_testata, v_col)
      USING p_stato_id, p_id;
    GET DIAGNOSTICS v_n = ROW_COUNT;

    PERFORM set_config('zeroerp.doc_cambio_stato', COALESCE(v_prima, ''), true);

    IF v_n <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_scrivi_stato', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text, 'id', p_id,
                               'stato_id', p_stato_id, 'righe', v_n),
            NULL::uuid,
            'script.fn_doc_scrivi_stato',
            'p_id: un documento esistente, preso FOR UPDATE dal verbo');
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_scrivi_stato(p_testata regclass, p_id bigint, p_stato_id bigint)
IS 'BB del modello del documento, seconda meta'' del verbo di stato: scrive lo stato di un documento attraverso la porta. Apre la porta per QUESTA testata e QUESTO documento (GUC transazionale zeroerp.doc_cambio_stato = ''<oid testata>:<id>''), fa l''UPDATE della colonna di stato della mappa (script.fn_doc_stato_modello) con tutti i guard di sempre, e rimette la GUC com''era (un verbo che cambia due documenti non lascia aperta la porta del primo). SECURITY INVOKER: la porta (script.trgfn_doc_stato_solo_dal_verbo) chiede anche che chi esegue sia il proprietario della tabella, quindi passa da un verbo DEFINER e si ferma se la chiama l''applicazione. Il permesso lo controlla prima la prima meta'', script.fn_guard_passaggio; i passaggi di processo (manuale = false) li scrive il verbo che ne e'' la causa, con questa sola. Testata fuori mappa, id o stato mancanti, nessuna riga toccata: E_SCRIPT_CHIAMATA_NON_VALIDA. Brief: brief-modello-documento-vendita §7 (S-1, S-2, Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
