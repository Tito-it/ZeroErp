{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo.md" %}
# ⚙️ Funzione `fn_crea_indirizzi_ruolo`

```sql
CREATE FUNCTION fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
    v_natura_id     anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_tipo_id       anagrafiche.indirizzi.tipo_indirizzo_id%TYPE;
    v_oggi          config.tipi_ruolo_tipi_indirizzo.valido_dal%TYPE;
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
    --   - AUTO-CLONE: i tipi obbligatori del ruolo assenti dal
    --     payload si copiano dal primo indirizzo
    --     (fn_indirizzi_con_obbligatori); sono obbligatori i tipi
    --     che il ruolo chiede e che il ruolo e la natura del
    --     soggetto ammettono oggi
    --     (fn_tipo_indirizzo_obbligatorio_per_ruolo): un tipo
    --     che la natura vieta non si copia;
    --   - un tipo che il ruolo ha gia' senza istanza si salta (la
    --     chiave di uq_indirizzi_ruolo_tipo_no_istanza); le righe
    --     le scrive la singolare fn_crea_indirizzo_ruolo;
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

    SELECT sr.tipo_ruolo_id, s.tipo_soggetto_dettaglio_id
      INTO v_tipo_ruolo_id, v_natura_id
      FROM anagrafiche.soggetti_ruoli sr
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
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

    -- 2. AUTO-CLONE: i tipi del requisito del ruolo, sulla natura
    --    del soggetto, oggi, copiati dal primo indirizzo; non quelli
    --    che il ruolo (senza istanza) o l'elenco hanno gia', col tipo
    --    o col ripiego (D-T7a-4).
    v_oggi := script.fn_data_operativa();
    v_norm := anagrafiche.fn_indirizzi_con_obbligatori(
        v_norm,
        ARRAY(SELECT o.tipo_indirizzo_id
                FROM anagrafiche.fn_indirizzi_obbligatori_ruolo(
                         v_tipo_ruolo_id, v_natura_id, v_oggi) o
               WHERE NOT EXISTS (
                         SELECT 1
                           FROM anagrafiche.indirizzi i
                          WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
                            AND i.istanza_utility_id IS NULL
                            AND i.tipo_indirizzo_id
                                IN (o.tipo_indirizzo_id, o.ripiego_tipo_indirizzo_id))
                 AND NOT EXISTS (
                         SELECT 1
                           FROM jsonb_array_elements(v_norm) AS x
                          WHERE (x ->> 'tipo_indirizzo_id')::integer
                                IN (o.tipo_indirizzo_id, o.ripiego_tipo_indirizzo_id))));

    -- 3. La scrittura: un tipo che il ruolo ha gia' (senza
    --    istanza) si salta. La via si risolve solo qui, per gli
    --    indirizzi che si scrivono.
    FOR v_el IN SELECT e FROM jsonb_array_elements(v_norm) AS e LOOP
        v_tipo_id := (v_el ->> 'tipo_indirizzo_id')::integer;

        CONTINUE WHEN EXISTS (
            SELECT 1
              FROM anagrafiche.indirizzi i
             WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
               AND i.tipo_indirizzo_id = v_tipo_id
               AND i.istanza_utility_id IS NULL);

        PERFORM anagrafiche.fn_crea_indirizzo_ruolo(p_soggetto_ruolo_id, v_el);

        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_indirizzi_ruolo(p_soggetto_ruolo_id bigint, p_indirizzi jsonb)
IS 'Madre plurale: scrive gli indirizzi di un ruolo in una sola istruzione e ritorna quanti ne ha scritti. p_indirizzi: array di oggetti, ciascuno col tipo (tipo_indirizzo_id o tipo_indirizzo_codice_interno, codice interno) e l''indirizzo in una di tre forme: libero (indirizzo_libero con stato, poi comune e CAP del catalogo oppure locality e postal_code), dettaglio gia'' risolto (indirizzo_dettaglio_id), via da risolvere (stradario_id oppure toponomastica_id + descrizione_via + comune_id + codice_postale_id, piu'' il civico). AUTO-CLONE: i tipi del requisito del ruolo (anagrafiche.fn_indirizzi_obbligatori_ruolo, sul tipo di ruolo e sulla natura del soggetto, il giorno di script.fn_data_operativa(): lo stesso giudizio dei guard) si copiano dal primo indirizzo (anagrafiche.fn_indirizzi_con_obbligatori), salvo quelli di cui il ruolo senza istanza o il payload hanno gia'' il tipo o il ripiego. Un tipo che la natura non ammette non si copia. Un tipo che il ruolo ha gia'' senza istanza si salta (la chiave di uq_indirizzi_ruolo_tipo_no_istanza); payload vuoto: nessuna scrittura. Ogni riga la scrive la singolare anagrafiche.fn_crea_indirizzo_ruolo. Rifiuti: elenco malformato E_SCRIPT_CHIAMATA_NON_VALIDA, ruolo inesistente E_SOGGETTO_RUOLO_NON_TROVATO; l''elemento lo legge anagrafiche.fn_indirizzo_elemento (oggetto, chiavi ammesse, tipo: E_SCRIPT_CHIAMATA_NON_VALIDA, E_CAMPO_NON_AMMESSO, E_TIPO_INDIRIZZO_NON_TROVATO) e la via la risolve anagrafiche.fn_indirizzo_elemento_dettaglio. La via nuova la valida anagrafiche.fn_create_indirizzo (E_INDIRIZZO_VIA_NUOVA_INCOMPLETA, col campo); il permesso non lo valida. SECURITY INVOKER. Gemella di anagrafiche.fn_crea_indirizzi_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
