{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo.md" %}
# ⚙️ Funzione `fn_crea_indirizzi_ruolo`

```sql
CREATE FUNCTION fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    c_chi           CONSTANT text := 'anagrafiche.fn_crea_indirizzi_ruolo';
    v_lista         jsonb := COALESCE(p_indirizzi, '[]'::jsonb);
    v_norm          jsonb := '[]'::jsonb;  -- elementi col tipo risolto
    v_el            jsonb;
    v_tipo_ruolo_id anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_tipo_id       anagrafiche.indirizzi.tipo_indirizzo_id%TYPE;
    v_n             integer := 0;   -- un conteggio: niente da ancorare
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere gli indirizzi di un ruolo. p_indirizzi e' un
    --   array di oggetti; per ognuno il tipo (id o codice
    --   interno) e l'indirizzo, in una di tre forme:
    --     * libero:  indirizzo_libero (+ stato, comune e CAP del
    --       catalogo, oppure localita' e codice postale);
    --     * dettaglio gia' risolto: indirizzo_dettaglio_id;
    --     * via: stradario_id, oppure via nuova (toponomastica,
    --       descrizione_via, comune, CAP), piu' il civico.
    --   La grammatica dell'elemento e la via sono dei BB
    --   fn_indirizzo_elemento e fn_indirizzo_elemento_dettaglio,
    --   comuni con fn_crea_indirizzo_soggetto.
    --   Ritorna quanti indirizzi ha scritto.
    --
    -- Regole:
    --   - AUTO-CLONE: i tipi obbligatori della matrice del ruolo
    --     (config.tipi_ruolo_tipi_indirizzo) assenti dal payload
    --     si copiano dal primo indirizzo;
    --   - un tipo che il ruolo ha gia' si salta;
    --   - payload vuoto: niente, nemmeno i cloni;
    --   - la completezza e la forma le dice il guard della
    --     tabella (trgfn_indirizzi_guard_forma_libera).
    -- =========================================================
    IF jsonb_typeof(v_lista) <> 'array' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_indirizzi', jsonb_typeof(v_lista)),
            NULL::uuid,
            c_chi,
            'gli indirizzi non sono un elenco');
    END IF;

    SELECT sr.tipo_ruolo_id
      INTO v_tipo_ruolo_id
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            COALESCE(p_soggetto_ruolo_id::text, '-'));
    END IF;

    IF jsonb_array_length(v_lista) = 0 THEN
        RETURN 0;
    END IF;

    -- 1. Ogni elemento: un oggetto, chiavi ammesse, tipo risolto.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        v_norm := v_norm || jsonb_build_array(
                    anagrafiche.fn_indirizzo_elemento(
                        v_el, c_chi,
                        jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id)));
    END LOOP;

    -- 2. AUTO-CLONE: i tipi obbligatori del ruolo che il payload
    --    non porta, copiati dal primo indirizzo.
    -- ⭐ rev 20261019-38 (D-16a): la copia del primo indirizzo per i tipi
    --   obbligatori che mancano e' il BB anagrafiche.fn_indirizzi_con_obbligatori,
    --   comune alla plurale del soggetto. Qui resta la matrice del ruolo.
    v_norm := anagrafiche.fn_indirizzi_con_obbligatori(
        v_norm,
        ARRAY(SELECT m.tipo_indirizzo_id
                FROM config.tipi_ruolo_tipi_indirizzo m
               WHERE m.tipo_ruolo_id = v_tipo_ruolo_id
                 AND m.attivo
                 AND m.obbligatorio));

    -- 3. La scrittura: un tipo che il ruolo ha gia' si salta. La
    --    via si risolve solo qui, per gli indirizzi che si scrivono.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_norm) AS e LOOP
        v_tipo_id := (v_el ->> 'tipo_indirizzo_id')::integer;

        CONTINUE WHEN EXISTS (
            SELECT 1
              FROM anagrafiche.indirizzi i
             WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
               AND i.tipo_indirizzo_id = v_tipo_id
               -- ⭐ rev 20261019-38: la chiave e' uq_indirizzi_ruolo_tipo_no_istanza.
               --   Prima un indirizzo di un'ISTANZA dello stesso tipo faceva
               --   saltare quello del ruolo.
               AND i.istanza_utility_id IS NULL);

        -- ⭐ rev 20261019-38 (D-16a): la riga la scrive la singolare
        --   anagrafiche.fn_crea_indirizzo_ruolo, sede unica dell'INSERT.
        PERFORM anagrafiche.fn_crea_indirizzo_ruolo(p_soggetto_ruolo_id, v_el);

        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
IS 'Madre (2026-10-17): scrive gli indirizzi di un ruolo in una sola istruzione. p_indirizzi: array di oggetti, ciascuno col tipo (tipo_indirizzo_id o tipo_indirizzo_codice, codice interno) e l''indirizzo in una di tre forme: libero (indirizzo_libero con stato, poi comune e CAP del catalogo oppure locality e postal_code), dettaglio gia'' risolto (indirizzo_dettaglio_id), via da risolvere (stradario_id oppure toponomastica_id + descrizione_via + comune_id + codice_postale_id, piu'' il civico). AUTO-CLONE: i tipi obbligatori della matrice del ruolo (config.tipi_ruolo_tipi_indirizzo, attivi) assenti dal payload si copiano dal primo indirizzo; un tipo che il ruolo ha gia'' si salta; payload vuoto: nessuna scrittura. Il tipo del ruolo si legge dal ruolo. Ritorna quanti indirizzi ha scritto. Rifiuti: elenco malformato E_SCRIPT_CHIAMATA_NON_VALIDA, ruolo inesistente E_SOGGETTO_RUOLO_NON_TROVATO; l''elemento lo legge anagrafiche.fn_indirizzo_elemento (oggetto, chiavi ammesse, tipo: E_SCRIPT_CHIAMATA_NON_VALIDA, E_CAMPO_NON_AMMESSO, E_TIPO_INDIRIZZO_NON_TROVATO) e la via la risolve anagrafiche.fn_indirizzo_elemento_dettaglio (fn_create_indirizzo, idempotente): la stessa grammatica di fn_crea_indirizzo_soggetto (rev 2026-10-18, D-4 di Tid). Il tipo ammesso per il ruolo e la forma dell''indirizzo libero li dicono i guard della tabella (anagrafiche.trgfn_indirizzi_guard_forma_libera). Non valida i campi di una via nuova (pre-check del backend) ne'' il permesso (dominio anagrafiche, B-5). INVOKER. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 2; §6.11). ⭐ Rev 2026-10-19 (20261019-38, R-BE-6 e R-BE-12, D-16a di Tid): ogni riga la scrive la singolare anagrafiche.fn_crea_indirizzo_ruolo (sede unica dell''INSERT); il salto dei tipi presenti guarda solo gli indirizzi del ruolo SENZA istanza (la chiave di uq_indirizzi_ruolo_tipo_no_istanza: prima un indirizzo di un''istanza dello stesso tipo faceva saltare quello del ruolo).';
```

</div>

---
{% include-markdown "signature-core.md" %}
