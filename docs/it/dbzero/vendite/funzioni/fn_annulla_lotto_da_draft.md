{% include-markdown "it/dbzero/vendite/manual/fn_annulla_lotto_da_draft.md" %}
# ⚙️ Funzione `fn_annulla_lotto_da_draft`

```sql
CREATE FUNCTION fn_annulla_lotto_da_draft(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_lotto_da_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer, annullati_task_run integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: rollback tecnico di un lotto in DRAFT — cancella le
--        fatture PRE-FISCALI (DRAFT/EMESSA), ripristina le
--        attivita' e CHIUDE il lotto portandolo ad ANNULLATA.
-- Perimetro (D-L pt.2 + D-T): vale per MASSIVO **e** GIORNALIERO.
--        Il vincolo al solo MASSIVO e' caduto quando D-T ha reso
--        lecita la transizione DRAFT->ANNULLATA per entrambi.
-- rev 2026-09-04 (brief-residuo-fatturabili-e-bandiere-esito-parziale,
--        D4): l'annullo CHIUDE anche i task run del lotto, con
--        l'esito ANNULLATO. Prima non li nominava affatto, e un
--        lotto annullato continuava a comparire fra gli «errori
--        vivi» del cruscotto: la CTE task_err di
--        vw_dash_competenza_errori prende i run in ERRORE ancora
--        attivi e NON guarda lo stato del lotto.
--        ⭐ SIMMETRIA con la sorella fn_riporta_lotto_a_draft, che
--        fa gia' esattamente questo — stessa primitiva
--        (fn_cancel_lotto_task_run), stesso esito, stesso contatore
--        di ritorno. Due sorelle non possono comportarsi
--        diversamente sulla stessa cosa.
--        ⛔ E NON con `attivo = false`, che sembra la strada ovvia:
--        la SELECT di fn_resolve_lotto_task_execution_mode non
--        filtra su `attivo`, quindi non basterebbe — e' la sorella
--        stessa a dirlo nel proprio corpo. Inoltre `attivo` risponde
--        gia' a «questo e' il tentativo valido»: caricarlo anche di
--        «il lotto non e' piu' in lavorazione» sono due domande su
--        un flag solo, e il giorno che dissentono non c'e' scritto
--        da nessuna parte quale vince.
--        ⚠️ La vista non si tocca: i run cadono da soli, PER ESITO.
-- rev 2026-08-04: le precondizioni NON si scrivono piu' qui.
--        Arrivano da script.fn_check_lotto_annullabile, la stessa
--        che alimenta enabled/reasons di
--        script.fn_available_actions_lotto. Il pulsante e la
--        funzione non possono piu' divergere.
DECLARE
    v_lock_batch_id        vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_annullata_id         config.stati_doc_fiscale.id%TYPE;
    v_motivi               jsonb;
    v_fatture_ids          BIGINT[];
    v_updated_lotti        INTEGER := 0;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
    v_annullati_task_run   INTEGER := 0;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_annulla_lotto_da_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- PRECONDIZIONI — sede unica. Il check verifica anche
    -- l'esistenza del lotto (E_LOTTO_NON_TROVATO) e solleva
    -- il codice del PRIMO motivo; il context porta l'elenco
    -- completo, cosi' il BE puo' mostrarli tutti.
    v_motivi := script.fn_check_lotto_annullabile(p_lotto_id);
    IF jsonb_array_length(v_motivi) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_annulla_lotto_da_draft',
            v_motivi -> 0 ->> 'codice',
            jsonb_build_object('lotto_id', p_lotto_id, 'motivi', v_motivi),
            NULL::uuid,
            v_motivi -> 0 ->> 'dettaglio');
    END IF;

    SELECT fl.lock_batch_id
      INTO v_lock_batch_id
      FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;

    SELECT s.id INTO v_annullata_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'ANNULLATA' AND s.attivo IS TRUE LIMIT 1;
    IF v_annullata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_annulla_lotto_da_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'ANNULLATA'), NULL::uuid, 'stato ANNULLATA non configurato');
    END IF;

    SELECT array_agg(lf.fattura_id) INTO v_fatture_ids
      FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = p_lotto_id;
    IF v_fatture_ids IS NULL THEN v_fatture_ids := ARRAY[]::BIGINT[]; END IF;

    -- ⚠️ Qui il lock_batch_id SI passa, ed e' corretto: il reset
    -- globale deve liberare anche le attivita' agganciate al lotto
    -- che non sono mai diventate riga. E' il per-fattura che deve
    -- passare NULL (C-22).
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(v_fatture_ids, v_lock_batch_id) AS c;

    -- 🔴 D4 — la bandiera si abbassa QUI, e per ESITO.
    -- Stessa forma della sorella fn_riporta_lotto_a_draft: si
    -- chiudono le corse di TUTTI gli step, non solo di quello
    -- fallito. La pulizia qui sopra ha cancellato tutto cio' che
    -- quelle corse avevano prodotto — nessuna deve piu' avere voce
    -- sul cruscotto, e nemmeno sul giro successivo.
    -- ⚠️ `task_stato IS DISTINCT FROM 'ANNULLATO'` tiene fuori le
    --    corse gia' chiuse cosi': la funzione resta idempotente, e
    --    il contatore dice quante ne ha chiuse DAVVERO questa
    --    chiamata, non quante ce n'erano.
    WITH da_annullare AS (
      SELECT r.id
        FROM vendite.fatturazione_lotti_task_runs r
       WHERE r.lotto_id = p_lotto_id
         AND r.attivo IS TRUE
         AND r.task_stato IS DISTINCT FROM 'ANNULLATO'
    ), annullati AS (
      SELECT vendite.fn_cancel_lotto_task_run(
               d.id,
               jsonb_build_object('motivo', 'annullo_lotto', 'lotto_id', p_lotto_id)
             )
        FROM da_annullare d
    )
    SELECT count(*)::INTEGER INTO v_annullati_task_run FROM annullati;

    -- ⛔ `stato_lotto` NON SI TOCCA (rev 2026-09-07). Fino a oggi questa riga
    --   ci scriveva 'COMPLETATO', e sono TRE regole infrante in una:
    --     1. la macchina a stati la vieta — fn_set_fatturazione_lotto_stato
    --        rifiuta ERRORE -> COMPLETATO («da ERRORE solo IN_ESECUZIONE») —
    --        e questo UPDATE diretto le passava dietro, quindi il guardiano
    --        non vedeva nemmeno la transizione;
    --     2. la sorella fn_riporta_lotto_a_draft dichiara nel proprio corpo
    --        «stato_lotto NON si tocca — ha una macchina a stati cablata», e
    --        l'intestazione qui sopra invoca la SIMMETRIA con lei come
    --        principio: «due sorelle non possono comportarsi diversamente
    --        sulla stessa cosa»;
    --     3. e' la stessa cosa che l'intestazione rifiuta due paragrafi sopra
    --        per `attivo`: DUE DOMANDE SU UN FLAG SOLO. `stato_lotto` risponde
    --        a «com'e' andata l'elaborazione»; che il lotto non sia piu' in
    --        lavorazione lo dicono gia' `stato_operativo` e
    --        `stato_doc_fiscale_id`, che questa riga scrive.
    -- ⭐ E non serviva a niente: il problema degli «errori vivi» lo risolve la
    --   chiusura dei task run PER ESITO (rev 2026-09-04), e
    --   vw_dash_competenza_errori `stato_lotto` lo PROIETTA soltanto, non ci
    --   filtra. Verificato: nessun cancello pretende COMPLETATO su un annullato.
    -- ⚠️ E falsificava in ENTRAMBI i casi, non solo sul lotto fallito: uno
    --   annullato mentre era IN_ESECUZIONE veniva marcato COMPLETATO, cioe'
    --   «la corsa e' finita bene» di un giro interrotto. Effetto misurato il
    --   2026-09-07: LTF-0009900, annullato dopo un fallimento,
    --   risultava COMPLETATO con una segnalazione critica viva, e accendeva
    --   vw_lotti_chiusi_con_gruppi_in_errore — un presidio che dichiara di
    --   dover poter restare vuoto.
    -- Brief: brief-db-esito-gruppo-lotto §22-§24.
    UPDATE vendite.fatturazione_lotti SET stato_operativo = 'CHIUSO', stato_doc_fiscale_id = v_annullata_id, data_update = now(), user_update = current_user WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture, v_deleted_righe, v_annullati_task_run;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
