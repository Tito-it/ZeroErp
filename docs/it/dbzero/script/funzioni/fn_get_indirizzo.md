{% include-markdown "it/dbzero/script/manual/fn_get_indirizzo.md" %}
# ⚙️ Funzione `fn_get_indirizzo`

```sql
CREATE FUNCTION fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying, p_istanza_utility_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying, p_istanza_utility_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(tipo_indirizzo character varying, indirizzo_completo text, geoloc geometry, indirizzo_id bigint, soggetto_ruolo_id bigint, istanza_utility_id bigint, tipo_indirizzo_id integer, indirizzo_dettaglio_id bigint, indirizzo_libero text, is_normalizzato boolean, stato_id integer, stato_descrizione character varying, stato_iso2 character, regione_id integer, regione_descrizione character varying, provincia_id integer, provincia_sigla character varying, provincia_descrizione character varying, comune_id integer, comune_descrizione character varying, codice_postale_id integer, cap_codice character varying, locality character varying, administrative_area character varying, sublocality character varying, postal_code character varying)
 LANGUAGE plpgsql
 STABLE ROWS 10
AS $function$
DECLARE
    v_tipo_ruolo_id      anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_soggetto_id        anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_current_codice     config.tipi_indirizzi.codice_interno%TYPE;
    v_current_tipo_id    config.tipi_indirizzi.id%TYPE;
    v_fallback_tipo_id   config.tipi_ruolo_tipi_indirizzo.fallback_tipo_indirizzo_id%TYPE;
    v_rows_found         integer;
    v_visited_tipo_ids   config.tipi_indirizzi.id%TYPE[] := '{}'::integer[];
BEGIN
    /*
      Policy indirizzi a 3 livelli con fallback per tipo:
        FASE 1: ruolo + istanza specifica (se p_istanza_utility_id valorizzato)
        FASE 2: ruolo generico (istanza IS NULL)
        FASE 3: fallback soggetto (via fn_get_indirizzo_by_soggetto)
      Ogni fase segue la catena fallback in tipi_ruolo_tipi_indirizzo
      con protezione anti-loop circolare.
    */

    -- Recupera soggetto e tipo ruolo
    SELECT sr.tipo_ruolo_id, sr.soggetto_id
      INTO v_tipo_ruolo_id, v_soggetto_id
    FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.id = p_soggetto_ruolo_id;

    IF v_tipo_ruolo_id IS NULL THEN RETURN; END IF;

    -- FASE 1: RUOLO + ISTANZA SPECIFICA
    IF p_istanza_utility_id IS NOT NULL THEN
        v_current_codice := p_tipo_codice;
        v_visited_tipo_ids := '{}'::integer[];
        LOOP
            -- Il tipo si confronta per ID (rev 20260923-49): la vista espone in
            -- tipo_indirizzo il CODICE (display, mutabile), il parametro e' il
            -- CODICE_INTERNO. Confrontati come testo non si incontravano mai.
            SELECT ti.id INTO v_current_tipo_id
            FROM config.tipi_indirizzi ti WHERE ti.codice_interno = v_current_codice;
            IF v_current_tipo_id IS NULL THEN EXIT; END IF;

            RETURN QUERY
            SELECT f.tipo_indirizzo, f.indirizzo_completo, f.geoloc,
                f.indirizzo_id, f.soggetto_ruolo_id, f.istanza_utility_id,
                f.tipo_indirizzo_id, f.indirizzo_dettaglio_id, f.indirizzo_libero,
                f.is_normalizzato,
                f.stato_id, f.stato_descrizione, f.stato_iso2,
                f.regione_id, f.regione_descrizione,
                f.provincia_id, f.provincia_sigla, f.provincia_descrizione,
                f.comune_id, f.comune_descrizione,
                f.codice_postale_id, f.cap_codice,
                f.locality, f.administrative_area, f.sublocality, f.postal_code
            FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id, p_istanza_utility_id) f
            WHERE f.tipo_indirizzo_id = v_current_tipo_id
              AND f.istanza_utility_id = p_istanza_utility_id;

            GET DIAGNOSTICS v_rows_found = ROW_COUNT;
            IF v_rows_found > 0 THEN RETURN; END IF;

            -- Cerca fallback per tipo indirizzo
            IF v_current_tipo_id = ANY (v_visited_tipo_ids) THEN EXIT; END IF;
            v_visited_tipo_ids := array_append(v_visited_tipo_ids, v_current_tipo_id);

            SELECT m.fallback_tipo_indirizzo_id INTO v_fallback_tipo_id
            FROM config.tipi_ruolo_tipi_indirizzo m
            WHERE m.tipo_ruolo_id = v_tipo_ruolo_id
              AND m.tipo_indirizzo_id = v_current_tipo_id
              AND m.attivo = TRUE
              AND (m.valido_dal IS NULL OR m.valido_dal <= (SELECT script.fn_data_operativa()))
              AND (m.valido_al IS NULL OR m.valido_al >= (SELECT script.fn_data_operativa()))
            LIMIT 1;
            IF v_fallback_tipo_id IS NULL THEN EXIT; END IF;

            SELECT ti.codice_interno INTO v_current_codice
            FROM config.tipi_indirizzi ti WHERE ti.id = v_fallback_tipo_id;
            IF v_current_codice IS NULL THEN EXIT; END IF;
        END LOOP;
    END IF;

    -- FASE 2: RUOLO GENERICO (istanza_utility_id IS NULL)
    v_current_codice := p_tipo_codice;
    v_visited_tipo_ids := '{}'::integer[];
    LOOP
        -- Il tipo si confronta per ID (rev 20260923-49), come in FASE 1.
        SELECT ti.id INTO v_current_tipo_id
        FROM config.tipi_indirizzi ti WHERE ti.codice_interno = v_current_codice;
        IF v_current_tipo_id IS NULL THEN EXIT; END IF;

        RETURN QUERY
        SELECT f.tipo_indirizzo, f.indirizzo_completo, f.geoloc,
            f.indirizzo_id, f.soggetto_ruolo_id, f.istanza_utility_id,
            f.tipo_indirizzo_id, f.indirizzo_dettaglio_id, f.indirizzo_libero,
            f.is_normalizzato,
            f.stato_id, f.stato_descrizione, f.stato_iso2,
            f.regione_id, f.regione_descrizione,
            f.provincia_id, f.provincia_sigla, f.provincia_descrizione,
            f.comune_id, f.comune_descrizione,
            f.codice_postale_id, f.cap_codice,
            f.locality, f.administrative_area, f.sublocality, f.postal_code
        FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id) f
        WHERE f.tipo_indirizzo_id = v_current_tipo_id
          AND f.istanza_utility_id IS NULL;

        GET DIAGNOSTICS v_rows_found = ROW_COUNT;
        IF v_rows_found > 0 THEN RETURN; END IF;

        -- Cerca fallback per tipo indirizzo
        IF v_current_tipo_id = ANY (v_visited_tipo_ids) THEN EXIT; END IF;
        v_visited_tipo_ids := array_append(v_visited_tipo_ids, v_current_tipo_id);

        SELECT m.fallback_tipo_indirizzo_id INTO v_fallback_tipo_id
        FROM config.tipi_ruolo_tipi_indirizzo m
        WHERE m.tipo_ruolo_id = v_tipo_ruolo_id
          AND m.tipo_indirizzo_id = v_current_tipo_id
          AND m.attivo = TRUE
          AND (m.valido_dal IS NULL OR m.valido_dal <= (SELECT script.fn_data_operativa()))
          AND (m.valido_al IS NULL OR m.valido_al >= (SELECT script.fn_data_operativa()))
        LIMIT 1;
        IF v_fallback_tipo_id IS NULL THEN EXIT; END IF;

        SELECT ti.codice_interno INTO v_current_codice
        FROM config.tipi_indirizzi ti WHERE ti.id = v_fallback_tipo_id;
        IF v_current_codice IS NULL THEN EXIT; END IF;
    END LOOP;

    -- FASE 3: FALLBACK SOGGETTO
    RETURN QUERY
    SELECT
        r.tipo_indirizzo_codice,
        r.indirizzo_display,
        r.geoloc,
        r.indirizzo_id,
        p_soggetto_ruolo_id,
        r.istanza_utility_id,
        r.tipo_indirizzo_id,
        r.indirizzo_dettaglio_id,
        r.indirizzo_libero,
        r.is_normalizzato,
        r.stato_id,
        r.stato_descrizione,
        r.stato_iso2,
        r.regione_id,
        r.regione_descrizione,
        r.provincia_id,
        r.provincia_sigla,
        r.provincia_descrizione,
        r.comune_id,
        r.comune_descrizione,
        r.codice_postale_id,
        r.cap_codice,
        r.locality,
        r.administrative_area,
        r.sublocality,
        r.postal_code
    FROM script.fn_get_indirizzo_by_soggetto(v_soggetto_id, p_tipo_codice) r;

    RETURN;
END;
$function$

COMMENT ON FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying, p_istanza_utility_id bigint)
IS 'Policy indirizzi 3 livelli: (1) ruolo+istanza con fallback tipo, (2) ruolo generico con fallback tipo, (3) soggetto con fallback tipo.';
```

---
{% include-markdown "signature-core.md" %}
