{% include-markdown "it/dbzero/vendite/manual/fn_get_next_progressivo.md" %}
# ⚙️ Funzione `fn_get_next_progressivo`

```sql
CREATE FUNCTION fn_get_next_progressivo(p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text, p_fattura_id bigint, p_famiglia_documento character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text DEFAULT NULL::text, p_fattura_id bigint DEFAULT NULL::bigint, p_famiglia_documento character varying DEFAULT 'FATTURA'::character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_anno       vendite.registri_fatturazione_progressivi.anno%TYPE;
    -- ⭐ La politica di azzeramento del sezionale, LETTA e non assunta.
    v_reset      vendite.registri_fatturazione.reset_policy%TYPE;
    v_serie      TEXT := COALESCE(p_serie, '');
    v_last       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    v_next       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    -- ⭐ Il valore da cui parte un secchio APPENA NATO: non piu' zero.
    v_seme       vendite.registri_fatturazione_progressivi.last_numero%TYPE;
    v_pavimento  vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    v_origine    text;
    v_competenza vendite.fatture.competenza_mese%TYPE;
    v_ultima_id  vendite.fatture.id%TYPE;
    v_bersagli   jsonb;
    -- ⭐ Il codice del ramo SEQUENZA lo sceglie la famiglia.
    v_codice_seq text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Consegnare il prossimo numero del sezionale, e rifiutare
    --   se la data del documento sta sotto il PAVIMENTO
    --   EFFETTIVO.
    --
    -- Regole:
    --   - il controllo sta SOTTO il lock, o e' soggetto a corsa;
    --   - il lock ha lo STESSO perimetro del controllo;
    --   - la stessa data e' ammessa (>=, non >);
    --   - il codice dell'errore lo sceglie il pavimento che ha
    --     morso E la famiglia del documento.
    --
    -- ⭐ rev 2026-08-31: arriva p_famiglia_documento. Cambia SOLO
    --   il ramo d'errore — il percorso felice non legge
    --   vendite.fatture e non l'ha mai fatto.
    -- =========================================================

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

    -- ⭐ LA COMPETENZA, O IL SUO RIPIEGO.
    -- ⛔ NON si legge dal lotto: quello ha la RLS, e da dentro una
    --    SECURITY INVOKER un lotto invisibile darebbe competenza
    --    NULL e via libera — fail-open nel punto non aggirabile.
    -- ℹ️ Sui documenti non fiscali la competenza non serve a
    --    niente (il limite di emissione non si applica), ma il
    --    ripiego costa nulla e tiene una sola forma di chiamata.
    v_competenza := COALESCE(p_competenza_mese,
                             date_trunc('month', p_data)::date);

    -- ─── ⭐ L'ANNO DEL SECCHIO, NON QUELLO DEL DOCUMENTO ──
    -- ⛔ Sono due cose diverse che si chiamano uguale:
    --    · l'anno del DOCUMENTO (fatture.anno, ddt.anno, ...) e'
    --      sempre l'anno solare, e lo compone
    --      vendite.fn_assegna_numero_documento;
    --    · l'anno del SECCHIO e' una chiave di contatore, e sotto
    --      reset_policy = 'NESSUNA' non esiste: c'e' un secchio
    --      solo, e vale 0.
    -- ⭐ Per questo vendite.fn_get_anno_registro NON e' stata
    --    toccata: risponde all'altra domanda, e ha quattro
    --    chiamanti che non c'entrano con questa.
    SELECT r.reset_policy INTO v_reset
      FROM vendite.registri_fatturazione r
     WHERE r.id = p_registro_id;

    -- ⚠️ Registro inesistente: qui non si decide. Si ripiega sul
    --    comportamento storico, e a dirlo sara' la FK del contatore
    --    piu' sotto — che e' il posto giusto.
    v_anno := CASE
        WHEN v_reset = 'NESSUNA' THEN 0::smallint
        ELSE vendite.fn_get_anno_registro(p_data)
    END;

    -- ─── IL LOCK ──────────────────────────────────────────
    -- 🔴 La chiave NON porta l'anno, e non e' una svista: il
    --    cancello legge il massimo ATTRAVERSO GLI ANNI, e con
    --    l'anno nella chiave due transazioni con date in anni
    --    diversi prenderebbero lock DIVERSI e passerebbero
    --    entrambe.
    -- ⚠️ Forma a DUE argomenti (namespace + chiave).
    PERFORM pg_advisory_xact_lock(
        hashtext('registri_fatturazione_progressivi'),
        hashtext(p_registro_id::text || '|' || v_serie)
    );

    -- ─── ⭐ IL CANCELLO ───────────────────────────────────
    -- ⚠️ La lettura resta SOTTO il lock: la parte di sequenza
    --    legge il contatore, ed e' quella che va serializzata.
    -- ⭐ Dal 20260831-05 il pavimento sa gia' che il limite di
    --    emissione vale sulla sola FATTURA: qui non si distingue
    --    niente, si chiede.
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
                     'tipo', p_famiglia_documento,
                     'id',   p_fattura_id::text))
            ELSE '[]'::jsonb
        END;

        -- ─── Ramo LIMITE DI EMISSIONE ────────────────────
        -- ⛔ Nessun secondo bersaglio: dietro il limite non c'e'
        --    nessun documento da aprire.
        -- ⛔ E questo ramo e' raggiungibile SOLO dalla famiglia
        --    FATTURA: dal 20260831-05 il pavimento di emissione
        --    non si applica alle altre. E' il motivo per cui il
        --    codice resta E_FATTURA_* senza un gemello.
        IF v_origine = 'EMISSIONE' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_get_next_progressivo',
                'E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE',
                jsonb_build_object(
                    'campo',          'data_documento',
                    'registro_id',    p_registro_id,
                    'serie',          v_serie,
                    'pavimento',      v_pavimento,
                    'origine',        v_origine,
                    'competenza',     v_competenza,
                    'data_richiesta', p_data,
                    'famiglia',       p_famiglia_documento,
                    'documento_id',   p_fattura_id)
                || CASE WHEN jsonb_array_length(v_bersagli) > 0
                        THEN jsonb_build_object('bersaglio', v_bersagli)
                        ELSE '{}'::jsonb
                   END,
                NULL::uuid,
                to_char(v_pavimento, 'DD/MM/YYYY'));
        END IF;

        -- ─── Ramo SEQUENZA (e pareggio, che va a SEQUENZA) ─
        -- ⭐ Il secondo bersaglio — «apri l'ultima numerata» —
        --    esiste SOLO per la fattura: per gli altri documenti
        --    quella lookup e' su un'altra tabella e non c'e'
        --    nessuna pagina a cui mandare. Un pulsante verso il
        --    nulla e' peggio di nessun pulsante.
        -- ⭐ L'ultima numerata si cerca PER DATA, non per numero:
        --    in un registro con inversioni gia' scritte «l'ultimo
        --    per numero» porterebbe una data diversa da quella
        --    che la frase nomina.
        -- ⚠️ vendite.fatture ha la RLS e questa funzione e'
        --    SECURITY INVOKER: se non e' visibile non si trova
        --    nulla e il pulsante non nasce.
        IF p_famiglia_documento = 'FATTURA' THEN
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
        END IF;

        -- ⭐ Il codice lo sceglie la FAMIGLIA: la frase del
        --    gemello non nomina la fattura, perche' a leggerla e'
        --    chi sta emettendo un DDT. ⛔ Riusare il codice della
        --    fattura manderebbe a cercare nel posto sbagliato:
        --    i consumatori di un messaggio si trovano dal NOME
        --    di chi lo solleva.
        v_codice_seq := CASE
            WHEN p_famiglia_documento = 'FATTURA'
            THEN 'E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO'
            ELSE 'E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO'
        END;

        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_next_progressivo',
            v_codice_seq,
            jsonb_build_object(
                'campo',          'data_documento',
                'registro_id',    p_registro_id,
                'serie',          v_serie,
                'ultima_data',    v_pavimento,
                'origine',        v_origine,
                'data_richiesta', p_data,
                'famiglia',       p_famiglia_documento,
                'documento_id',   p_fattura_id)
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

    -- ─── IL CONTATORE ─────────────────────────────────────
    SELECT rp.last_numero
      INTO v_last
      FROM vendite.registri_fatturazione_progressivi rp
     WHERE rp.registro_id = p_registro_id
       AND rp.anno  = v_anno
       AND rp.serie = v_serie
       FOR UPDATE;

    IF v_last IS NULL THEN
        -- ⭐ IL SEME DEL SECCHIO NUOVO, e non e' zero.
        --   Un secchio nasce quando cambia la CHIAVE, e la chiave cambia in
        --   due momenti: a capodanno (ANNUALE) e quando qualcuno cambia
        --   reset_policy su un registro che ha gia' numerato. Nel secondo caso
        --   ripartire da 1 consegna un numero che nell'anno solare del
        --   documento e' gia' stato emesso: il vincolo di unicita' del
        --   documento lo respinge, il rollback riporta indietro anche
        --   l'incremento, e al tentativo dopo si sbatte di nuovo. Cioe' un
        --   numeratore PIANTATO, con un errore che parla del numero e non
        --   nomina la causa.
        --
        -- ⛔ Il criterio NON e' «il massimo di sempre»: sotto ANNUALE il primo
        --   documento dell'anno DEVE ripartire da 1, ed e' tutto il senso della
        --   politica. Si guardano solo i secchi che possono COLLIDERE, cioe'
        --   quelli i cui documenti condividono un anno solare con questo:
        --     · secchio continuo (v_anno = 0)  -> li attraversa TUTTI  ⇒ max su tutti;
        --     · secchio d'anno   (v_anno = Y)  -> solo il continuo, se esiste;
        --       gli altri anni no, altrimenti l'azzeramento non avverrebbe mai.
        --
        -- ⚠️ Su un registro che il secchio continuo non ce l'ha, il massimo e'
        --   su zero righe e il COALESCE rende 0: il comportamento di prima,
        --   identico. Il ramo si accende SOLO dove una politica e' cambiata.
        -- ⭐ E gira gia' sotto il lock giusto: la chiave dell'advisory lock non
        --   porta l'anno (vedi sopra), quindi due transazioni con date in anni
        --   diversi sullo stesso (registro, serie) sono comunque serializzate.
        SELECT COALESCE(max(rp.last_numero), 0)
          INTO v_seme
          FROM vendite.registri_fatturazione_progressivi rp
         WHERE rp.registro_id = p_registro_id
           AND rp.serie       = v_serie
           AND (v_anno = 0 OR rp.anno = 0);

        INSERT INTO vendite.registri_fatturazione_progressivi
               (registro_id, anno, serie, last_numero, attivo)
        VALUES (p_registro_id, v_anno, v_serie, v_seme, true)
        RETURNING last_numero INTO v_last;
    END IF;

    v_next := v_last + 1;

    -- ⭐ `GREATEST` e non un'assegnazione secca: la memoria della
    --    sequenza non deve MAI arretrare.
    UPDATE vendite.registri_fatturazione_progressivi
       SET last_numero = v_next,
           ultima_data = GREATEST(COALESCE(ultima_data, p_data), p_data)
     WHERE registro_id = p_registro_id
       AND anno  = v_anno
       AND serie = v_serie;

    RETURN v_next;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_next_progressivo(p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text, p_fattura_id bigint, p_famiglia_documento character varying)
IS 'Prossimo progressivo del sezionale, con il CANCELLO sulla data. ⛔ Rifiuta se p_data sta sotto il PAVIMENTO EFFETTIVO, che e'' il MAGGIORE fra la sequenza gia'' emessa su (registro, serie) e il LIMITE DI EMISSIONE. La data UGUALE al pavimento e'' ammessa (>=, non >). ⭐ Il pavimento arriva COMPOSTO da vendite.fn_get_pavimento_data_documento — una sede sola. ⭐ rev 2026-08-31 (brief-db-registri-di-numerazione-emittente-e-trasloco, C2-6/7): ARRIVA p_famiglia_documento, e il motore smette di parlare solo di fatture. ⭐ IL PERCORSO FELICE NON CAMBIA DI UNA RIGA, ed e'' il fatto che ha reso il trasloco economico: questa funzione non legge vendite.fatture sul percorso felice e non l''ha mai fatto — la competenza arriva come parametro, il pavimento dalla sede unica, il contatore dalla sua tabella. Le fatture comparivano in DUE punti soltanto, entrambi nel ramo d''errore: la lookup del BERSAGLIO e il NOME dei codici. ⚠️ Il parametro nuovo ha un DEFAULT e sta in CODA, quindi l''unico chiamante — vendite.fn_assign_numero_fattura, che chiama POSIZIONALE con cinque argomenti — non cambia. ⛔ Ma un parametro in piu'' crea un OVERLOAD e non una sostituzione: senza DROP resterebbero due funzioni e le chiamate a cinque argomenti diventerebbero ambigue, ed e'' per questo che il changeSet fa DROP prima del CREATE. ⛔ IL NOME p_fattura_id RESTA benche'' ora porti l''id di un documento qualunque: rinominarlo spezzerebbe le chiamate per parametro nominato e costringerebbe a una revisione di fn_assign_numero_fattura che questo cantiere non deve fare — e'' la stessa scelta gia'' presa sul nome della tabella registri_fatturazione, si tiene il nome e si dichiara il debito. ⭐ IL CODICE ERRORE DEL RAMO SEQUENZA LO SCEGLIE LA FAMIGLIA: E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO per la fattura, E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO per gli altri. ⛔ Non si riusa il codice della fattura: la sua frase parla di fatture, e i consumatori di un messaggio si cercano dal NOME di chi lo solleva — un DDT che segnalasse E_FATTURA_* manderebbe a cercare nel posto sbagliato. ⛔ IL GEMELLO DEL LIMITE DI EMISSIONE NON ESISTE, ed e'' una conseguenza del 20260831-05: quel pavimento vale sulla sola famiglia FATTURA, quindi fuori dalla fattura il ramo EMISSIONE e'' IRRAGGIUNGIBILE PER COSTRUZIONE — e un codice che nessuno puo'' sollevare sarebbe una voce dichiarata e non implementata. ⭐ IL SECONDO BERSAGLIO — «apri l''ultima numerata del sezionale» — esiste SOLO per la fattura: per gli altri documenti quella lookup e'' su un''altra tabella e non c''e'' nessuna pagina a cui mandare, e un pulsante verso il nulla e'' peggio di nessun pulsante (stessa regola gia'' scritta per il ramo EMISSIONE). ⚠️ L''ultima numerata si cerca PER DATA e non per numero, e solo se VISIBILE: vendite.fatture ha la RLS e questa funzione e'' SECURITY INVOKER. ⭐ Il controllo sta SOTTO l''advisory lock: e'' l''unico punto NON AGGIRABILE. 🔴 La chiave del lock non porta l''ANNO ed e'' (registro | serie), perche'' il cancello legge il massimo ATTRAVERSO GLI ANNI. ⚠️ Il massimo si legge dal CONTATORE e non da vendite.fatture, che ha la RLS: un max() sotto perimetro ristretto tornerebbe NULL, cioe'' «via libera» proprio quando non si sa. ⭐ ultima_data si aggiorna con GREATEST: la memoria della sequenza non arretra mai. ℹ️ Sui documenti non fiscali la competenza non serve (il limite non si applica) ma il ripiego resta, per tenere una sola forma di chiamata. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-10, rivisto da brief-db-registri-di-numerazione-emittente-e-trasloco C2-6/7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
