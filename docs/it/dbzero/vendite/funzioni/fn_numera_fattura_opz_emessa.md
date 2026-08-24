{% include-markdown "it/dbzero/vendite/manual/fn_numera_fattura_opz_emessa.md" %}
# ⚙️ Funzione `fn_numera_fattura_opz_emessa`

```sql
CREATE FUNCTION fn_numera_fattura_opz_emessa(p_fattura_id bigint, p_set_emessa boolean, p_codice_interno_emessa character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_numera_fattura_opz_emessa(p_fattura_id bigint, p_set_emessa boolean DEFAULT true, p_codice_interno_emessa character varying DEFAULT 'EMESSA'::character varying)
 RETURNS TABLE(registro_id bigint, anno smallint, mese smallint, serie character varying, numero bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ `BOOLEAN` esplicito: e' l'esito di un controllo, non il valore
    --    di una colonna.
    v_is_numbered  BOOLEAN;
    v_reset        vendite.registri_fatturazione.reset_policy%TYPE;
    v_data         vendite.fatture.data%TYPE;
    v_registro_id  vendite.fatture.registro_id%TYPE;
    v_anno         vendite.fatture.anno%TYPE;
    -- ⚠️ `SMALLINT` esplicito, stessa ragione del `mese` in RETURNS:
    --    la colonna non esiste, il mese si ricava dalla data.
    v_mese         SMALLINT;
    v_serie        vendite.fatture.serie%TYPE;
    v_numero       vendite.fatture.numero%TYPE;
    v_stato_emessa_id config.stati_doc_fiscale.id%TYPE;
    -- ⚠️ `integer` e `text` espliciti: sono un CONTEGGIO e un'ETICHETTA, non il
    --    valore di una colonna. Non c'e' niente da ancorare, e va detto invece
    --    di sembrare una dimenticanza.
    --
    -- ⭐ Dal 24-08-2026 `v_n_bloccanti` non e' piu' solo diagnostica: e' il
    --    valore che riempie l'unico segnaposto del messaggio 937. Il conteggio
    --    e' l'unica cosa che la frase puo' dire su QUANTI documenti mancano
    --    quando i pulsanti sono al massimo cinque (linee-guida-sql §5).
    v_n_bloccanti     integer;
    -- ⭐ E `v_primo_bloccante` non e' piu' nella frase: resta nel context, cioe'
    --    in dbops.error_log, per chi diagnostica. Due lettori, due canali.
    v_primo_bloccante text;
    -- Il BERSAGLIO: l'array di {tipo,id} che il frontend trasforma in
    -- pulsanti. `jsonb` perche' e' la forma del context, non una colonna.
    v_bersagli        jsonb;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_numera_fattura_opz_emessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    IF p_set_emessa IS TRUE AND (p_codice_interno_emessa IS NULL OR btrim(p_codice_interno_emessa) = '') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_numera_fattura_opz_emessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_codice_interno_emessa', 'valore', p_codice_interno_emessa),
            NULL::uuid, 'p_codice_interno_emessa obbligatorio se p_set_emessa=true');
    END IF;

    -- Lock riga fattura (solo la riga fattura, alias f)
    --
    -- ⭐ E' ANCHE IL CANCELLO DI VISIBILITA' SU CUI POGGIA IL PRIMO BERSAGLIO:
    --    la RLS e' attiva e la funzione e' SECURITY INVOKER, quindi una fattura
    --    fuori dal perimetro di chi opera qui non si trova e si esce con
    --    E_FATTURA_NON_TROVATA. Arrivare alla guardia significa che
    --    `p_fattura_id` e' un documento che chi opera puo' aprire.
    SELECT f.numero IS NOT NULL, f.data, f.registro_id, r.reset_policy, f.anno, f.serie, f.numero
      INTO v_is_numbered, v_data, v_registro_id, v_reset, v_anno, v_serie, v_numero
      FROM vendite.fatture f
      JOIN vendite.registri_fatturazione r ON r.id = f.registro_id
     WHERE f.id = p_fattura_id FOR UPDATE OF f;

    IF v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_numera_fattura_opz_emessa', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id), NULL::uuid, p_fattura_id::text);
    END IF;

    -- Idempotente: se gia' numerata ritorna valori correnti
    IF v_is_numbered THEN
        v_mese := CASE WHEN v_reset = 'MENSILE' THEN EXTRACT(MONTH FROM v_data)::SMALLINT ELSE NULL END;
        RETURN QUERY SELECT v_registro_id, v_anno, v_mese, v_serie, v_numero;
        RETURN;
    END IF;

    -- --------------------------------------------------
    -- ⛔ IL RIFERIMENTO FISCALE DEVE ESISTERE PRIMA.
    --    Un documento che RETTIFICA le righe di un'altra fattura non si puo'
    --    numerare finche' quella fattura non ha un numero.
    --
    -- ⚠️ NON e' una questione di cronologia. Una nota di credito deve citare
    --    numero e data del documento corretto nel blocco DatiFattureCollegate
    --    della fattura elettronica (TD04): con il documento rettificato ancora
    --    senza numero quel blocco non e' compilabile, e la nota nascerebbe
    --    gia' inadatta a partire verso lo SDI. Il rifiuto arriva PRIMA di
    --    consumare un numero, che e' l'unica cosa che non si torna indietro.
    --
    -- ⚠️ IL PREDICATO E' PER RIGA, NON PER DOCUMENTO: una nota di credito puo'
    --    rettificare righe di fatture DIVERSE, e basta che UNA sia senza
    --    numero perche' il blocco fiscale resti incompleto.
    --
    -- ⭐ E NON GUARDA LA NATURA. Sarebbe stato naturale scrivere «se natura =
    --    NOTA_CREDITO allora...», ed e' sbagliato per due motivi: una nota di
    --    DEBITO che rettifica ha lo stesso identico problema, e una fattura
    --    ordinaria non ha righe con riga_rettificata_id — quindi il predicato
    --    sulle righe copre tutti i casi senza mai bloccare quelli normali.
    --    Il legame e' quello che esiste dalla generazione delle righe; il
    --    ponte documentale vendite.fatture_rettifiche lo popola un task che
    --    gira DOPO questa funzione, quindi qui sarebbe sempre vuoto.
    --
    -- ⛔ FAIL-CLOSED SULLA VISIBILITA'. vendite.fatture e vendite.fatture_righe
    --    hanno la RLS e questa funzione e' SECURITY INVOKER: una fattura
    --    rettificata fuori dal perimetro emittente di chi opera si legge come
    --    «non c'e'». I JOIN sono quindi LEFT e la riga senza padre visibile
    --    CONTA COME BLOCCANTE: il predicato non e' «risulta non numerata», e'
    --    «non posso dimostrare che sia numerata». Con dei JOIN interni uno zero
    --    avrebbe voluto dire «via libera» proprio nel caso in cui non si sa.
    --
    -- ⭐ 24-08-2026: `v_n_bloccanti` e' anche il valore che va nella frase.
    --    Un padre invisibile entra quindi nel CONTEGGIO ma non nel bersaglio,
    --    ed e' coerente: la frase dice quanti documenti mancano, i pulsanti
    --    dicono dove si puo' andare. Sono due domande diverse, come i due
    --    tipi di JOIN qui sotto.
    -- --------------------------------------------------
    SELECT count(DISTINCT COALESCE(rif.id::text, 'riga ' || fr.riga_rettificata_id::text))::integer,
           min(COALESCE(rif.id::text, 'riga ' || fr.riga_rettificata_id::text))
      INTO v_n_bloccanti, v_primo_bloccante
      FROM vendite.fatture_righe fr
      LEFT JOIN vendite.fatture_righe rr ON rr.id  = fr.riga_rettificata_id
      LEFT JOIN vendite.fatture      rif ON rif.id = rr.fattura_id
     WHERE fr.fattura_id = p_fattura_id
       AND fr.riga_rettificata_id IS NOT NULL
       AND (rif.id IS NULL OR rif.numero IS NULL);

    IF v_n_bloccanti > 0 THEN
        -- ⭐ IL BERSAGLIO, DUE RUOLI (24-08-2026, passo T-3b del brief).
        --    E' la forma che il §4.2 dichiarava dal primo giro — «il documento
        --    da numerare e la fattura rettificata» — ed e' la ragione per cui
        --    questa chiave e' un ARRAY. Il pilota ne emetteva uno solo.
        --
        --    1. IL DOCUMENTO DA NUMERARE, sempre e per PRIMO.
        --       ⭐ Senza di lui il T-3b non si potrebbe fare: dentro un giro di
        --          lotto l'errore arriva su una fattura fra molte, e tolti gli
        --          id dalla frase QUALE non lo direbbe piu' nessuno.
        --       ⭐ E' sempre presente per costruzione: se non fosse visibile,
        --          la SELECT ... FOR UPDATE qui sopra non l'avrebbe trovato e
        --          saremmo usciti con E_FATTURA_NON_TROVATA.
        --       ⭐ Ed e' PRIMO perche' il canale compatto tiene i primi cinque
        --          elementi per ordinalita': in testa, la cosa che dice «quale»
        --          sopravvive al tetto anche con sette padri bloccanti.
        --
        --    2. I PADRI BLOCCANTI, solo quelli VISIBILI, in ordine di id.
        --       ⛔ JOIN INTERNI, al contrario del predicato qui sopra, e non e'
        --          una svista: la guardia dev'essere fail-closed (un padre
        --          invisibile BLOCCA), il bersaglio dev'essere onesto (a un
        --          padre invisibile non si puo' mandare nessuno). Un pulsante
        --          in un vicolo cieco e' peggio di nessun pulsante — §4.3.
        --
        -- ⚠️ Niente piu' `CASE WHEN v_bersagli IS NULL`: con il documento in
        --    testa l'array ha SEMPRE almeno un elemento, quindi il ramo «chiave
        --    assente» del pilota non esiste piu'. Scritto perche' chi confronta
        --    i due changeSet non lo legga come una dimenticanza.
        --
        -- ⚠️ Gira solo qui dentro, cioe' solo quando l'errore parte davvero:
        --    sul percorso felice non costa niente.
        SELECT jsonb_build_array(
                   jsonb_build_object('tipo', 'FATTURA',
                                      'id',   p_fattura_id::text))
               || COALESCE(
                    (SELECT jsonb_agg(jsonb_build_object('tipo', 'FATTURA',
                                                         'id',   x.id::text)
                                      ORDER BY x.id)
                       FROM (SELECT DISTINCT rif.id
                               FROM vendite.fatture_righe fr
                               JOIN vendite.fatture_righe rr  ON rr.id  = fr.riga_rettificata_id
                               JOIN vendite.fatture      rif  ON rif.id = rr.fattura_id
                              WHERE fr.fattura_id = p_fattura_id
                                AND fr.riga_rettificata_id IS NOT NULL
                                AND rif.numero IS NULL) x),
                    '[]'::jsonb)
          INTO v_bersagli;

        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_numera_fattura_opz_emessa', 'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
            -- ⚠️ `primo_bloccante` resta QUI e non nella frase: nel ramo
            --    fail-closed non e' nemmeno un id di fattura (e' la stringa
            --    `riga <id>`), e non si nomina in chiaro una riga che il
            --    lettore non puo' aprire. Per chi diagnostica e' invece
            --    l'aggancio esatto, e dbops.error_log e' la sua sede.
            jsonb_build_object('fattura_id',      p_fattura_id,
                               'bloccanti',       v_n_bloccanti,
                               'primo_bloccante', v_primo_bloccante,
                               'bersaglio',       v_bersagli),
            NULL::uuid,
            -- ⭐ L'UNICO valore che entra nella frase, ed e' un CONTEGGIO, non
            --    un identificativo: «Documenti da numerare prima: 2». Non c'e'
            --    piu' niente da ricopiare in un campo di ricerca.
            v_n_bloccanti::text);
    END IF;

    -- Assegna numero
    SELECT t.registro_id, t.anno, t.mese, t.serie, t.numero
      INTO v_registro_id, v_anno, v_mese, v_serie, v_numero
      FROM vendite.fn_assign_numero_fattura(p_fattura_id) AS t;

    -- Opzionale: stato EMESSA
    IF p_set_emessa THEN
        SELECT id INTO v_stato_emessa_id
          FROM config.stati_doc_fiscale WHERE codice_interno = p_codice_interno_emessa LIMIT 1;

        IF v_stato_emessa_id IS NOT NULL THEN
            UPDATE vendite.fatture SET stato_doc_fiscale_id = COALESCE(stato_doc_fiscale_id, v_stato_emessa_id) WHERE id = p_fattura_id;
        END IF;
    END IF;

    RETURN QUERY SELECT v_registro_id, v_anno, v_mese, v_serie, v_numero;
END;
$function$

COMMENT ON FUNCTION vendite.fn_numera_fattura_opz_emessa(p_fattura_id bigint, p_set_emessa boolean, p_codice_interno_emessa character varying)
IS 'Assegna numero fattura (idempotente) e opzionalmente imposta stato EMESSA. ⭐ rev 2026-08-21: rifiuta di numerare un documento che RETTIFICA le righe di una fattura ancora senza numero (E_FATTURA_RETTIFICATA_SENZA_NUMERO). Non e'' cronologia: una nota di credito deve citare numero e data del documento corretto nel blocco DatiFattureCollegate della TD04, e con il padre senza numero quel blocco non e'' compilabile — la nota nascerebbe gia'' inadatta allo SDI. Il rifiuto arriva PRIMA di consumare un numero. ⚠️ Il predicato e'' PER RIGA (fatture_righe.riga_rettificata_id -> riga -> fattura): una nota puo'' rettificare righe di fatture diverse e ne basta UNA senza numero. ⭐ NON guarda la natura del documento: una nota di DEBITO che rettifica ha lo stesso problema, e una fattura ordinaria non ha righe con riga_rettificata_id — il predicato sulle righe copre tutto senza bloccare i casi normali. Non usa vendite.fatture_rettifiche perche'' quel ponte lo popola un task che gira DOPO la numerazione. ⛔ FAIL-CLOSED sulla visibilita'': fatture e fatture_righe hanno la RLS e la funzione e'' SECURITY INVOKER, quindi i JOIN sono LEFT e una riga il cui padre non e'' visibile conta come BLOCCANTE — il predicato e'' «non posso dimostrare che sia numerata», non «risulta non numerata». ⚠️ La guardia sta DOPO il ritorno idempotente: un documento gia'' numerato continua a rispondere con i suoi valori, altrimenti un secondo giro romperebbe cio'' che il primo ha gia'' fatto bene. ⚠️ CHI CHIAMA DEVE NUMERARE PRIMA I PADRI: il giro di lotto e'' fail-fast (una fattura che rifiuta ferma lo step). Oggi regge perche'' il backend ordina per f.id e la fattura rettificata e'' sempre piu'' vecchia della nota — la merce dev''essere gia'' stata fatturata perche'' l''accredito sia possibile — ma e'' un invariante implicito, non una garanzia scritta. ⭐ rev 2026-08-23: l''errore porta un BERSAGLIO (canale DATATYPE, via script.fn_log_and_raise_error). ⭐ rev 2026-08-24 (T-3b): l''ID ESCE DALLA PROSA. Il messaggio 937 passa da due segnaposto a UNO, che porta il CONTEGGIO dei bloccanti e non piu'' due chiavi interne; il bersaglio prende DUE RUOLI — il documento DA NUMERARE (sempre, e per PRIMO, cosi'' sopravvive al tetto di cinque elementi del canale compatto) e i padri bloccanti VISIBILI in ordine di id. ⭐ Il primo elemento c''e'' sempre per costruzione: se p_fattura_id non fosse visibile a chi opera, la SELECT ... FOR UPDATE non l''avrebbe trovato e si sarebbe usciti con E_FATTURA_NON_TROVATA. Senza quel primo bersaglio il T-3b non si sarebbe potuto fare: dentro un giro di lotto, tolti gli id dalla frase, QUALE fattura ha rifiutato non lo direbbe piu'' nessuno. ⛔ Il bersaglio dei padri resta a JOIN INTERNI contro i LEFT JOIN del predicato: un padre invisibile entra nel CONTEGGIO della frase ma NON fra i pulsanti, perche'' a un documento che non si puo'' aprire non si manda nessuno. ⚠️ La chiave `bersaglio` e'' ora incondizionata (l''array non e'' mai vuoto), quindi il CASE del pilota e'' sparito. ⚠️ `primo_bloccante` resta nel context per chi diagnostica: nel ramo fail-closed non e'' nemmeno un id di fattura. ⛔ Questo changeSet e'' inseparabile dalla riga 937 di 80_data/sql/config/messaggi_errore.csv. Brief: docs/it/dev/work-in-progress/brief-db-bersaglio-errore.md §7-ter, passo T-3b.';
```

---
{% include-markdown "signature-core.md" %}
