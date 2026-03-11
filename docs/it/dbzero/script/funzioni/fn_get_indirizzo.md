{% include-markdown "it/dbzero/script/manual/fn_get_indirizzo.md" %}
# ⚙️ Funzione `fn_get_indirizzo`

```sql
CREATE FUNCTION fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying)
 RETURNS TABLE(tipo_indirizzo character varying, indirizzo_completo text, geoloc geometry, indirizzo_id bigint, soggetto_ruolo_id bigint, tipo_indirizzo_id integer, indirizzo_dettaglio_id bigint, indirizzo_libero text, is_normalizzato boolean, stato_id integer, stato_descrizione character varying, stato_iso2 character, regione_id integer, regione_descrizione character varying, provincia_id integer, provincia_sigla character, provincia_descrizione character, comune_id integer, comune_descrizione character varying, codice_postale_id integer, cap_codice character, locality character varying, administrative_area character varying, sublocality character varying, postal_box character varying)
 LANGUAGE plpgsql
 STABLE ROWS 10
AS $function$
DECLARE
    v_tipo_ruolo_id      anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_soggetto_id        anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_current_codice     config.tipi_indirizzi.codice_interno%TYPE := p_tipo_codice;
    v_current_tipo_id    config.tipi_indirizzi.id%TYPE;
    v_fallback_tipo_id   config.tipi_ruolo_tipi_indirizzo.fallback_tipo_indirizzo_id%TYPE;
    v_rows_found         integer;
    v_visited_tipo_ids   config.tipi_indirizzi.id%TYPE[] := '{}'::integer[];
BEGIN
    -- Recupera soggetto e tipo ruolo dal soggetto_ruolo richiesto
    SELECT sr.tipo_ruolo_id, sr.soggetto_id
      INTO v_tipo_ruolo_id, v_soggetto_id
    FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.id = p_soggetto_ruolo_id;

    IF v_tipo_ruolo_id IS NULL THEN
        RETURN;
    END IF;

    -- 1) MASTER: cerca indirizzi RUOLO per il tipo richiesto,
    --    con fallback su matrice config.tipi_ruolo_tipi_indirizzo
    LOOP
        RETURN QUERY
        SELECT
            f.tipo_indirizzo,
            f.indirizzo_completo,
            f.geoloc,
            f.indirizzo_id,
            f.soggetto_ruolo_id,
            f.tipo_indirizzo_id,
            f.indirizzo_dettaglio_id,
            f.indirizzo_libero,
            f.is_normalizzato,
            f.stato_id,
            f.stato_descrizione,
            f.stato_iso2,
            f.regione_id,
            f.regione_descrizione,
            f.provincia_id,
            f.provincia_sigla,
            f.provincia_descrizione,
            f.comune_id,
            f.comune_descrizione,
            f.codice_postale_id,
            f.cap_codice,
            f.locality,
            f.administrative_area,
            f.sublocality,
            f.postal_box
        FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id) f
        WHERE f.tipo_indirizzo = v_current_codice;

        -- Se trovato, ritorna direttamente
        GET DIAGNOSTICS v_rows_found = ROW_COUNT;
        IF v_rows_found > 0 THEN
            RETURN;
        END IF;

        -- Risolvi ID tipo indirizzo corrente
        SELECT ti.id
          INTO v_current_tipo_id
        FROM config.tipi_indirizzi ti
        WHERE ti.codice_interno = v_current_codice;

        IF v_current_tipo_id IS NULL THEN
            EXIT;
        END IF;

        -- Protezione anti-loop circolare
        IF v_current_tipo_id = ANY (v_visited_tipo_ids) THEN
            EXIT;
        END IF;

        v_visited_tipo_ids := array_append(v_visited_tipo_ids, v_current_tipo_id);

        -- Cerca fallback nella matrice ruolo/tipo_indirizzo
        SELECT m.fallback_tipo_indirizzo_id
          INTO v_fallback_tipo_id
        FROM config.tipi_ruolo_tipi_indirizzo m
        WHERE m.tipo_ruolo_id = v_tipo_ruolo_id
          AND m.tipo_indirizzo_id = v_current_tipo_id
          AND m.attivo = TRUE
          AND (m.valido_dal IS NULL OR m.valido_dal <= current_date)
          AND (m.valido_al IS NULL OR m.valido_al >= current_date)
        LIMIT 1;

        IF v_fallback_tipo_id IS NULL THEN
            EXIT;
        END IF;

        -- Passa al codice del tipo fallback per il prossimo ciclo
        SELECT ti.codice_interno
          INTO v_current_codice
        FROM config.tipi_indirizzi ti
        WHERE ti.id = v_fallback_tipo_id;

        IF v_current_codice IS NULL THEN
            EXIT;
        END IF;
    END LOOP;

    -- 2) FALLBACK: se RUOLO non ha risultati, cerca su layer SOGGETTO
    --    tramite fn_get_indirizzo_by_soggetto (con propria catena fallback)
    RETURN QUERY
    SELECT
        r.tipo_indirizzo_codice         AS tipo_indirizzo,
        r.indirizzo_display             AS indirizzo_completo,
        r.geoloc,
        r.indirizzo_id,
        p_soggetto_ruolo_id             AS soggetto_ruolo_id,
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
        r.postal_box
    FROM script.fn_get_indirizzo_by_soggetto(v_soggetto_id, p_tipo_codice) r;

    RETURN;
END;
$function$

COMMENT ON FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying)
IS 'Policy indirizzi: usa indirizzi RUOLO come master (con fallback tipo su matrice ruolo) e, se assenti, fallback su indirizzi SOGGETTO.';
```

---
{% include-markdown "signature-core.md" %}
