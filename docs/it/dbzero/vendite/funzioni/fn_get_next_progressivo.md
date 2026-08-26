{% include-markdown "it/dbzero/vendite/manual/fn_get_next_progressivo.md" %}
# ⚙️ Funzione `fn_get_next_progressivo`

```sql
CREATE FUNCTION fn_get_next_progressivo(p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text, p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text DEFAULT NULL::text, p_fattura_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_anno       vendite.registri_fatturazione_progressivi.anno%TYPE;
    -- ⚠️ Fermo a 0 finche' MENSILE non esiste: vedi il COMMENT
    --    della colonna.
    v_mese       vendite.registri_fatturazione_progressivi.mese%TYPE := 0;
    v_serie      TEXT := COALESCE(p_serie, '');
    v_last       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    v_next       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    -- Il pavimento EFFETTIVO: la data sotto la quale non si puo'
    -- scendere, comunque ci si arrivi.
    v_pavimento  vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    -- ⚠️ `text`: non riflette nessuna colonna. SEQUENZA o EMISSIONE.
    v_origine    text;
    v_competenza vendite.fatture.competenza_mese%TYPE;
    v_ultima_id  vendite.fatture.id%TYPE;
    v_bersagli   jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Consegnare il prossimo numero del sezionale, e rifiutare
    --   se la data del documento sta sotto il PAVIMENTO
    --   EFFETTIVO — che e' il maggiore fra la sequenza gia'
    --   emessa e il limite di emissione.
    --
    -- Regole:
    --   - il controllo sta SOTTO il lock, o e' soggetto a corsa;
    --   - il lock ha lo STESSO perimetro del controllo;
    --   - la stessa data e' ammessa (>=, non >);
    --   - il codice dell'errore lo sceglie il pavimento che ha
    --     morso, e la frase nomina quello EFFETTIVO.
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

    -- ⭐ LA COMPETENZA, O IL SUO RIPIEGO. L'esenzione della
    --    differita e' una proprieta' DELLA DATA — «un documento
    --    datato l'ultimo giorno del mese M si emette fino al
    --    giorno G di M+1» — quindi dal mese della data si ricava
    --    la stessa risposta per ogni documento nato dalla
    --    politica. Sulle fatture nate prima del 2026-08-26 la
    --    colonna e' NULL, e questo e' il comportamento di allora.
    -- ⛔ NON si legge dal lotto: quello ha la RLS, e da dentro una
    --    SECURITY INVOKER un lotto invisibile darebbe competenza
    --    NULL e via libera — fail-open nel punto non aggirabile.
    v_competenza := COALESCE(p_competenza_mese,
                             date_trunc('month', p_data)::date);

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
    -- ⭐ rev 2026-08-26: il pavimento arriva COMPOSTO — sequenza
    --    E limite di emissione — da una sede sola, che dice anche
    --    QUALE dei due ha vinto. Prima qui c'era un
    --    `max(ultima_data)` scritto a mano, cioe' una delle tre
    --    copie della stessa regola.
    -- ⚠️ La lettura resta SOTTO il lock: la parte di sequenza
    --    legge il contatore, ed e' proprio quella che va
    --    serializzata.
    SELECT pv.pavimento, pv.origine
      INTO v_pavimento, v_origine
      FROM vendite.fn_get_pavimento_data_documento(
               p_registro_id, v_serie, v_competenza) pv;

    -- ⚠️ `<` e non `<=`: la STESSA data del pavimento e' ammessa,
    --    ed e' il caso piu' comune.
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

        -- ─── Ramo LIMITE DI EMISSIONE ────────────────────────
        -- ⛔ Nessun secondo bersaglio: dietro il limite non c'e'
        --    nessun documento da aprire, e un pulsante verso il
        --    nulla e' peggio di nessun pulsante.
        IF v_origine = 'EMISSIONE' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_get_next_progressivo',
                'E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE',
                jsonb_build_object(
                    -- il campo che il frontend deve accendere
                    'campo',          'data_documento',
                    -- il resto e' diagnosi, per dbops.error_log
                    'registro_id',    p_registro_id,
                    'serie',          v_serie,
                    'pavimento',      v_pavimento,
                    'origine',        v_origine,
                    'competenza',     v_competenza,
                    'data_richiesta', p_data,
                    'fattura_id',     p_fattura_id)
                || CASE WHEN jsonb_array_length(v_bersagli) > 0
                        THEN jsonb_build_object('bersaglio', v_bersagli)
                        ELSE '{}'::jsonb
                   END,
                NULL::uuid,
                -- ⭐ Nella frase va il pavimento EFFETTIVO, in
                --    formato italiano: a leggerlo e' una persona.
                to_char(v_pavimento, 'DD/MM/YYYY'));
        END IF;

        -- ─── Ramo SEQUENZA (e pareggio, che va a SEQUENZA) ───
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
                'campo',          'data_documento',
                'registro_id',    p_registro_id,
                'serie',          v_serie,
                'ultima_data',    v_pavimento,
                'origine',        v_origine,
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

COMMENT ON FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text, p_fattura_id bigint)
IS 'Prossimo progressivo del sezionale, con il CANCELLO sulla data. ⛔ Rifiuta se p_data sta sotto il PAVIMENTO EFFETTIVO, che dal 2026-08-26 e'' il MAGGIORE fra due: la sequenza gia'' emessa su (registro, serie) e il LIMITE DI EMISSIONE del registro. La data UGUALE al pavimento e'' ammessa. ⭐ Il pavimento arriva COMPOSTO da vendite.fn_get_pavimento_data_documento — una sede sola — e non piu'' da un max(ultima_data) scritto qui: prima era una delle tre copie della stessa regola. ⭐ DUE CODICI ERRORE, e li sceglie `origine`: E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO quando a mordere e'' la sequenza, E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE quando e'' il limite. Sono due rimedi diversi — risalire alla fattura che porta quel numero, oppure avvicinare la data a oggi — e dire il primo quando vale il secondo manda a cercare la cosa sbagliata. A parita'' di data vince SEQUENZA, che puo'' portare un bersaglio. ⛔ LA FRASE NOMINA IL PAVIMENTO EFFETTIVO, non quello di origine: fino al 2026-08-25 nominava quello di sequenza perche'' era l''unico, e con due pavimenti direbbe all''operatore di scegliere una data CHE VERREBBE RIFIUTATA DI NUOVO. ⭐ rev 2026-08-26: arriva p_competenza_mese, OBBLIGATORIO e in TERZA posizione (i parametri con DEFAULT stanno in coda). Gliela passa fn_assign_numero_fattura, che LEGGE GIA'' la riga della fattura per numerarla: una colonna in piu'' in una SELECT che c''e''. ⛔ NON si legge qui dal lotto: vendite.fatturazione_lotti ha la RLS e questa funzione e'' SECURITY INVOKER — un lotto fuori perimetro darebbe competenza NULL e via libera, cioe'' un presidio FAIL-OPEN nel punto che esiste apposta per non esserlo. ⚠️ RIPIEGO su date_trunc(''month'', p_data) quando la competenza e'' NULL (fatture nate prima del 2026-08-26): l''esenzione differita e'' una proprieta'' DELLA DATA, quindi la risposta e'' la stessa per ogni documento nato dalla politica. ⛔ Il prezzo, dichiarato: col ripiego il cancello non distingue un 31/07 che e'' davvero di luglio da uno che e'' di giugno — chi la competenza vera ce l''ha e'' la porta di dichiarazione, dove il controllo resta STRETTO (decisione D-7), e la differenza di severita'' e'' scritta in entrambi i COMMENT. ⭐ Il controllo sta QUI e SOTTO l''advisory lock: e'' l''unico punto NON AGGIRABILE — le tre vie che consumano un numero passano tutte di qui — e un controllo letto PRIMA del lock sarebbe soggetto a corsa. 🔴 La chiave del lock PERDE L''ANNO ed e'' (registro | serie): il cancello legge il massimo ATTRAVERSO GLI ANNI, quindi con l''anno nella chiave due numerazioni con date in anni diversi avrebbero preso lock DIVERSI e passato entrambe. Il FOR UPDATE sulla riga di contatore non basta, perche'' blocca la riga dell''anno corrente e non le altre. ⚠️ Il massimo si legge dal CONTATORE e non da vendite.fatture: quella tabella ha la RLS e un max() sotto perimetro ristretto tornerebbe NULL, cioe'' «via libera» proprio quando non si sa. ⭐ ultima_data si aggiorna con GREATEST: la memoria della sequenza non arretra mai. ℹ️ Sul ramo SEQUENZA il bersaglio ha due elementi — la fattura da numerare e l''ultima numerata del sezionale, cercata PER DATA e non per numero e solo se visibile; sul ramo EMISSIONE ce n''e'' uno solo, perche'' dietro il limite non c''e'' nessun documento da aprire. Tutto questo gira SOLO nel ramo d''errore. ⚠️ p_serie resta `text` e non %TYPE: cambierebbe l''identita'' della funzione senza guadagno, e il valore che arriva e'' una serie gia'' risolta dal chiamante. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-10.';
```

---
{% include-markdown "signature-core.md" %}
