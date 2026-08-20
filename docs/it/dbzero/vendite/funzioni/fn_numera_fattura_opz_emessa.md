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
    v_is_numbered  BOOLEAN;
    v_reset        vendite.registri_fatturazione.reset_policy%TYPE;
    v_data         vendite.fatture.data%TYPE;
    v_registro_id  vendite.fatture.registro_id%TYPE;
    v_anno         vendite.fatture.anno%TYPE;
    v_mese         SMALLINT;
    v_serie        vendite.fatture.serie%TYPE;
    v_numero       vendite.fatture.numero%TYPE;
    v_stato_emessa_id config.stati_doc_fiscale.id%TYPE;
    -- ⚠️ `integer` e `text` espliciti: sono un CONTEGGIO e un'ETICHETTA, non il
    --    valore di una colonna. Non c'e' niente da ancorare, e va detto invece
    --    di sembrare una dimenticanza.
    v_n_bloccanti     integer;
    v_primo_bloccante text;
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
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_numera_fattura_opz_emessa', 'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
            jsonb_build_object('fattura_id',      p_fattura_id,
                               'bloccanti',       v_n_bloccanti,
                               'primo_bloccante', v_primo_bloccante),
            NULL::uuid,
            p_fattura_id::text, v_primo_bloccante);
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
IS 'Assegna numero fattura (idempotente) e opzionalmente imposta stato EMESSA. ⭐ rev 2026-08-21: rifiuta di numerare un documento che RETTIFICA le righe di una fattura ancora senza numero (E_FATTURA_RETTIFICATA_SENZA_NUMERO). Non e'' cronologia: una nota di credito deve citare numero e data del documento corretto nel blocco DatiFattureCollegate della TD04, e con il padre senza numero quel blocco non e'' compilabile — la nota nascerebbe gia'' inadatta allo SDI. Il rifiuto arriva PRIMA di consumare un numero. ⚠️ Il predicato e'' PER RIGA (fatture_righe.riga_rettificata_id -> riga -> fattura): una nota puo'' rettificare righe di fatture diverse e ne basta UNA senza numero. ⭐ NON guarda la natura del documento: una nota di DEBITO che rettifica ha lo stesso problema, e una fattura ordinaria non ha righe con riga_rettificata_id — il predicato sulle righe copre tutto senza bloccare i casi normali. Non usa vendite.fatture_rettifiche perche'' quel ponte lo popola un task che gira DOPO la numerazione. ⛔ FAIL-CLOSED sulla visibilita'': fatture e fatture_righe hanno la RLS e la funzione e'' SECURITY INVOKER, quindi i JOIN sono LEFT e una riga il cui padre non e'' visibile conta come BLOCCANTE — il predicato e'' «non posso dimostrare che sia numerata», non «risulta non numerata». ⚠️ La guardia sta DOPO il ritorno idempotente: un documento gia'' numerato continua a rispondere con i suoi valori, altrimenti un secondo giro romperebbe cio'' che il primo ha gia'' fatto bene. ⚠️ CHI CHIAMA DEVE NUMERARE PRIMA I PADRI: il giro di lotto e'' fail-fast (una fattura che rifiuta ferma lo step). Oggi regge perche'' il backend ordina per f.id e la fattura rettificata e'' sempre piu'' vecchia della nota — la merce dev''essere gia'' stata fatturata perche'' l''accredito sia possibile — ma e'' un invariante implicito, non una garanzia scritta.';
```

---
{% include-markdown "signature-core.md" %}
