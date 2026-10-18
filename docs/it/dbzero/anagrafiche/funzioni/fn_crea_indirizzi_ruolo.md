{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo.md" %}
# ⚙️ Funzione `fn_crea_indirizzi_ruolo`

```sql
CREATE FUNCTION fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_lista         jsonb := COALESCE(p_indirizzi, '[]'::jsonb);
    v_norm          jsonb := '[]'::jsonb;  -- elementi col tipo risolto
    v_el            jsonb;
    v_estranea      text;
    v_tipo_ruolo_id anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_tipo_id       anagrafiche.indirizzi.tipo_indirizzo_id%TYPE;
    v_libero        anagrafiche.indirizzi.indirizzo_libero%TYPE;
    v_det_id        anagrafiche.indirizzi.indirizzo_dettaglio_id%TYPE;
    v_n             integer := 0;   -- un conteggio: niente da ancorare
    -- Le chiavi di un indirizzo: le colonne della riga, piu' quelle
    -- di una via da risolvere (fn_create_indirizzo).
    c_ammesse CONSTANT text[] := ARRAY[
        'tipo_indirizzo_id', 'tipo_indirizzo_codice',
        'indirizzo_dettaglio_id', 'indirizzo_libero',
        'stato_id', 'comune_id', 'codice_postale_id',
        'administrative_area', 'locality', 'sublocality', 'postal_box',
        'stradario_id', 'toponomastica_id', 'descrizione_via',
        'civico', 'estensione_civico', 'palazzina', 'scala', 'piano', 'interno'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere gli indirizzi di un ruolo. p_indirizzi e' un
    --   array di oggetti; per ognuno il tipo (id o codice
    --   interno) e l'indirizzo, in una di tre forme:
    --     * libero:  indirizzo_libero (+ stato, comune, CAP...);
    --     * dettaglio gia' risolto: indirizzo_dettaglio_id;
    --     * via: stradario_id, oppure via nuova (toponomastica,
    --       descrizione_via, comune, CAP), piu' il civico:
    --       la risolve anagrafiche.fn_create_indirizzo.
    --   Ritorna quanti indirizzi ha scritto.
    --
    -- Regole:
    --   - AUTO-CLONE: i tipi obbligatori della matrice del ruolo
    --     (config.tipi_ruolo_tipi_indirizzo) assenti dal payload
    --     si copiano dal primo indirizzo;
    --   - un tipo che il ruolo ha gia' si salta;
    --   - payload vuoto: niente, nemmeno i cloni.
    -- =========================================================
    IF jsonb_typeof(v_lista) <> 'array' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_indirizzi_ruolo', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_indirizzi', jsonb_typeof(v_lista)),
            NULL::uuid,
            'anagrafiche.fn_crea_indirizzi_ruolo',
            'gli indirizzi non sono un elenco');
    END IF;

    SELECT sr.tipo_ruolo_id
      INTO v_tipo_ruolo_id
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_indirizzi_ruolo', 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            COALESCE(p_soggetto_ruolo_id::text, '-'));
    END IF;

    IF jsonb_array_length(v_lista) = 0 THEN
        RETURN 0;
    END IF;

    -- 1. Ogni elemento: un oggetto, chiavi ammesse, tipo risolto.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        IF jsonb_typeof(v_el) <> 'object' THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'anagrafiche.fn_crea_indirizzi_ruolo', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
                jsonb_build_object('tipo_elemento', jsonb_typeof(v_el)),
                NULL::uuid,
                'anagrafiche.fn_crea_indirizzi_ruolo',
                'un indirizzo non e'' un oggetto');
        END IF;

        v_estranea := script.fn_prima_chiave_estranea(v_el, c_ammesse);
        IF v_estranea IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'anagrafiche.fn_crea_indirizzi_ruolo', 'E_CAMPO_NON_AMMESSO',
                jsonb_build_object('campo', v_estranea,
                                   'soggetto_ruolo_id', p_soggetto_ruolo_id),
                NULL::uuid,
                v_estranea);
        END IF;

        v_tipo_id := (v_el ->> 'tipo_indirizzo_id')::integer;
        IF v_tipo_id IS NULL AND NULLIF(btrim(v_el ->> 'tipo_indirizzo_codice'), '') IS NOT NULL THEN
            SELECT ti.id
              INTO v_tipo_id
              FROM config.tipi_indirizzi ti
             WHERE ti.codice_interno = upper(btrim(v_el ->> 'tipo_indirizzo_codice'));
        END IF;

        IF v_tipo_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'anagrafiche.fn_crea_indirizzi_ruolo', 'E_TIPO_INDIRIZZO_NON_TROVATO',
                jsonb_build_object('campo', 'tipo_indirizzo_codice',
                                   'tipo_indirizzo_codice', v_el ->> 'tipo_indirizzo_codice',
                                   'soggetto_ruolo_id', p_soggetto_ruolo_id),
                NULL::uuid,
                COALESCE(NULLIF(btrim(v_el ->> 'tipo_indirizzo_codice'), ''), '-'));
        END IF;

        v_norm := v_norm || jsonb_build_array(
                    (v_el - 'tipo_indirizzo_codice')
                    || jsonb_build_object('tipo_indirizzo_id', v_tipo_id));
    END LOOP;

    -- 2. AUTO-CLONE: i tipi obbligatori del ruolo che il payload
    --    non porta, copiati dal primo indirizzo.
    v_norm := v_norm || COALESCE(
        (SELECT jsonb_agg((v_norm -> 0) || jsonb_build_object('tipo_indirizzo_id', m.tipo_indirizzo_id)
                          ORDER BY m.tipo_indirizzo_id)
           FROM config.tipi_ruolo_tipi_indirizzo m
          WHERE m.tipo_ruolo_id = v_tipo_ruolo_id
            AND m.attivo
            AND m.obbligatorio
            AND NOT EXISTS (
                  SELECT 1
                    FROM jsonb_array_elements(v_norm) AS x
                   WHERE (x ->> 'tipo_indirizzo_id')::integer = m.tipo_indirizzo_id)),
        '[]'::jsonb);

    -- 3. La scrittura: un tipo che il ruolo ha gia' si salta.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_norm) AS e LOOP
        v_tipo_id := (v_el ->> 'tipo_indirizzo_id')::integer;

        CONTINUE WHEN EXISTS (
            SELECT 1
              FROM anagrafiche.indirizzi i
             WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
               AND i.tipo_indirizzo_id = v_tipo_id);

        v_libero := NULLIF(btrim(v_el ->> 'indirizzo_libero'), '');
        v_det_id := (v_el ->> 'indirizzo_dettaglio_id')::bigint;

        IF v_libero IS NULL AND v_det_id IS NULL THEN
            v_det_id := anagrafiche.fn_create_indirizzo(
                p_stradario_id      := (v_el ->> 'stradario_id')::integer,
                p_toponomastica_id  := (v_el ->> 'toponomastica_id')::integer,
                p_descrizione_via   := v_el ->> 'descrizione_via',
                p_comune_id         := (v_el ->> 'comune_id')::integer,
                p_codice_postale_id := (v_el ->> 'codice_postale_id')::integer,
                p_civico            := (v_el ->> 'civico')::integer,
                p_estensione_civico := NULLIF(btrim(v_el ->> 'estensione_civico'), ''),
                p_palazzina         := NULLIF(btrim(v_el ->> 'palazzina'), ''),
                p_scala             := NULLIF(btrim(v_el ->> 'scala'), ''),
                p_piano             := NULLIF(btrim(v_el ->> 'piano'), ''),
                p_interno           := NULLIF(btrim(v_el ->> 'interno'), ''));
        END IF;

        INSERT INTO anagrafiche.indirizzi (
            soggetto_ruolo_id, tipo_indirizzo_id,
            indirizzo_dettaglio_id, indirizzo_libero,
            stato_id, comune_id, codice_postale_id,
            administrative_area, locality, sublocality, postal_box)
        VALUES (
            p_soggetto_ruolo_id, v_tipo_id,
            v_det_id, v_libero,
            (v_el ->> 'stato_id')::integer,
            (v_el ->> 'comune_id')::integer,
            (v_el ->> 'codice_postale_id')::integer,
            v_el ->> 'administrative_area',
            v_el ->> 'locality',
            v_el ->> 'sublocality',
            v_el ->> 'postal_box');

        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
IS 'Madre (2026-10-17): scrive gli indirizzi di un ruolo in una sola istruzione. p_indirizzi: array di oggetti, ciascuno col tipo (tipo_indirizzo_id o tipo_indirizzo_codice, codice interno) e l''indirizzo in una di tre forme: libero (indirizzo_libero con stato, comune, CAP, locality...), dettaglio gia'' risolto (indirizzo_dettaglio_id), via da risolvere (stradario_id oppure toponomastica_id + descrizione_via + comune_id + codice_postale_id, piu'' il civico: anagrafiche.fn_create_indirizzo, idempotente). AUTO-CLONE: i tipi obbligatori della matrice del ruolo (config.tipi_ruolo_tipi_indirizzo, attivi) assenti dal payload si copiano dal primo indirizzo; un tipo che il ruolo ha gia'' si salta; payload vuoto: nessuna scrittura. Il tipo del ruolo si legge dal ruolo. Ritorna quanti indirizzi ha scritto. Rifiuti: elenco o elemento malformato E_SCRIPT_CHIAMATA_NON_VALIDA, chiave estranea E_CAMPO_NON_AMMESSO, tipo inesistente E_TIPO_INDIRIZZO_NON_TROVATO, ruolo inesistente E_SOGGETTO_RUOLO_NON_TROVATO; il tipo ammesso per il ruolo e la completezza li dicono i guard della tabella. Non valida i campi di una via nuova (pre-check del backend, come fn_create_indirizzo) ne'' il permesso (dominio anagrafiche, B-5). INVOKER. Gemello di fn_crea_indirizzo_soggetto sul livello del ruolo. Prende il posto di SoggettiService.create_indirizzi_ruolo (2b-2) e dell''INSERT di dbops.fn_pgtap_crea_soggetto_ruolo. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 2).';
```

---
{% include-markdown "signature-core.md" %}
