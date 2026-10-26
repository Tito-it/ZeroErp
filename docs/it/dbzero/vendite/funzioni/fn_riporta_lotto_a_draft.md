{% include-markdown "it/dbzero/vendite/manual/fn_riporta_lotto_a_draft.md" %}
# ⚙️ Funzione `fn_riporta_lotto_a_draft`

```sql
CREATE FUNCTION fn_riporta_lotto_a_draft(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer, riemesse_attivita integer, annullati_task_run integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: rollback di un lotto PRE-FISCALE verso DRAFT — delega la
--        pulizia alla primitiva, azzera lo STATO DI ESECUZIONE del
--        lotto (task_run ad ANNULLATO), lo marca come riaperto e
--        REGISTRA L'ATTO NEL GIORNALE.
--        Il lotto resta vivo e ripartira' dallo step DRAFT.
-- Perimetro (RD-1): si torna indietro per QUALSIASI motivo.
--        MASSIVO **e** GIORNALIERO, su lotti DRAFT o EMESSA.
-- RD-4:  il ripristino delle TABELLE non si scrive qui, e' della
--        primitiva. Qui vive lo stato del LOTTO — stato fiscale,
--        stato operativo, riaperto_il e stato di esecuzione.
-- RD-6:  🔴 i task_run si chiudono ad ANNULLATO, altrimenti
--        fn_resolve_lotto_task_execution_mode li vede COMPLETATO e
--        risponde SKIP: il lotto riaperto rilancia A VUOTO.
-- RD-7 (rev 2026-08-31): 🔴 l'atto entra in vendite.event_log.
--        Prima si leggeva solo DI RIMBALZO dai task_run ANNULLATO.
-- rev 2026-08-04: le precondizioni NON si scrivono piu' qui.
--        Arrivano da script.fn_check_lotto_riportabile_a_draft, la
--        stessa che alimenta enabled/reasons di
--        script.fn_available_actions_lotto.
DECLARE
    v_lock_batch_id        vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_draft_id             config.stati_doc_fiscale.id%TYPE;
    v_stato_precedente     config.stati_doc_fiscale.codice_interno%TYPE;
    v_motivi               jsonb;
    v_fatture_ids          BIGINT[];
    v_updated_lotti        INTEGER := 0;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
    v_riemesse_attivita    INTEGER := 0;
    v_annullati_task_run   INTEGER := 0;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- PRECONDIZIONI — sede unica. Il check verifica anche
    -- l'esistenza del lotto (E_LOTTO_NON_TROVATO) e solleva il
    -- codice del PRIMO motivo; il context porta l'elenco completo.
    -- ⚠️ Fra i motivi c'e' il guard sul NUMERO della fattura, che
    -- e' ridondante rispetto allo stato e va tenuto lo stesso: il
    -- danno sarebbe irreversibile, quindi si guarda il fatto e non
    -- lo stato che dovrebbe implicarlo.
    v_motivi := script.fn_check_lotto_riportabile_a_draft(p_lotto_id);
    IF jsonb_array_length(v_motivi) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_riporta_lotto_a_draft',
            v_motivi -> 0 ->> 'codice',
            jsonb_build_object('lotto_id', p_lotto_id, 'motivi', v_motivi),
            NULL::uuid,
            v_motivi -> 0 ->> 'dettaglio');
    END IF;

    -- ⭐ RD-7: si legge anche DA DOVE il lotto sta tornando, ed e'
    -- l'unico fatto che dopo l'UPDATE non sarebbe piu' ricostruibile
    -- (riaperto_il dice QUANDO, non DA QUALE stato).
    -- ⚠️ LEFT JOIN e non INNER: fatturazione_lotti.stato_doc_fiscale_id
    -- e' NULLABLE, e un INNER qui non tornerebbe righe azzerando
    -- anche v_lock_batch_id.
    SELECT fl.lock_batch_id, sdf.codice_interno
      INTO v_lock_batch_id, v_stato_precedente
      FROM vendite.fatturazione_lotti fl
      LEFT JOIN config.stati_doc_fiscale sdf ON sdf.id = fl.stato_doc_fiscale_id
     WHERE fl.id = p_lotto_id;

    SELECT s.id INTO v_draft_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1;
    IF v_draft_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'DRAFT'), NULL::uuid, 'stato DRAFT non configurato');
    END IF;

    SELECT array_agg(lf.fattura_id) INTO v_fatture_ids
      FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = p_lotto_id;
    IF v_fatture_ids IS NULL THEN v_fatture_ids := ARRAY[]::BIGINT[]; END IF;

    -- Concorrenza (punto E): dopo TUTTE le guard, com'e' convenzione —
    -- una chiamata invalida non deve serializzare gli altri. Forma a
    -- DUE argomenti, entrambi int4 (unico overload a due esistente):
    -- la chiave passa da hashtext e non da un cast, che esploderebbe
    -- oltre i 2 miliardi.
    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.fn_riporta_lotto_a_draft'),
        hashtext(p_lotto_id::text)
    );

    -- Pulizia: tutta della primitiva (RD-4). Il lock_batch_id SI passa,
    -- perche' e' un reset GLOBALE del lotto — e' il per-fattura che deve
    -- passare NULL (C-22).
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita, c.riemesse_attivita
      INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita, v_riemesse_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(v_fatture_ids, v_lock_batch_id) AS c;

    -- 🔴 RD-6 — lo stato di esecuzione del lotto.
    -- fn_resolve_lotto_task_execution_mode legge l'ULTIMO task_run per
    -- (lotto, task, stato_doc): COMPLETATO -> SKIP, ANNULLATO -> RUN.
    -- Senza questo passo il lotto riaperto rilancia e i task vengono
    -- saltati tutti, in silenzio: nessun errore, nessun task_run nuovo,
    -- e il giro sembra riuscito.
    -- ⚠️ NON basta `attivo = false`: quella SELECT non filtra su
    -- `attivo`. La leva e' l'ESITO, e la funzione per scriverlo esiste
    -- gia' — non si inventa un meccanismo nuovo.
    -- ⚠️ Si annullano le corse di TUTTI gli step, non solo di DRAFT: il
    -- lotto risalira' l'intera catena, e la pulizia ha cancellato tutto
    -- cio' che quelle corse avevano prodotto — nessuna deve piu' avere
    -- voce sul giro successivo.
    WITH da_annullare AS (
      SELECT r.id
        FROM vendite.fatturazione_lotti_task_runs r
       WHERE r.lotto_id = p_lotto_id
         AND r.attivo IS TRUE
         AND r.task_stato IS DISTINCT FROM 'ANNULLATO'
    ), annullati AS (
      SELECT vendite.fn_cancel_lotto_task_run(
               d.id,
               jsonb_build_object('motivo', 'ritorno_a_draft', 'lotto_id', p_lotto_id)
             )
        FROM da_annullare d
    )
    SELECT count(*)::INTEGER INTO v_annullati_task_run FROM annullati;

    -- stato_operativo torna APERTO: il lotto ha di nuovo lavoro da
    -- fare. stato_lotto NON si tocca — ha una macchina a stati cablata
    -- in Python e da COMPLETATO come da ERRORE l'unica transizione
    -- ammessa e' verso IN_ESECUZIONE, che e' quello che fara' il giro
    -- successivo.
    UPDATE vendite.fatturazione_lotti
       SET stato_doc_fiscale_id = v_draft_id,
           stato_operativo      = 'APERTO',
           riaperto_il          = now(),
           data_update          = now(),
           user_update          = current_user
     WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    -- 🔴 RD-7 — l'atto entra nel GIORNALE, e ci entra QUI: dopo
    -- l'UPDATE, perche' solo adesso i contatori sono definitivi.
    -- ⭐ Il payload porta i numeri, e sono la ragione della riga:
    -- «riaperto» da solo e' deducibile dai task_run ANNULLATO,
    -- «riaperto, e ha cancellato N fatture e M righe» no.
    -- ⚠️ severity WARN, non INFO: vw_giornale_entita mappa gia'
    -- TASK_RUN ANNULLATO -> WARN, e la causa non puo' stare piu' in
    -- basso del proprio effetto, o chi filtra per gravita' vede il
    -- sintomo senza il motivo.
    -- ⚠️ Non introduce un ramo di fallimento: il trigger di scope
    -- deriva l'emittente da fatturazione_lotti, dove la colonna e'
    -- NOT NULL, e l'esistenza del lotto e' gia' garantita sopra.
    -- ⚠️ correlation_id resta NULL: la riapertura e' un atto
    -- dell'operatore, non un passo di un giro di pipeline — non c'e'
    -- un run a cui correlarla.
    -- ⛔ E il registro e' event_log anche per un motivo di
    -- COMPORTAMENTO, non solo di leggibilita': le segnalazioni si
    -- compongono da fatture_log UNION fatturazione_lotti_log, e da
    -- event_log si legge solo l'ancora PIPELINE_STARTED. Scrivere
    -- qui NON aggiunge una segnalazione, quindi non entra nel
    -- conteggio su cui il runner decide l'avanzamento: un atto
    -- registrato non deve diventare un atto che blocca.
    PERFORM vendite.fn_log_event(
        p_entity_type    => 'LOTTO',
        p_entity_id      => p_lotto_id,
        p_event_code     => 'LOTTO_RIAPERTO',
        p_severity       => 'WARN',
        p_correlation_id => NULL::uuid,
        p_payload        => jsonb_build_object(
            'stato_precedente',   v_stato_precedente,
            'deleted_fatture',    v_deleted_fatture,
            'deleted_righe',      v_deleted_righe,
            'updated_attivita',   v_updated_attivita,
            'riemesse_attivita',  v_riemesse_attivita,
            'annullati_task_run', v_annullati_task_run
        )
    );

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture,
                        v_deleted_righe, v_riemesse_attivita, v_annullati_task_run;
END;
$function$

COMMENT ON FUNCTION vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)
IS 'Rollback di un lotto PRE-FISCALE (DRAFT o EMESSA) verso DRAFT, per MASSIVO e GIORNALIERO. Delega TUTTA la pulizia delle tabelle a fn_cleanup_fatture_by_ids (RD-4) e si occupa dello stato del LOTTO: stato fiscale a DRAFT, stato_operativo APERTO, riaperto_il (RD-2) e stato di ESECUZIONE. 🔴 RD-6: chiude ad ANNULLATO tutti i task_run attivi del lotto, perche'' fn_resolve_lotto_task_execution_mode legge l''ultimo task_run e su COMPLETATO risponde SKIP — senza questo passo il lotto riaperto rilancia A VUOTO, senza errori e senza task_run nuovi. ⚠️ Non basterebbe attivo = false: quella SELECT non filtra su attivo. Le corse non si cancellano: si chiudono con esito, e il giro nuovo apre tentativo = MAX+1, quindi la storia resta leggibile per intero. 🔴 RD-7 (rev 2026-08-31): l''atto entra nel GIORNALE — LOTTO_RIAPERTO in vendite.event_log via fn_log_event, severity WARN, payload coi contatori e con lo stato fiscale di partenza. Prima la riapertura si leggeva solo DI RIMBALZO dai task_run passati ad ANNULLATO. Registro scelto per DUE proprieta'' strutturali che fatturazione_lotti_log non ha: append-only per trigger e codice a catalogo (li'' c''e'' disabilitato, e un atto che distrugge documenti non deve poter essere silenziato). WARN e non INFO perche'' vw_giornale_entita mappa gia'' TASK_RUN ANNULLATO -> WARN: la causa non puo'' stare piu'' in basso del proprio effetto. ⛔ Terza ragione della scelta, ed e'' di comportamento: le segnalazioni si compongono da fatture_log UNION fatturazione_lotti_log e da event_log si legge la sola ancora PIPELINE_STARTED, quindi questa riga NON entra nel conteggio su cui il runner decide l''avanzamento — un atto registrato non deve diventare un atto che blocca. ⚠️ La scrittura non introduce un ramo di fallimento: emittente_soggetto_ruolo_id e'' NOT NULL su fatturazione_lotti e l''esistenza del lotto e'' gia'' garantita dal check. RD-1: si torna indietro per QUALSIASI motivo; cio'' che resta vietato e'' numerare un documento incoerente (guard D-K). Sorella di fn_annulla_lotto_da_draft, che invece CHIUDE il lotto portandolo ad ANNULLATA. rev 2026-08-04: le precondizioni non sono piu'' scritte qui — arrivano da script.fn_check_lotto_riportabile_a_draft, la STESSA che alimenta enabled/reasons di script.fn_available_actions_lotto, cosi'' il pulsante e la funzione non possono divergere. ⚠️ Rifiuta ancora se una sola fattura e'' gia'' NUMERATA (ora E_LOTTO_FATTURE_NUMERATE): il controllo guarda il numero e non lo stato. Il pg_advisory_xact_lock resta DOPO le validazioni: una chiamata invalida non deve serializzare gli altri chiamanti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
