{% include-markdown "it/dbzero/vendite/manual/fn_annulla_lotto_da_draft.md" %}
# ⚙️ Funzione `fn_annulla_lotto_da_draft`

```sql
CREATE FUNCTION fn_annulla_lotto_da_draft(p_lotto_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_lotto_da_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer, annullati_task_run integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- rev 2026-10-27 (20261027-27): solo commenti; la regola del job e' la matrice
--   config.transizioni_stati_lotto_job (vedi «stato_lotto NON SI TOCCA»).
-- rev 2026-10-27 (20261027-15, brief-modello-documento-vendita §15): lo
--   stato fiscale lo scrive il verbo del lotto, vendite.fn_cambia_stato_lotto,
--   dopo la pulizia (la porta non lascia passare l'UPDATE); il passaggio
--   non chiede un'azione (Q-F2: basta il permesso sui lotti). Lo stato
--   d'annullo dal vocabolario (script.fn_stato_abortito_id), non dal
--   letterale 'ANNULLATA'.
-- Scopo: rollback tecnico di un lotto in DRAFT — cancella le
--        fatture PRE-FISCALI (DRAFT/EMESSA), ripristina le
--        attivita' e CHIUDE il lotto portandolo ad ANNULLATA.
-- Perimetro (D-L pt.2 + D-T): vale per MASSIVO **e** GIORNALIERO.
--        Il vincolo al solo MASSIVO e' caduto quando D-T ha reso
--        lecita la transizione DRAFT->ANNULLATA per entrambi.
-- rev 2026-09-23 (brief-db-annullamento-chiude-la-vita §9.4):
--        l'annullo CHIUDE anche gli ESITI — un lotto annullato e'
--        VUOTO. Ogni esito non ancora ESCLUSO passa a ESCLUSO con
--        il motivo dell'annullo; il timbro lo mette il trigger.
--        ⚠️ Qui la sorella fn_riporta_lotto_a_draft NON va
--        imitata, ed e' voluto: lei tiene il lotto vivo e il giro
--        dopo riscrive gli esiti; l'annullo non ha un giro dopo.
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
    v_utente               config.user_override_azioni.auth_user_id%TYPE;
    v_stato_da_id          vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_lock_batch_id        vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_lotto_codice         vendite.fatturazione_lotti.codice%TYPE;
    v_annullata_id         config.stati_doc_fiscale.id%TYPE;
    v_annullata_codice     config.stati_doc_fiscale.codice_interno%TYPE;
    v_uscita_motivo        vendite.fatturazione_lotti_esiti.uscita_motivo%TYPE;
    v_motivi               jsonb;
    v_fatture_ids          BIGINT[];
    v_updated_lotti        INTEGER := 0;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
    v_annullati_task_run   INTEGER := 0;
    v_esiti_chiusi         INTEGER := 0;
BEGIN
    -- ⭐ rev 2026-11-25 (brief-db-porte-aperte-dalla-sola-guc, giro 1-7): SECURITY DEFINER.
    --   L'ordine e' utente, parametri, lotto nel perimetro, permesso,
    --   motivi. Il permesso dipende dallo stato del lotto (la riga del
    --   passaggio verso lo stato d'annullo), quindi prima si legge il lotto: e'
    --   lo stesso ordine di vendite.fn_cambia_stato_lotto.
    v_utente := script.fn_utente_di_sessione('vendite.fn_annulla_lotto_da_draft');

    -- Le GUC che dentro un verbo DEFINER aprirebbero una porta si
    -- spengono all'ingresso: quella del reset del lotto (la riaccende
    -- solo la pulizia, e solo mentre lavora) e quella delle righe
    -- contabili del fondo.
    PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', '', true);
    PERFORM set_config('zeroerp.allow_contabile_riga_delete_override', '', true);

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_annulla_lotto_da_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- Il perimetro, una volta, all'ingresso, sul lotto: la regola della
    -- policy di vendite.fatturazione_lotti, rimessa qui perche' il verbo
    -- legge da proprietario. Fuori perimetro il lotto «non c'e'», come un
    -- lotto che non esiste, e prima di dire qualunque cosa sul suo stato.
    IF NOT COALESCE(script.fn_scope_ef_whitelist_via_lotto(v_utente, p_lotto_id), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_annulla_lotto_da_draft', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('detail', 'lotto inesistente o fuori perimetro', 'lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- ⭐ E sulle sue fatture (D-Y a): il modello non lega la fattura
    -- all'azienda del lotto (nessun vincolo su fatturazione_lotti_fatture),
    -- e la pulizia le cancella tutte. Una sola fuori perimetro e il lotto
    -- «non c'e'»: fail-closed, senza dire che cosa contiene.
    IF EXISTS (SELECT 1
                 FROM vendite.fatturazione_lotti_fatture lf
                WHERE lf.lotto_id = p_lotto_id
                  AND NOT COALESCE(script.fn_scope_ef_whitelist_via_fattura(v_utente, lf.fattura_id), false)) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_annulla_lotto_da_draft', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('detail', 'lotto con fatture fuori perimetro', 'lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- Il lotto, col lucchetto, e il suo stato: da qui il permesso.
    SELECT l.stato_doc_fiscale_id INTO v_stato_da_id
      FROM vendite.fatturazione_lotti l
     WHERE l.id = p_lotto_id
       FOR UPDATE;

    -- Il permesso che l'endpoint controlla (D-X a): l'azione della riga del
    -- passaggio, o il livello TUTTO sull'area vendite.
    PERFORM vendite.fn_guard_passaggio_lotto(v_utente, v_stato_da_id, script.fn_stato_abortito_id('vendite.fatturazione_lotti'::regclass));

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

    -- rev 2026-09-23: anche il codice, per il motivo d'uscita degli esiti.
    SELECT fl.lock_batch_id, fl.codice
      INTO v_lock_batch_id, v_lotto_codice
      FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;

    -- Lo stato d'annullo dal vocabolario (rev 2026-10-27, guida del modello §8).
    SELECT s.id, s.codice_interno INTO v_annullata_id, v_annullata_codice
      FROM config.stati_doc_fiscale s
     WHERE s.id = script.fn_stato_abortito_id('vendite.fatturazione_lotti'::regclass);
    IF v_annullata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_annulla_lotto_da_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('stati_doc_fiscale', 'is_abortito'), NULL::uuid, 'stato d''annullo del vocabolario fiscale non configurato');
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

    -- ⭐ rev 2026-09-23 — GLI ESITI ESCONO TUTTI. Un lotto annullato
    --   e' vuoto: la pulizia qui sopra ha cancellato ogni fattura del
    --   giro, quindi nessun esito puo' piu' dire com'e' andato un
    --   documento in QUESTO lotto — nemmeno COMPLETED, che direbbe
    --   «e' andato bene» su un documento senza fattura.
    -- ⭐ ESCLUSO, lo stato che dice gia' «uscito dal giro», con il
    --   motivo obbligatorio per CHECK. uscita_quando/uscita_da li
    --   scrive trgfn_fatturazione_lotti_esiti_uscita: non qui.
    -- ⚠️ `<> 'ESCLUSO'`: chi era gia' uscito tiene il SUO motivo e il
    --    suo timbro (e il trigger non li toccherebbe comunque), e la
    --    funzione resta idempotente.
    v_uscita_motivo := format('Annullo del lotto %s', v_lotto_codice);

    UPDATE vendite.fatturazione_lotti_esiti e
       SET stato_esecuzione = 'ESCLUSO',
           uscita_motivo    = v_uscita_motivo
     WHERE e.lotto_id = p_lotto_id
       AND e.stato_esecuzione <> 'ESCLUSO';
    GET DIAGNOSTICS v_esiti_chiusi = ROW_COUNT;

    -- ⛔ `stato_lotto` NON SI TOCCA (rev 2026-09-07). Fino a oggi questa riga
    --   ci scriveva 'COMPLETATO', e sono TRE regole infrante in una:
    --     1. la macchina a stati la vietava — allora fn_set_fatturazione_lotto_stato
    --        rifiutava ERRORE -> COMPLETATO («da ERRORE solo IN_ESECUZIONE») —
    --        e questo UPDATE diretto le passava dietro, quindi il guardiano
    --        non vedeva nemmeno la transizione. Dal 2026-10-27 la regola sta
    --        nella matrice config.transizioni_stati_lotto_job, applicata a ogni
    --        scrittura da trgfn_fatturazione_lotti_guard_stato_job (la funzione
    --        e' ritirata, 20261027-07): ERRORE -> COMPLETATO resta vietato;
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
    -- rev 2026-10-27: lo stato fiscale dal verbo del lotto (la porta), lo
    -- stato operativo con l'UPDATE di sempre.
    PERFORM 1 FROM vendite.fn_cambia_stato_lotto(p_lotto_id, v_annullata_codice);
    UPDATE vendite.fatturazione_lotti SET stato_operativo = 'CHIUSO', data_update = now(), user_update = current_user WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    -- ⭐ rev 2026-09-23 — L'USCITA SI RACCONTA NEL GIORNALE, come fa
    --   fn_escludi_documento_da_giro per il singolo documento. Dopo
    --   l'UPDATE: la riga porta lo stato del lotto chiuso. `I`: e' un
    --   fatto, non un allarme. Il motivo nel MESSAGGIO, non solo in
    --   meta: chi legge il giornale legge il messaggio.
    IF v_esiti_chiusi > 0 THEN
        PERFORM vendite.fn_log_pipeline_fase(
            p_lotto_id,
            v_annullata_id,
            'ANNULLO_LOTTO',
            'I'::char,
            format('%s: %s documenti usciti dal giro', v_uscita_motivo, v_esiti_chiusi),
            jsonb_build_object('esiti_chiusi',  v_esiti_chiusi,
                               'uscita_motivo', v_uscita_motivo));
    END IF;

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture, v_deleted_righe, v_annullati_task_run;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_lotto_da_draft(p_lotto_id bigint)
IS 'Verbo SECURITY DEFINER: legge il lotto nel perimetro, e con lui tutte le sue fatture (fuori: E_LOTTO_NON_TROVATO, come un lotto che non esiste), poi il permesso del passaggio verso lo stato d''annullo con vendite.fn_guard_passaggio_lotto (l''azione della riga, o il livello TUTTO sull''area vendite: lo stesso controllo dell''endpoint). Spegne all''ingresso le GUC delle porte; la pulizia riservata gira da proprietario e apre la porta del reset solo mentre lavora (brief-db-porte-aperte-dalla-sola-guc, giro 1-7). Annullo di un lotto in DRAFT (MASSIVO e GIORNALIERO): precondizioni da script.fn_check_lotto_annullabile, cancella le fatture pre-fiscali e ripristina le attivita'' (fn_cleanup_fatture_by_ids), chiude i task run con esito ANNULLATO, porta il lotto a CHIUSO/ANNULLATA senza toccare stato_lotto (rev 2026-09-07). ⭐ rev 2026-09-23: chiude anche gli ESITI — ogni riga di vendite.fatturazione_lotti_esiti non ancora ESCLUSO passa a ESCLUSO con uscita_motivo «Annullo del lotto <codice>» (timbro dal trigger) — e scrive una riga I nel giornale (fase ANNULLO_LOTTO) col numero di documenti usciti. Un lotto annullato e'' VUOTO: nessun controllo deve escluderlo. ⚠️ La sorella fn_riporta_lotto_a_draft non chiude gli esiti, ed e'' voluto: il lotto resta vivo e il giro dopo li riscrive. Firma invariata (il backend legge le cinque colonne per posizione). Brief: brief-db-annullamento-chiude-la-vita §9.4. rev 2026-10-27 (20261027-15, brief-modello-documento-vendita §15): lo stato fiscale lo scrive il verbo del lotto, vendite.fn_cambia_stato_lotto, dopo la pulizia (la porta non lascia passare l''UPDATE); il passaggio DRAFT -> ANNULLATA non chiede un''azione (Q-F2). Lo stato d''annullo dal vocabolario (script.fn_stato_abortito_id), non dal letterale ANNULLATA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
