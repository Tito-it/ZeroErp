{% include-markdown "it/dbzero/vendite/manual/fn_genera_scadenze_fattura.md" %}
# ⚙️ Funzione `fn_genera_scadenze_fattura`

```sql
CREATE FUNCTION fn_genera_scadenze_fattura(p_fattura_id bigint)
```

**Definizione completa:**

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
--         seguono D-D (NULL errore, zero e negativo sono
--         documenti legittimi senza rate).
DECLARE
    v_data           vendite.fatture.data%TYPE;
    v_base           vendite.fatture.totale_a_pagare%TYPE;
    v_termine_id     vendite.fatture.termine_pagamento_id%TYPE;
    v_modalita_id    vendite.fatture.modalita_pagamento_id%TYPE;
    v_stato          config.stati_doc_fiscale.codice_interno%TYPE;
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
           f.modalita_pagamento_id, s.codice_interno
      INTO v_trovata, v_data, v_base, v_termine_id, v_modalita_id, v_stato
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
    IF v_stato IS NOT NULL AND v_stato NOT IN ('DRAFT', 'EMESSA') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_FATTURA_BLOCCATA',
            jsonb_build_object('fattura_id', p_fattura_id, 'stato', v_stato,
                               'soglia', 'DRAFT,EMESSA'),
            NULL::uuid, p_fattura_id::text, v_stato
        );
    END IF;

    -- C-13: si LEGGE. Un termine mancante e' un difetto a monte
    -- (la catena ha un default), non un caso da compensare qui.
    IF v_termine_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_fattura', 'E_SCADENZE_TERMINE_MANCANTE',
            jsonb_build_object('fattura_id', p_fattura_id),
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
            jsonb_build_object('fattura_id', p_fattura_id),
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

    -- D-D caso 3: saldo a favore del cliente. Nessuna rata (il CHECK
    -- vieta importi negativi) ma una nota NON critica: a volte e'
    -- corretto, a volte e' un fondo configurato male, e la differenza
    -- la vede una persona.
    IF v_base < 0 THEN
        INSERT INTO vendite.fatture_log (
                    fattura_id, data_ora, messaggio,
                    status, disabilitato, meta)
        VALUES (p_fattura_id, now(),
                format('Totale a pagare negativo (%s): nessun piano rate generato.', v_base),
                'W', FALSE,
                jsonb_build_object(
                    'task',              'genera_scadenze_lotto',
                    'source',            'fn_genera_scadenze_fattura',
                    'totale_a_pagare',   v_base,
                    'termine_pagamento_id', v_termine_id));
        RETURN QUERY SELECT v_deleted, 0;
        RETURN;
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
        'modalita_codice',         v_modalita_cod));

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

            IF v_importo < 0 THEN
                -- Vedi la nota in testa al file: sarebbe una violazione
                -- di chk_fatture_scadenze_importo_pos a meta' giro. La
                -- diagnosi vera e' il termine, non la fattura.
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
                    'termine_codice_interno', v_codice_interno)));
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
IS 'Fase 4.1 — (ri)genera il piano rate di una fattura. LEGGE il termine dalla testata e non lo risolve (C-13: la catena unica e'' fn_resolve_termini_pagamento, e il termine arriva qui passando dalla chiave). Formula a ramo unico dopo la riforma D-E: data = fattura.data + primo_offset_giorni + (n-1)*intervallo, in giorni, con spostamento a fine mese se richiesto; importo = base/numero_rate arrotondato con script.fn_arrotonda_importo (building block unico) e quadratura sull''ULTIMA rata, cosi'' la somma e'' esattamente la base. DELETE+INSERT: rieseguire ricostruisce lo stesso piano invece di sommarcisi, e la DELETE precede i casi a base non positiva perche'' una fattura diventata interamente coperta da acconti deve PERDERE le rate che aveva. I tre casi della base seguono D-D: NULL = passo fuori ordine (E_SCADENZE_BASE_NON_PRONTA), zero = coperta da acconti (zero rate, nessun log), negativa = saldo a favore del cliente (zero rate, log NON critico). Oltre la soglia DRAFT/EMESSA solleva E_SCADENZE_FATTURA_BLOCCATA (D-F): il filtro «salta senza fallire» spetta al wrapper di lotto. Scrive in testata termine_pagamento_snapshot con i VALORI del termine e non il solo id, perche'' una fattura emessa deve continuare a spiegare le proprie rate anche se il catalogo cambia.';
```

---
{% include-markdown "signature-core.md" %}
