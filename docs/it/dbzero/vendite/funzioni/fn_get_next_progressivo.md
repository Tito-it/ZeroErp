{% include-markdown "it/dbzero/vendite/manual/fn_get_next_progressivo.md" %}
# ⚙️ Funzione `fn_get_next_progressivo`

```sql
CREATE FUNCTION fn_get_next_progressivo(p_registro_id bigint, p_data date, p_serie text, p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_serie text DEFAULT NULL::text, p_fattura_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_anno       vendite.registri_fatturazione_progressivi.anno%TYPE;
    -- ⚠️ Fermo a 0 finche' MENSILE non esiste: vedi il COMMENT
    --    della colonna e la D-1 del brief.
    v_mese       vendite.registri_fatturazione_progressivi.mese%TYPE := 0;
    v_serie      TEXT := COALESCE(p_serie, '');
    v_last       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    v_next       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    -- Il pavimento: la data sotto la quale non si puo' scendere.
    v_pavimento  vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    v_ultima_id  vendite.fatture.id%TYPE;
    v_bersagli   jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Consegnare il prossimo numero del sezionale, e rifiutare
    --   se la data del documento e' anteriore all'ultima gia'
    --   numerata sullo stesso (registro, serie).
    --
    -- Regole:
    --   - il controllo sta SOTTO il lock, o e' soggetto a corsa;
    --   - il lock ha lo STESSO perimetro del controllo;
    --   - la stessa data e' ammessa (>=, non >).
    -- =========================================================

    -- Guard di parametro, uno per parametro: un id nullo o non
    -- positivo, o una data assente, non escono da nessuna
    -- interfaccia — li produce solo un chiamante rotto, ed e' per
    -- questo che il codice e' TECNICO.
    IF p_registro_id IS NULL OR p_registro_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_next_progressivo',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'registro_id obbligatorio e maggiore di zero',
                'p_registro_id', p_registro_id),
            NULL::uuid,
            'vendite.fn_get_next_progressivo',
            'p_registro_id (obbligatorio, maggiore di zero)');
    END IF;

    IF p_data IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_next_progressivo',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'data documento obbligatoria',
                'p_registro_id', p_registro_id),
            NULL::uuid,
            'vendite.fn_get_next_progressivo',
            'p_data (obbligatorio)');
    END IF;

    v_anno := vendite.fn_get_anno_registro(p_data);

    -- ─── IL LOCK ──────────────────────────────────────────────
    -- 🔴 La chiave NON porta l'anno, e non e' una svista.
    --    Il cancello qui sotto legge il massimo ATTRAVERSO GLI
    --    ANNI: con l'anno nella chiave, due transazioni con date
    --    in anni diversi sullo stesso sezionale prenderebbero
    --    lock DIVERSI, leggerebbero lo stesso massimo e
    --    passerebbero entrambe — il cancello sarebbe aggirabile
    --    proprio nel caso che dichiara di coprire.
    --    Il perimetro del lock deve coincidere con quello del
    --    controllo che ci sta dentro.
    -- ⚠️ Forma a DUE argomenti (namespace + chiave): lo spazio a
    --    un argomento e' condiviso fra feature scorrelate.
    PERFORM pg_advisory_xact_lock(
        hashtext('registri_fatturazione_progressivi'),
        hashtext(p_registro_id::text || '|' || v_serie)
    );

    -- ─── ⭐ IL CANCELLO ───────────────────────────────────────
    -- Il massimo si prende su TUTTE le righe di contatore del
    -- sezionale, non su quella dell'anno corrente: altrimenti un
    -- documento retrodatato al 31/12 dell'anno scorso finirebbe
    -- nel contatore dell'anno scorso e passerebbe indisturbato,
    -- aprendo un numero in un anno gia' chiuso.
    SELECT max(rp.ultima_data)
      INTO v_pavimento
      FROM vendite.registri_fatturazione_progressivi rp
     WHERE rp.registro_id = p_registro_id
       AND rp.serie       = v_serie;

    -- ⚠️ `<` e non `<=`: la STESSA data dell'ultimo numerato e'
    --    ammessa, ed e' il caso piu' comune (decisione 7).
    IF v_pavimento IS NOT NULL AND p_data < v_pavimento THEN

        -- ⭐ Da qui in giu' si e' gia' deciso di rifiutare: il
        --    costo di comporre il bersaglio non tocca il percorso
        --    felice.
        v_bersagli := CASE
            WHEN p_fattura_id IS NOT NULL
            THEN jsonb_build_array(jsonb_build_object(
                     'tipo', 'FATTURA', 'id', p_fattura_id::text))
            ELSE '[]'::jsonb
        END;

        -- ⭐ L'ultima numerata si cerca PER DATA, non per numero:
        --    in un registro con inversioni gia' scritte «l'ultimo
        --    per numero» puo' portare una data diversa da quella
        --    che la frase nomina, e il messaggio si
        --    contraddirebbe da solo.
        -- ⚠️ vendite.fatture ha la RLS e questa funzione e'
        --    SECURITY INVOKER: se non e' visibile, qui non si
        --    trova nulla e il pulsante non nasce. A un documento
        --    che non si puo' aprire non si manda nessuno.
        SELECT f.id
          INTO v_ultima_id
          FROM vendite.fatture f
          JOIN vendite.registri_fatturazione r ON r.id = f.registro_id
         WHERE f.registro_id = p_registro_id
           AND COALESCE(f.serie, r.serie_default, '') = v_serie
           AND f.numero IS NOT NULL
           AND f.data   = v_pavimento
         ORDER BY f.anno DESC, f.numero DESC
         LIMIT 1;

        IF v_ultima_id IS NOT NULL THEN
            v_bersagli := v_bersagli || jsonb_build_array(
                jsonb_build_object('tipo', 'FATTURA',
                                   'id', v_ultima_id::text));
        END IF;

        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_next_progressivo',
            'E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO',
            jsonb_build_object(
                -- il campo che il frontend deve accendere
                'campo',          'data_documento',
                -- il resto e' diagnosi, per dbops.error_log
                'registro_id',    p_registro_id,
                'serie',          v_serie,
                'ultima_data',    v_pavimento,
                'data_richiesta', p_data,
                'fattura_id',     p_fattura_id)
            -- ⚠️ La chiave si OMETTE se non c'e' nessun bersaglio:
            --    un array vuoto e' malformato e lascerebbe un
            --    W_BERSAGLIO_MALFORMATO nel log per niente.
            || CASE WHEN jsonb_array_length(v_bersagli) > 0
                    THEN jsonb_build_object('bersaglio', v_bersagli)
                    ELSE '{}'::jsonb
               END,
            NULL::uuid,
            -- ⭐ Nella frase va SOLO la data dell'ultimo numerato:
            --    l'unico dato che serve a scegliere quella giusta.
            --    Formato italiano, perche' a leggerlo e' una
            --    persona. Nessun id, nessun nome di colonna.
            to_char(v_pavimento, 'DD/MM/YYYY'));
    END IF;

    -- ─── IL CONTATORE ─────────────────────────────────────────
    -- La riga e' per anno; il cancello guardava il sezionale.
    SELECT rp.last_numero
      INTO v_last
      FROM vendite.registri_fatturazione_progressivi rp
     WHERE rp.registro_id = p_registro_id
       AND rp.anno  = v_anno
       AND rp.mese  = v_mese
       AND rp.serie = v_serie
       FOR UPDATE;

    IF v_last IS NULL THEN
        INSERT INTO vendite.registri_fatturazione_progressivi
               (registro_id, anno, mese, serie, last_numero, attivo)
        VALUES (p_registro_id, v_anno, v_mese, v_serie, 0, true)
        RETURNING last_numero INTO v_last;
    END IF;

    v_next := v_last + 1;

    -- ⭐ `GREATEST` e non un'assegnazione secca: la memoria della
    --    sequenza non deve MAI arretrare. Il cancello ammette la
    --    data uguale, quindi due numeri consecutivi possono
    --    portare la stessa data — e in quel caso il pavimento
    --    resta dov'e'.
    UPDATE vendite.registri_fatturazione_progressivi
       SET last_numero = v_next,
           ultima_data = GREATEST(COALESCE(ultima_data, p_data), p_data)
     WHERE registro_id = p_registro_id
       AND anno  = v_anno
       AND mese  = v_mese
       AND serie = v_serie;

    RETURN v_next;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_serie text, p_fattura_id bigint)
IS 'Prossimo progressivo del sezionale, con il CANCELLO DI MONOTONIA sulla data. ⛔ Rifiuta (E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO) se p_data e'' anteriore all''ultima data gia'' numerata su (registro, serie); la data UGUALE e'' ammessa (decisione 7). ⭐ Il controllo sta QUI e SOTTO l''advisory lock per due ragioni: e'' l''unico punto NON AGGIRABILE — le tre vie che consumano un numero (lotto singolo, giro per competenza, backstop del worker di stampa) passano tutte di qui — e un controllo letto PRIMA del lock sarebbe soggetto a corsa, con due transazioni che leggono lo stesso massimo, passano entrambe e producono l''inversione che il cancello doveva impedire. 🔴 rev 2026-08-25: la chiave dell''advisory lock PERDE L''ANNO ed e'' ora (registro | serie). Il cancello legge il massimo ATTRAVERSO GLI ANNI, quindi con l''anno nella chiave due numerazioni con date in anni diversi sullo stesso sezionale avrebbero preso lock DIVERSI e passato entrambe: il perimetro del lock deve coincidere con quello del controllo che ci sta dentro, o il controllo e'' decorativo. Il FOR UPDATE sulla riga di contatore non basta, perche'' blocca la riga dell''anno corrente e non le altre. ⚠️ La chiave e'' (registro, serie) e non il solo registro: il modello ammette due serie sullo stesso registro (tipi_doc_fiscale_registri lo consente apposta) e sul solo registro due sequenze indipendenti si bloccherebbero a vicenda. ⚠️ Il massimo si legge dal CONTATORE e non da vendite.fatture: quella tabella ha la RLS e un max() sotto perimetro ristretto tornerebbe NULL, cioe'' «via libera» proprio quando non si sa. ⭐ ultima_data si aggiorna con GREATEST: la memoria della sequenza non arretra mai. ℹ️ Il BERSAGLIO ha due elementi — la fattura da numerare (p_fattura_id, che dice QUALE documento ha rifiutato dentro un giro di lotto) e l''ultima numerata del sezionale, cercata PER DATA e non per numero (in un registro con inversioni gia'' scritte «l''ultimo per numero» porterebbe una data diversa da quella che la frase nomina) e solo se visibile a chi opera. La chiave si omette se l''array sarebbe vuoto. Tutto questo gira SOLO nel ramo d''errore. ⚠️ p_serie resta `text` e non %TYPE: cambierebbe l''identita'' della funzione senza guadagno, e il valore che arriva e'' una serie gia'' risolta col COALESCE del chiamante. ⭐ I guard di parametro passano da E_PARAMETRO_INVALIDO — che portava nomi di variabili PL/pgSQL nella frase letta da una persona — a E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO), uno per parametro, col controllo <= 0 sugli id che prima mancava. Brief: docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md §4 DB-8.';
```

---
{% include-markdown "signature-core.md" %}
