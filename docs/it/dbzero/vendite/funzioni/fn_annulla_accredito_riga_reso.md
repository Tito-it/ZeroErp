# ⚙️ Funzione `fn_annulla_accredito_riga_reso`

```sql
CREATE FUNCTION fn_annulla_accredito_riga_reso(p_resi_riga_id bigint, p_motivo text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_accredito_riga_reso(p_resi_riga_id bigint, p_motivo text)
 RETURNS TABLE(accredito_id bigint, commessa_attivita_id bigint, fattura_riga_rettificata_id bigint, qta numeric, qta_partita numeric)
 LANGUAGE plpgsql
AS $function$
-- Scopo: madre DB del verbo «annulla accredito». Specchio di
--   vendite.fn_accredita_riga_reso: toglie le coppie dal ponte
--   vendite.resi_righe_accrediti e porta le rettifiche di
--   commessa a stato_emissione = 'ANNULLATA'.
-- Perimetro: una sola unita' atomica, e la sua unita' e'
--   l'ACCREDITO INTERO — non la singola coppia. Ritorna le
--   coppie rimosse, nella stessa forma con cui la madre le ha
--   create, perche' il chiamante possa dire cosa ha disfatto.
-- ⛔ Non e' l'annullo del DOCUMENTO: quello e' il reset del
--   lotto, e dopo un reset la nota di credito RIGENERA al giro
--   successivo. Qui no: si torna prima del verbo.
-- Il presidio permessi vive sul BE (post_permission), non qui:
--   la madre deve restare usabile da un processo autorizzato.
DECLARE
    v_motivo        text;
    -- ⚠️ bigint[] esplicito: colonna%TYPE[] non esiste in
    --    PostgreSQL (linee-guida-sql, memoria di casa).
    --    E' l'unica eccezione all'ancoraggio in questo DECLARE.
    v_ids           bigint[];
    -- `integer` esplicito: sono CONTEGGI, non il valore di una
    -- colonna. Non c'e' nulla da ancorare, e va detto invece di
    -- sembrare una dimenticanza.
    v_n_coppie      integer;
    v_n_rettifiche  integer;
    v_n_viste       integer;
    v_n_bloccate    integer;
    v_n_cancellate  integer;
    v_n_annullate   integer;
    v_r             record;
BEGIN
    -- --------------------------------------------------
    -- 1) Guard sui parametri (AGENTS.md: NULL o <=0 ->
    --    errore parlante, mai normalizzazione silenziosa).
    -- --------------------------------------------------
    IF p_resi_riga_id IS NULL OR p_resi_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','resi_riga_id','valore',p_resi_riga_id),
            NULL::uuid, 'resi_riga_id obbligatorio (>0)');
    END IF;

    -- Motivo: btrim, poi obbligatorio non vuoto. L'annullo
    -- CANCELLA le coppie, quindi l'unica traccia del PERCHE'
    -- resta l'evento di log: senza motivo resta il fatto senza
    -- la ragione, e a mesi di distanza un accredito sparito
    -- senza spiegazione e' indistinguibile da un errore.
    v_motivo := btrim(COALESCE(p_motivo, ''));
    IF v_motivo = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_ACCREDITO_MOTIVO_OBBLIGATORIO',
            jsonb_build_object('resi_riga_id', p_resi_riga_id),
            NULL::uuid, p_resi_riga_id::text);
    END IF;

    -- --------------------------------------------------
    -- 2) IL LOCK, in testa e prima di leggere l'insieme.
    --    FOR UPDATE sulla riga di reso: e' lo stesso appiglio
    --    che trgfn_resi_accrediti_guard prende a ogni scrittura
    --    sul ponte, quindi e' il punto in cui l'esclusione con
    --    la madre INTERSECA davvero — la madre ci arriva
    --    attraversando il proprio guard alla prima INSERT.
    --    Il suo advisory lock sta sulla riga di DDT e serve al
    --    progressivo #RET: un altro appiglio, per un'altra cosa.
    --    ⛔ Nessun deadlock: qui non si attende mai l'advisory,
    --    quindi il secondo verso del ciclo non esiste.
    --    Sta DOPO le guard sui parametri: una chiamata invalida
    --    non deve serializzare gli altri operatori.
    -- --------------------------------------------------
    PERFORM 1 FROM vendite.resi_righe r
      WHERE r.id = p_resi_riga_id
      FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_VALORE_MANCANTE',
            jsonb_build_object('resi_riga_id', p_resi_riga_id),
            NULL::uuid, concat('resi_riga_id ', p_resi_riga_id));
    END IF;

    -- --------------------------------------------------
    -- 3) L'INSIEME. Si legge dal ponte, che non ha RLS: e'
    --    la sola fonte che dica la verita' su QUANTE
    --    rettifiche compongono questo accredito.
    --    Due conteggi distinti e non uno: oggi il rapporto
    --    coppia/rettifica e' 1:1 per costruzione, ma nessun
    --    vincolo lo impone (uq_resi_accrediti_pair e' sulla
    --    coppia, non su commessa_attivita_id). Contarli
    --    separatamente costa nulla e non da' per scontato un
    --    invariante che nessuno difende.
    -- --------------------------------------------------
    SELECT count(*)::integer,
           count(DISTINCT a.commessa_attivita_id)::integer,
           array_agg(DISTINCT a.commessa_attivita_id)
      INTO v_n_coppie, v_n_rettifiche, v_ids
      FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = p_resi_riga_id;

    IF v_n_coppie = 0 THEN
        -- ⚠️ «Mai accreditato» e «gia' annullato» finiscono
        --    qui insieme, e non e' un difetto: l'annullo
        --    cancella, quindi lo stato osservabile e' lo
        --    stesso. Un flag per distinguerle sarebbe il
        --    soft-delete che romperebbe il gate della rinuncia.
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_ACCREDITO_NON_TROVATO',
            jsonb_build_object('resi_riga_id', p_resi_riga_id),
            NULL::uuid, p_resi_riga_id::text);
    END IF;

    -- --------------------------------------------------
    -- 4) FAIL-CLOSED sulla VISIBILITA', prima di scrivere.
    --    vendite.commesse_attivita ha la RLS, il ponte no:
    --    una rettifica fuori perimetro emittente si legge come
    --    «non c'e'» e la UPDATE la salterebbe in silenzio.
    --    Zero non e' un dato, e' fail-closed: qui si misura
    --    PRIMA, cosi' la diagnosi arriva senza che ci sia
    --    nulla da annullare.
    -- --------------------------------------------------
    SELECT count(*)::integer
      INTO v_n_viste
      FROM vendite.commesse_attivita ca
     WHERE ca.id = ANY(v_ids);

    IF v_n_viste <> v_n_rettifiche THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_ACCREDITO_ANNULLO_INCOMPLETO',
            jsonb_build_object('resi_riga_id',  p_resi_riga_id,
                               'fase',          'pre-scrittura',
                               'viste',         v_n_viste,
                               'attese',        v_n_rettifiche,
                               'attivita_ids',  to_jsonb(v_ids)),
            NULL::uuid,
            p_resi_riga_id::text, v_n_viste::text, v_n_rettifiche::text);
    END IF;

    -- --------------------------------------------------
    -- 5) ⛔ IL CANCELLO TUTTO-O-NIENTE.
    --    Le tre condizioni sono quelle con cui la catena
    --    tratta qualunque attivita' non ancora emessa, e vanno
    --    tenute TUTTE E TRE: dopo un reset di lotto la riga di
    --    attivita_fatturabili SOPRAVVIVE (fn_cleanup_fatture_by_ids
    --    la sblocca e le azzera fattura_riga_id, non la
    --    cancella). Scrivere «esiste una AF -> bloccato»
    --    vieterebbe per sempre l'annullo dopo un reset
    --    legittimo: e' il ramo che sembra piu' prudente e
    --    invece e' sbagliato.
    --    Basta UNA rettifica bloccata per rifiutare TUTTO: un
    --    annullo parziale lascerebbe la coda a chiedere un
    --    residuo che nessuno puo' piu' soddisfare, che e' la
    --    malattia per cui questo cantiere esiste.
    -- --------------------------------------------------
    SELECT count(*)::integer
      INTO v_n_bloccate
      FROM vendite.commesse_attivita ca
     WHERE ca.id = ANY(v_ids)
       AND ( ca.stato_emissione <> 'NON_EMESSA'
             OR EXISTS (
                 SELECT 1
                   FROM vendite.attivita_fatturabili af
                  WHERE af.commessa_attivita_id = ca.id
                    AND ( COALESCE(af.lock_in_fatturazione, false)
                          OR af.fattura_riga_id IS NOT NULL ) ) );

    IF v_n_bloccate > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_ACCREDITO_ANNULLO_NON_AMMESSO',
            jsonb_build_object('resi_riga_id', p_resi_riga_id,
                               'bloccate',     v_n_bloccate,
                               'totali',       v_n_rettifiche,
                               'attivita_ids', to_jsonb(v_ids)),
            NULL::uuid,
            p_resi_riga_id::text, v_n_bloccate::text, v_n_rettifiche::text);
    END IF;

    -- --------------------------------------------------
    -- 6) AUDIT + risultato, PRIMA della cancellazione: dopo,
    --    le coppie non ci sono piu' e con loro sparirebbe
    --    l'unica descrizione di cosa e' stato disfatto.
    --    Specchio di ACCREDITO_RICHIESTO scritto dalla madre.
    -- --------------------------------------------------
    FOR v_r IN
        SELECT a.id, a.commessa_attivita_id, a.fattura_riga_rettificata_id,
               a.qta, a.qta_partita, a.gruppo, a.meta
          FROM vendite.resi_righe_accrediti a
         WHERE a.resi_riga_id = p_resi_riga_id
         ORDER BY a.id
    LOOP
        INSERT INTO vendite.commesse_attivita_log (commessa_attivita_id, evento, dettaglio)
        VALUES (v_r.commessa_attivita_id, 'ACCREDITO_ANNULLATO',
                jsonb_build_object(
                    'motivo',                      v_motivo,
                    'resi_riga_id',                p_resi_riga_id,
                    'accredito_id',                v_r.id,
                    'fattura_riga_rettificata_id', v_r.fattura_riga_rettificata_id,
                    'qta_documento',               v_r.qta,
                    'qta_partita',                 v_r.qta_partita,
                    'gruppo',                      v_r.gruppo,
                    'segment_key',                 v_r.meta ->> 'segment_key',
                    -- L'insieme di cui questa riga faceva parte:
                    -- senza, il log direbbe COSA e' stato tolto
                    -- ma non che era una operazione sola.
                    'coppie_dell_accredito',       v_n_coppie,
                    'rettifiche_dell_accredito',   v_n_rettifiche));

        accredito_id                := v_r.id;
        commessa_attivita_id        := v_r.commessa_attivita_id;
        fattura_riga_rettificata_id := v_r.fattura_riga_rettificata_id;
        qta                         := v_r.qta;
        qta_partita                 := v_r.qta_partita;
        RETURN NEXT;
    END LOOP;

    -- --------------------------------------------------
    -- 7) Il ponte. ⭐ CANCELLA, non marca: e' da questa riga
    --    che dipende il gate della rinuncia (P-3), che si
    --    auto-ripara solo perche' la riga sparisce davvero.
    --    Ed e' la cancellazione a far RISALIRE accredito_dovuto
    --    in vw_resi_da_accreditare: senza, la coda resterebbe
    --    muta per sempre e la merce non sarebbe piu'
    --    accreditabile da nessuno.
    --    Il guard del ponte e' BEFORE INSERT OR UPDATE: sul
    --    DELETE non si oppone, e non deve — i tetti scendono.
    -- --------------------------------------------------
    DELETE FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = p_resi_riga_id;
    GET DIAGNOSTICS v_n_cancellate = ROW_COUNT;

    IF v_n_cancellate <> v_n_coppie THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_ACCREDITO_ANNULLO_INCOMPLETO',
            jsonb_build_object('resi_riga_id', p_resi_riga_id,
                               'fase',         'delete-ponte',
                               'toccate',      v_n_cancellate,
                               'attese',       v_n_coppie),
            NULL::uuid,
            p_resi_riga_id::text, v_n_cancellate::text, v_n_coppie::text);
    END IF;

    -- --------------------------------------------------
    -- 8) Le rettifiche: ANNULLATA, non DELETE. La riga resta
    --    con importo e storia e smette solo di essere
    --    eleggibile — ANNULLATA e' gia' filtrato da tutte le
    --    porte verso fattura e cockpit. stato_approvazione non
    --    si tocca: sono due assi con CHECK separati, e una
    --    riga annullata conserva la memoria di essere stata
    --    approvata.
    --    ⚠️ Il predicato ripete stato_emissione = 'NON_EMESSA'
    --    gia' verificato al punto 5: e' la scrittura stessa a
    --    essere fail-closed, cosi' un cambio di stato nella
    --    finestra fra controllo e UPDATE non passa inosservato
    --    ma fa scattare il ROW_COUNT qui sotto.
    -- --------------------------------------------------
    UPDATE vendite.commesse_attivita ca
       SET stato_emissione = 'ANNULLATA'
     WHERE ca.id = ANY(v_ids)
       AND ca.stato_emissione = 'NON_EMESSA';
    GET DIAGNOSTICS v_n_annullate = ROW_COUNT;

    IF v_n_annullate <> v_n_rettifiche THEN
        -- Difesa in profondita', gemella di
        -- E_ACCREDITO_SEGMENT_DUPLICATO nella madre: col lock
        -- in testa e il controllo di visibilita' al punto 4
        -- non deve mai scattare. Se scatta e' una regressione
        -- o un perimetro incoerente, non un caso d'uso.
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_accredito_riga_reso','E_ACCREDITO_ANNULLO_INCOMPLETO',
            jsonb_build_object('resi_riga_id', p_resi_riga_id,
                               'fase',         'update-rettifiche',
                               'toccate',      v_n_annullate,
                               'attese',       v_n_rettifiche,
                               'attivita_ids', to_jsonb(v_ids)),
            NULL::uuid,
            p_resi_riga_id::text, v_n_annullate::text, v_n_rettifiche::text);
    END IF;

    RETURN;
END
$function$

COMMENT ON FUNCTION vendite.fn_annulla_accredito_riga_reso(p_resi_riga_id bigint, p_motivo text)
IS 'MADRE del verbo «annulla accredito», specchio di vendite.fn_accredita_riga_reso (brief-db-note-credito-prerequisiti-be-fe §8 passo 3, P-5 corretta da C-2). Toglie le coppie da vendite.resi_righe_accrediti e porta le rettifiche a stato_emissione = ANNULLATA, con motivo obbligatorio e audit su commesse_attivita_log (evento ACCREDITO_ANNULLATO): tre scritture, una unita'' atomica. ⛔ NON e'' l''annullo del DOCUMENTO — quello e'' il reset del lotto, dopo il quale la nota di credito RIGENERA al giro successivo perche'' la merce resa non e'' cambiata; qui si torna prima del verbo. ⭐ SEMANTICA D''INSIEME: un accredito non e'' una riga ma N coppie e N rettifiche (consumo LIFO su piu'' righe di fattura + una rettifica per componente sui kit), quindi basta UNA rettifica emessa, fatturata o agganciata a un lotto vivo per rifiutare TUTTO (E_ACCREDITO_ANNULLO_NON_AMMESSO) — un annullo parziale lascerebbe la coda a chiedere un residuo che nessuno puo'' piu'' soddisfare, che e'' la dottrina di E_ACCREDITO_QUOTA_NON_COPERTA allo specchio. ⚠️ Le tre condizioni si tengono tutte e tre: dopo un reset di lotto la riga di attivita_fatturabili SOPRAVVIVE sbloccata e senza fattura_riga_id, quindi «esiste una AF -> bloccato» vieterebbe per sempre l''annullo dopo un reset legittimo. LOCK: FOR UPDATE su vendite.resi_righe, lo stesso appiglio di trgfn_resi_accrediti_guard — e'' li'' che l''esclusione con la madre interseca davvero, perche'' la madre ci arriva attraversando il proprio guard alla prima INSERT (il suo advisory lock sta sulla riga di DDT e serve al progressivo #RET). Nessun deadlock: qui l''advisory non si attende mai. ⚠️ DOPPIO FAIL-CLOSED su ROW_COUNT (E_ACCREDITO_ANNULLO_INCOMPLETO): commesse_attivita ha la RLS e il ponte no, quindi una rettifica fuori perimetro emittente verrebbe saltata IN SILENZIO lasciando l''annullo a meta''. ⭐ CANCELLA e non marca, e non e'' un dettaglio implementativo: il gate della rinuncia (fn_check_rinuncia_reversibile) si auto-ripara SOLO perche'' la riga sparisce — se un giorno diventasse un soft-delete, quel gate va cambiato insieme. E'' anche la cancellazione a far risalire accredito_dovuto in vw_resi_da_accreditare. NON si riusa fn_annulla_commessa_attivita benche'' le rettifiche siano sourceless: il suo perimetro dichiarato e'' la riga MANUALE, il suo evento di log direbbe il falso e la sua decisione e'' per riga invece che d''insieme. «Nessun accredito» copre insieme «mai accreditato» e «gia'' annullato», indistinguibili per costruzione. SECURITY INVOKER. Presidio permessi sul BE. Ritorna le coppie rimosse. rev 2026-08-18.';
```

---
{% include-markdown "signature-core.md" %}
