{% include-markdown "it/dbzero/vendite/manual/fn_reset_fondi_fattura.md" %}
# ⚙️ Funzione `fn_reset_fondi_fattura`

```sql
CREATE FUNCTION fn_reset_fondi_fattura(p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reset_fondi_fattura(p_fattura_id bigint)
 RETURNS TABLE(deleted_source integer, deleted_fondi integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_deleted_source INTEGER := 0;
    v_deleted_fondi  INTEGER := 0;
    -- ⚠️ Array: `colonna%TYPE[]` non esiste in PostgreSQL, quindi
    --    qui il tipo resta esplicito. Portano id di
    --    vendite.fatture_fondi_fattura_source.
    v_src_ids      bigint[];
    v_registrate   bigint[];
    v_chiuse       bigint[];
    v_congelate    bigint[];
    v_trattenute   bigint[];
    v_resettabili  bigint[];
    v_id           bigint;
    v_esito        record;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Reset dei fondi applicati a una fattura FIGLIA. Il
    --   CRITERIO non e' piu' qui: sta in
    --   vendite.fn_check_fondo_cancellabile, e da qui si
    --   costruisce la sola REAZIONE — segnalare e proseguire.
    --
    -- ⚠️ E' un'operazione TECNICA sul ciclo di vita della figlia
    --   (il ritorno di un lotto in bozza) e NON una reazione ai
    --   pagamenti: nessun incasso la chiama e nessun incasso deve
    --   chiamarla.
    -- =========================================================

    -- ℹ️ Resta E_PARAMETRO_INVALIDO: e' un debito dichiarato con un
    --    cantiere suo, e cambiarlo qui sarebbe un cambio di
    --    contratto verso chi lo riconosce.
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    -- =========================================================
    -- 1) GLI ATTI GIA' ESEGUITI: solo segnalazione.
    --    Non entrano nemmeno nel giro sotto (che filtra
    --    ASSEGNATO): qui si dicono, perche' un reset silenzioso
    --    su una fattura che aveva un fondo eseguito lascerebbe
    --    l'operatore a chiedersi dove sia finito.
    --    ⭐ La condizione non e' piu' `s.stato = 'ESEGUITO'` ma la
    --    risposta del predicato: stessa popolazione — ATTO_ESEGUITO
    --    e' il primo motivo che prova — e una sede sola.
    -- =========================================================
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Fondo non resettabile: il trasferimento e'' gia'' stato registrato (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_ESEGUITO_NON_RESETTABILE', 'cause', 'ATTO_ESEGUITO'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.fattura_figlia_id = p_fattura_id
       AND vendite.fn_check_fondo_cancellabile(s.id) = 'ATTO_ESEGUITO';

    -- =========================================================
    -- 2) GLI ATTI IN GIOCO, bloccati in lettura.
    --    ⚠️ FOR UPDATE OF s: si bloccano le sole righe
    --    dell'atto; le JOIN su tipi (filtro) e fatture
    --    (display) non vanno bloccate.
    -- =========================================================
    SELECT array_agg(q.id) INTO v_src_ids
      FROM (
        SELECT s.id
          FROM vendite.fatture_fondi_fattura_source s
          JOIN vendite.tipi_fondi_fattura t ON t.id = s.tipo_fondo_fattura_id
         WHERE s.fattura_figlia_id = p_fattura_id
           AND s.stato = 'ASSEGNATO'
           AND t.codice_interno = 'F_F_ADD_ACC'
           FOR UPDATE OF s
      ) q;

    IF v_src_ids IS NULL THEN
        RETURN QUERY SELECT 0, 0;
        RETURN;
    END IF;

    -- =========================================================
    -- 3) LA PARTIZIONE, da UNA sola lettura del predicato.
    --    ⛔ Il predicato si legge una volta sola per atto: e' il
    --    difetto gia' pagato in Fase C — chiamarlo due volte sulla
    --    stessa riga significa accettarne meta' e rifiutarne
    --    l'altra.
    --    ℹ️ FIGLIA_CONGELATA non si accende in questo percorso:
    --    l'unico chiamante (fn_cleanup_fatture_by_ids) imposta la
    --    GUC zeroerp.maintenance_reset_lotto_draft, che spegne la
    --    sola quarta condizione. Il ramo resta scritto perche' il
    --    vocabolario del predicato e' chiuso e ogni valore deve
    --    avere una reazione: un motivo senza reazione sarebbe un
    --    atto saltato in silenzio.
    -- =========================================================
    WITH letti AS (
        SELECT x AS id, vendite.fn_check_fondo_cancellabile(x) AS motivo
          FROM unnest(v_src_ids) AS x
    )
    SELECT array_agg(id) FILTER (WHERE motivo IS NULL),
           array_agg(id) FILTER (WHERE motivo = 'RIGA_REGISTRATA'),
           array_agg(id) FILTER (WHERE motivo = 'CONTABILE_CHIUSA'),
           array_agg(id) FILTER (WHERE motivo = 'FIGLIA_CONGELATA'),
           array_agg(id) FILTER (WHERE motivo = 'SISTEMAZIONE_ATTIVA')
      INTO v_resettabili, v_registrate, v_chiuse, v_congelate, v_trattenute
      FROM letti;

    -- =========================================================
    -- 4) Le segnalazioni dei bloccati, e l'annullamento dei soli
    --    bloccati da distinta chiusa.
    --    ⭐ La frase non dice «gia postato»: la condizione
    --       e' che la distinta e' chiusa, cioe' il caso in cui
    --       il denaro NON e' stato registrato.
    -- =========================================================
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Minimo non ripristinabile: la distinta contabile e'' chiusa (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_MINIMO_NON_RIPRISTINABILE', 'cause', 'CONTABILE_CHIUSA'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.id = ANY (COALESCE(v_chiuse, '{}'::bigint[]));

    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Fondo non resettabile: una sua riga contabile risulta gia'' registrata (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_ESEGUITO_NON_RESETTABILE', 'cause', 'RIGA_REGISTRATA'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.id = ANY (COALESCE(v_registrate, '{}'::bigint[]));

    -- ⭐ NUOVO: l'atto che una sistemazione trattiene. ⚠️ Fino a
    --    qui il reset ci sbatteva contro con un 23503 nudo sulla
    --    FK, e il lotto si fermava senza che nessuna riga dicesse
    --    perche'. Il reset fallira' comunque piu' avanti, sulla
    --    DELETE della fattura — l'atto continua a puntarla — ma
    --    adesso il diario porta la ragione.
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Fondo non resettabile: nasce da una sistemazione, e si disfa annullando quella (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_TRATTENUTO_DA_SISTEMAZIONE', 'cause', 'SISTEMAZIONE_ATTIVA'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.id = ANY (COALESCE(v_trattenute, '{}'::bigint[]));

    -- ⭐ NUOVO e non raggiungibile dall'unico chiamante di oggi
    --    (che porta il bypass di manutenzione). Sta qui perche' il
    --    vocabolario del predicato e' chiuso: un motivo senza
    --    reazione sarebbe un atto saltato in silenzio.
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Fondo non resettabile: la fattura che lo ha ricevuto non e'' piu'' modificabile (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_FIGLIA_CONGELATA', 'cause', 'FIGLIA_CONGELATA'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.id = ANY (COALESCE(v_congelate, '{}'::bigint[]));

    -- ⭐ La ragione dell'annullamento sta SUL DATO, non solo nel
    --    diario: chi legge la riga del fondo sa perche' e'
    --    ANNULLATO senza dover cercare in fatture_log.
    UPDATE vendite.fatture_fondi_fattura_source s
       SET stato = 'ANNULLATO',
           motivo = format('Minimo non ripristinabile: distinta contabile gia CHIUSA (fattura %s del %s)',
                           COALESCE(fs.numero::text, 'N/D'),
                           COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           data_update = now(), user_update = current_user
      FROM vendite.fatture fs
     WHERE fs.id = s.fattura_sorgente_id
       AND s.id = ANY (COALESCE(v_chiuse, '{}'::bigint[]));

    -- =========================================================
    -- 5) I RESETTABILI: la cancellazione la fa
    --    fn_cancella_fondo_fattura, che e' la sede UNICA dei tre
    --    DELETE nell'ordine che la FK NO ACTION impone.
    --    ⚠️ Un atto per volta, e non un giro insiemistico: la
    --    funzione e' la stessa che serve il gesto della persona, e
    --    tenerne due forme vorrebbe dire tenerne due allineate.
    -- =========================================================
    FOREACH v_id IN ARRAY COALESCE(v_resettabili, '{}'::bigint[])
    LOOP
        SELECT * INTO v_esito
          FROM vendite.fn_cancella_fondo_fattura(v_id);

        v_deleted_source := v_deleted_source + COALESCE(v_esito.deleted_source, 0);
        v_deleted_fondi  := v_deleted_fondi  + COALESCE(v_esito.deleted_fondi, 0);
    END LOOP;

    RETURN QUERY SELECT COALESCE(v_deleted_source, 0), COALESCE(v_deleted_fondi, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_reset_fondi_fattura(p_fattura_id bigint)
IS 'Reset dei fondi applicati a una fattura FIGLIA. ⭐ rev 2026-08-31 (D-21 di brief-db-fondo-fattura-ricalcolo-e-governo §9.7-b): il CRITERIO non sta piu'' qui — sta in vendite.fn_check_fondo_cancellabile — e i tre DELETE nell''ordine che la FK impone stanno in vendite.fn_cancella_fondo_fattura. Qui resta la sola REAZIONE, che e'' l''opposto di quella del gesto manuale: si SEGNALA E SI PROSEGUE, perche'' e'' un giro tecnico su N atti e un''eccezione fermerebbe il reset di un lotto intero per colpa di una fattura sola. ⛔ Non si e'' estratta la funzione ma il PREDICATO, proprio perche'' le due reazioni sono opposte; due copie del criterio direbbero, senza errori e senza log, che un atto e'' intoccabile mentre il reset lo cancella. ⚠️ Il predicato si legge UNA VOLTA SOLA per atto (difetto di Fase C). ⚠️ Comportamento invariato: il blocco degli ESEGUITO chiede al predicato invece di guardare lo stato, e la popolazione e'' la stessa perche'' ATTO_ESEGUITO e'' il primo motivo che il predicato prova. ⭐ La quarta condizione FIGLIA_CONGELATA non si accende in questo percorso: l''unico chiamante, fn_cleanup_fatture_by_ids, imposta zeroerp.maintenance_reset_lotto_draft — ed e'' cosi'' che il gesto di una persona e la pulizia di un lotto restano due porte diverse. Il ramo resta scritto perche'' il vocabolario e'' chiuso e un motivo senza reazione sarebbe un atto saltato in silenzio. ⭐ SISTEMAZIONE_ATTIVA e'' nuovo e migliora un difetto latente: un riporto sulla figlia faceva fallire il reset con un 23503 nudo, adesso l''atto viene saltato e il diario ne dice la ragione (il reset fallira'' comunque piu'' avanti, ma non piu'' in silenzio). ⭐ rev 2026-08-21 (cantiere incassi, lotto 3, passo S1-17, decisione D11): l''atto NON eseguito si CANCELLA invece di tornare DISPONIBILE, e un atto ESEGUITO non si tocca mai. ⚠️ Due conseguenze accettate: la tabella non e'' storicizzata, quindi il DELETE e'' definitivo (un atto mai eseguito e'' una PROPOSTA, non un fatto); e cancellare RIAPRE la rigenerazione, perche'' l''«atto unico» di fn_fondo_fattura_proponibile guarda se un atto esiste in qualunque stato. ⚠️ Il blocco «distinta CHIUSA» guarda anche le righe non attive: una riga archiviata in una distinta chiusa resta un fatto. ⚠️ E'' un''operazione TECNICA sul ciclo di vita della figlia e NON una reazione ai pagamenti: nessun incasso la chiama e nessun incasso deve chiamarla. ⚠️ Firma invariata (deleted_source, deleted_fondi): il conteggio delle righe contabili lo espone fn_cancella_fondo_fattura, e nessun consumatore lo chiede qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
