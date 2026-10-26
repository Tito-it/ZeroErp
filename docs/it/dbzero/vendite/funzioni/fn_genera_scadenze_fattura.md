{% include-markdown "it/dbzero/vendite/manual/fn_genera_scadenze_fattura.md" %}
# ⚙️ Funzione `fn_genera_scadenze_fattura`

```sql
CREATE FUNCTION fn_genera_scadenze_fattura(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_scadenze_fattura(p_fattura_id bigint)
 RETURNS TABLE(deleted_rows integer, inserted_rows integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: (ri)genera il piano rate di UNA fattura a partire dal
--        termine di pagamento gia' presente in testata.
-- Regole: LEGGE e non risolve (C-13); formula a ramo unico
--         (C-5); DELETE+INSERT quindi idempotente; la
--         quadratura va sull'ultima rata; i tre casi della base
--         seguono D-D (NULL errore, zero senza rate) — e dal
--         2026-09-17 (P-5, D19-e) la base NEGATIVA ha UNA rata
--         col segno del documento, alla prima data del termine.
DECLARE
    v_data           vendite.fatture.data%TYPE;
    v_base           vendite.fatture.totale_a_pagare%TYPE;
    v_termine_id     vendite.fatture.termine_pagamento_id%TYPE;
    v_modalita_id    vendite.fatture.modalita_pagamento_id%TYPE;
    v_stato          config.stati_doc_fiscale.codice_interno%TYPE;
    v_congela        config.stati_doc_fiscale.congela_fiscale%TYPE;
    v_trovata        boolean := FALSE;
    v_num_rate       config.termini_pagamento.numero_rate%TYPE;
    v_intervallo     config.termini_pagamento.intervallo%TYPE;
    v_offset         config.termini_pagamento.primo_offset_giorni%TYPE;
    v_fine_mese      config.termini_pagamento.fine_mese%TYPE;
    v_ripartizione   config.termini_pagamento.ripartizione%TYPE;
    v_metodo         config.termini_pagamento.arrotondamento_metodo%TYPE;
    v_decimali       config.termini_pagamento.arrotondamento_decimali%TYPE;
    v_codice_interno config.termini_pagamento.codice_interno%TYPE;
    v_descrizione    config.termini_pagamento.descrizione%TYPE;
    v_modalita_cod   config.modalita_pagamento.codice%TYPE;
    v_snapshot       jsonb;
    v_deleted        integer := 0;
    v_inserted       integer := 0;
    v_quota          numeric;
    v_erogato        numeric := 0;
    v_importo        numeric;
    v_data_rata      date;
    n                integer;
BEGIN
    -- Guard: id numerico obbligatorio e positivo (linee-guida-sql).
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id),
            NULL::uuid, 'p_fattura_id obbligatorio e > 0'
        );
    END IF;

    SELECT TRUE, f.data, f.totale_a_pagare, f.termine_pagamento_id,
           f.modalita_pagamento_id, s.codice_interno, s.congela_fiscale
      INTO v_trovata, v_data, v_base, v_termine_id, v_modalita_id, v_stato, v_congela
      FROM vendite.fatture f
      LEFT JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
     WHERE f.id = p_fattura_id;

    IF NOT v_trovata THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_VALORE_MANCANTE',
            jsonb_build_object('fattura_id', p_fattura_id),
            NULL::uuid, concat('fattura non trovata per id ', p_fattura_id)
        );
    END IF;

    -- D-F: oltre la soglia il documento e' uno snapshot fiscale.
    -- Stessa soglia (per codice_interno) del guard satelliti di 1.1:
    -- qui si solleva con il codice giusto invece di lasciar fallire
    -- la DELETE piu' sotto su un errore di trigger.
    -- ⭐ LA SOGLIA E' UN DATO, non una lista scritta qui (D33).
    --    Fino al 2026-08-30 questa funzione portava la propria copia di
    --    `NOT IN ('DRAFT','EMESSA')`. Erano OTTO copie della stessa frase,
    --    e `config.stati_doc_fiscale.congela_fiscale` era nata (I10) proprio
    --    per toglierle: era stata collegata a un solo lettore.
    -- ⚠️ Il comportamento NON cambia: verificato che sui sei stati esistenti
    --    colonna e lista dicono la stessa cosa. Cambia la SEDE, cioe' quante
    --    cose vanno toccate il giorno che il confine si sposta - da otto a una.
    -- ⚠️ E il trattamento dello STATO MANCANTE resta identico a prima: e' una
    --    decisione di questa funzione, non della soglia.
    -- ⚠️ `IS TRUE` e non un test nudo, e non e' pignoleria: la vecchia forma
    --    era `v_stato IS NOT NULL AND v_stato NOT IN (...)`, cioe' con lo stato
    --    NON risolvibile la funzione LASCIAVA PASSARE. `v_congela IS TRUE` e'
    --    falso quando la colonna e' NULL, quindi quel ramo resta identico.
    --    Non si e' colta l'occasione per renderlo fail-closed: sarebbe un
    --    cambiamento di comportamento nascosto dentro un lavoro di sede.
    IF v_congela IS TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_FATTURA_BLOCCATA',
            jsonb_build_object('fattura_id', p_fattura_id, 'stato', v_stato,
                               'soglia', 'congela_fiscale'),
            NULL::uuid, p_fattura_id::text, v_stato
        );
    END IF;

    -- C-13: si LEGGE. Un termine mancante e' un difetto a monte
    -- (la catena ha un default), non un caso da compensare qui.
    IF v_termine_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_TERMINE_MANCANTE',
            jsonb_build_object('fattura_id', p_fattura_id,
                               -- ⭐ Il bersaglio, su entrambi i rifiuti del piano
                               --    rate: si arriva qui dentro il giro di lotto,
                               --    e la fattura da sistemare non e' quella che
                               --    l'operatore ha davanti.
                               'bersaglio', jsonb_build_array(
                                   jsonb_build_object('tipo', 'FATTURA',
                                                      'id', p_fattura_id::text))),
            NULL::uuid, p_fattura_id::text
        );
    END IF;

    SELECT tp.numero_rate, tp.intervallo, tp.primo_offset_giorni, tp.fine_mese,
           tp.ripartizione, tp.arrotondamento_metodo, tp.arrotondamento_decimali,
           tp.codice_interno, tp.descrizione
      INTO v_num_rate, v_intervallo, v_offset, v_fine_mese,
           v_ripartizione, v_metodo, v_decimali, v_codice_interno, v_descrizione
      FROM config.termini_pagamento tp
     WHERE tp.id = v_termine_id;

    IF v_num_rate IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('termine_pagamento_id', v_termine_id, 'fattura_id', p_fattura_id),
            NULL::uuid, concat('termine di pagamento ', v_termine_id, ' inesistente')
        );
    END IF;

    -- Seconda linea: il CHECK del catalogo ammette solo UGUALI, quindi
    -- questo ramo si raggiunge solo aggirando il catalogo. Resta perche'
    -- un piano rate calcolato con una regola che non esiste sarebbe
    -- peggio di un errore.
    IF v_ripartizione IS DISTINCT FROM 'UGUALI' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_TERMINE_INVALIDO',
            jsonb_build_object('fattura_id', p_fattura_id, 'termine_pagamento_id', v_termine_id,
                               'ripartizione', v_ripartizione),
            NULL::uuid, p_fattura_id::text, v_termine_id::text,
            concat('ripartizione non gestita: ', v_ripartizione)
        );
    END IF;

    -- D-D caso 1: la base non c'e'. E' un passo eseguito fuori ordine
    -- (i totali si calcolano prima), non un documento particolare.
    IF v_base IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_BASE_NON_PRONTA',
            jsonb_build_object('fattura_id', p_fattura_id,
                               -- ⭐ Il bersaglio, su entrambi i rifiuti del piano
                               --    rate: si arriva qui dentro il giro di lotto,
                               --    e la fattura da sistemare non e' quella che
                               --    l'operatore ha davanti.
                               'bersaglio', jsonb_build_array(
                                   jsonb_build_object('tipo', 'FATTURA',
                                                      'id', p_fattura_id::text))),
            NULL::uuid, p_fattura_id::text
        );
    END IF;

    -- Idempotenza: si riparte sempre da zero. La DELETE sta PRIMA dei
    -- casi a base non positiva, cosi' una fattura che diventa
    -- interamente coperta da acconti PERDE le rate che aveva invece di
    -- tenersele senza che nessuno lo dica.
    DELETE FROM vendite.fatture_scadenze WHERE fattura_id = p_fattura_id;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    -- D-D caso 2: coperta da acconti. Documento normale, nessun log.
    IF v_base = 0 THEN
        RETURN QUERY SELECT v_deleted, 0;
        RETURN;
    END IF;

    -- D-D caso 3, riscritto il 2026-09-17 (P-5, D19-e — Tid: «la nota di
    -- credito ha una rata sola»): saldo a favore del cliente → UNA rata,
    -- importo = la base col suo segno, data = la PRIMA del termine (Q-C:
    -- primo_offset e fine_mese come per ogni documento, nessuna seconda
    -- regola). ⭐ Si ottiene senza un secondo ramo: v_num_rate := 1 e il
    -- loop sotto fa il resto — data dal termine, snapshot, quadratura
    -- esatta (n = v_num_rate → v_importo = v_base). Il CHECK che vietava
    -- il negativo e' stato tolto nello stesso giro (20260917-11): la
    -- coerenza di segno la presidia la numerazione (somma rate = totale).
    -- ⚠️ La nota NON critica resta (Q-D): a volte e' corretto, a volte e'
    -- un fondo configurato male, e la differenza la vede una persona.
    IF v_base < 0 THEN
        v_num_rate := 1;
        INSERT INTO vendite.fatture_log (
                    fattura_id, data_ora, messaggio,
                    status, disabilitato, meta)
        VALUES (p_fattura_id, now(),
                format('Totale a pagare negativo (%s): generata una rata unica di credito.', v_base),
                'W', FALSE,
                jsonb_build_object(
                    'task',              'genera_scadenze_lotto',
                    'source',            'fn_genera_scadenze_fattura',
                    -- ⭐ Codice DICHIARATO, non catturato: qui non c'e'
                    --    nessun errore altrui: la condizione l'ha vista
                    --    questa funzione. E' un W_ perche' non si
                    --    solleva — si registra e il giro prosegue.
                    'error_code',        'W_SCADENZE_TOTALE_NEGATIVO',
                    'totale_a_pagare',   v_base,
                    'termine_pagamento_id', v_termine_id,
                    'rata_unica_credito', true));
    END IF;

    -- Snapshot del termine: i VALORI, con l'id accanto come
    -- provenienza. Se domani il catalogo cambia, questa fattura
    -- continua a spiegare le rate che ha.
    SELECT mp.codice INTO v_modalita_cod
      FROM config.modalita_pagamento mp WHERE mp.id = v_modalita_id;

    v_snapshot := jsonb_strip_nulls(jsonb_build_object(
        'termine_pagamento_id',    v_termine_id,
        'codice_interno',          v_codice_interno,
        'descrizione',             v_descrizione,
        'numero_rate',             v_num_rate,
        'primo_offset_giorni',     v_offset,
        'intervallo',              v_intervallo,
        'fine_mese',               v_fine_mese,
        'ripartizione',            v_ripartizione,
        'arrotondamento_metodo',   v_metodo,
        'arrotondamento_decimali', v_decimali,
        'modalita_pagamento_id',   v_modalita_id,
        'modalita_codice',         v_modalita_cod,
        -- P-5: sulla nota di credito il piano e' UNA rata, qualunque
        -- numero_rate dica il termine: lo snapshot lo dichiara (NULL
        -- sui documenti positivi, e jsonb_strip_nulls lo toglie).
        'rata_unica_credito',      CASE WHEN v_base < 0 THEN true END));

    -- La quota nominale, arrotondata una volta sola con il building
    -- block unico del modello (script.fn_arrotonda_importo).
    v_quota := script.fn_arrotonda_importo(v_base / v_num_rate, v_decimali, v_metodo);

    FOR n IN 1..v_num_rate LOOP
        -- Formula a ramo unico: tutto in giorni.
        v_data_rata := v_data + (v_offset + (n - 1) * v_intervallo);

        -- `fine_mese`: la data risultante si sposta all'ultimo giorno
        -- del proprio mese. Il clamp lo fa PostgreSQL nativamente,
        -- quindi il caso a cavallo d'anno non ha codice dedicato.
        IF v_fine_mese THEN
            v_data_rata := (date_trunc('month', v_data_rata::timestamp)
                            + interval '1 month - 1 day')::date;
        END IF;

        IF n < v_num_rate THEN
            v_importo := v_quota;
            v_erogato := v_erogato + v_quota;
        ELSE
            -- Quadratura: l'ultima rata assorbe la differenza, cosi'
            -- la somma delle rate e' ESATTAMENTE la base.
            v_importo := v_base - v_erogato;

            -- ⚠️ Solo sulla base POSITIVA: sulla negativa (una rata sola,
            --    P-5) v_importo = v_base per costruzione. Prima del
            --    2026-09-17 qui si parlava del CHECK sull'importo, che non
            --    c'e' piu': la diagnosi vera resta il termine, non la fattura.
            IF v_base > 0 AND v_importo < 0 THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_TERMINE_INVALIDO',
                    jsonb_build_object('fattura_id', p_fattura_id,
                                       'termine_pagamento_id', v_termine_id,
                                       'base', v_base, 'numero_rate', v_num_rate,
                                       'quota_arrotondata', v_quota,
                                       'ultima_rata', v_importo),
                    NULL::uuid, p_fattura_id::text, v_termine_id::text,
                    'l''arrotondamento delle prime rate supera la base: ultima rata negativa'
                );
            END IF;
        END IF;

        INSERT INTO vendite.fatture_scadenze (
                    fattura_id, numero_rata, data_scadenza, importo, meta)
        VALUES (p_fattura_id, n, v_data_rata, v_importo,
                jsonb_strip_nulls(jsonb_build_object(
                    'modalita_codice',        v_modalita_cod,
                    'termine_codice_interno', v_codice_interno,
                    'rata_unica_credito',     CASE WHEN v_base < 0 THEN true END)));
        v_inserted := v_inserted + 1;
    END LOOP;

    UPDATE vendite.fatture f
       SET termine_pagamento_snapshot = v_snapshot,
           data_update = now(), user_update = current_user
     WHERE f.id = p_fattura_id;

    RETURN QUERY SELECT v_deleted, v_inserted;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_scadenze_fattura(p_fattura_id bigint)
IS 'Fase 4.1 — (ri)genera il piano rate di una fattura. LEGGE il termine dalla testata e non lo risolve (C-13: la catena unica e'' fn_resolve_termini_pagamento, e il termine arriva qui passando dalla chiave). Formula a ramo unico dopo la riforma D-E: data = fattura.data + primo_offset_giorni + (n-1)*intervallo, in giorni, con spostamento a fine mese se richiesto; importo = base/numero_rate arrotondato con script.fn_arrotonda_importo (building block unico) e quadratura sull''ULTIMA rata, cosi'' la somma e'' esattamente la base. DELETE+INSERT: rieseguire ricostruisce lo stesso piano invece di sommarcisi, e la DELETE precede i casi a base non positiva perche'' una fattura diventata interamente coperta da acconti deve PERDERE le rate che aveva. I tre casi della base seguono D-D: NULL = passo fuori ordine (E_SCADENZE_BASE_NON_PRONTA), zero = coperta da acconti (zero rate, nessun log), negativa = saldo a favore del cliente (zero rate, log NON critico). Oltre la soglia DRAFT/EMESSA solleva E_SCADENZE_FATTURA_BLOCCATA (D-F): il filtro «salta senza fallire» spetta al wrapper di lotto. Scrive in testata termine_pagamento_snapshot con i VALORI del termine e non il solo id, perche'' una fattura emessa deve continuare a spiegare le proprie rate anche se il catalogo cambia. ⭐ rev 2026-08-21 (cantiere brief-db-liste-drawer-lotto, L1/P-5): la nota di avviso sul totale a pagare negativo dichiara W_SCADENZE_TOTALE_NEGATIVO in meta->>''error_code''. ⚠️ Cambia specie rispetto ai tre changeSet gemelli dello stesso giro (fn_log_pipeline_fase, fn_snapshot_fattura_lotto, fn_genera_scadenze_lotto): quelli CATTURANO un errore altrui in un ramo EXCEPTION e ne prendono il codice da CONSTRAINT_NAME, qui non c''e'' niente da catturare — la condizione la vede questa funzione, e il codice si DICHIARA. E'' un W_ perche'' non si solleva mai: si registra e il giro prosegue (un W_ sollevato sarebbe un HTTP 500). ⛔ Il codice NON ha una entry in config.messaggi_errore, di proposito e per decisione: questo punto scrive la frase direttamente in vendite.fatture_log.messaggio e non passa da script.fn_log_and_raise_error, quindi un messaggio a catalogo sarebbe una seconda copia della stessa frase che nessuno compone. La forma e'' prevista dal disegno: la FK va da messaggi_errore verso codici_errore, quindi un codice senza figli e'' legittimo mentre un messaggio senza padre no. ⭐ rev 2026-08-24: i due rifiuti del piano rate (E_SCADENZE_TERMINE_MANCANTE, E_SCADENZE_BASE_NON_PRONTA) portano il BERSAGLIO sulla fattura. Si arriva qui dentro il giro di lotto, e la fattura da sistemare non e'' quella che l''operatore ha davanti. Brief: brief-db-bersaglio-errore.md §6 L6. ⭐ rev 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.6, P-5 / D19-e, decisione di Tid): la base NEGATIVA genera UNA rata col segno del documento (importo = totale_a_pagare), alla prima data del termine (primo_offset e fine_mese come per ogni documento: nessuna seconda regola, Q-C); si ottiene con v_num_rate := 1 e il loop di sempre. Il CHECK chk_fatture_scadenze_importo_pos e'''' stato tolto nello stesso giro (20260917-11): la coerenza di segno la presidia la numerazione (somma rate = totale a pagare, condizioni 3-4 di fn_assign_numero_fattura riscritte sul <> 0). La nota W_SCADENZE_TOTALE_NEGATIVO RESTA, riformulata (Q-D). Perche'''': una riga contabile SENZA rata non incontra nessuna capienza (il guard esce su scadenza_id IS NULL) — finche'''' la nota di credito non aveva una rata, pagarla o compensarla entrava in silenzio; con la rata passa dal guard di D14-c come tutto il resto. Lo snapshot in testata e il meta della rata dichiarano rata_unica_credito = true.';
```

</div>

---
{% include-markdown "signature-core.md" %}
