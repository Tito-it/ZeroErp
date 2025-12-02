{% include-markdown "it/dbzero/script/manual/fn_get_indirizzo.md" %}
# ⚙️ Funzione `fn_get_indirizzo`

```sql
CREATE FUNCTION fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id bigint, p_tipo_codice character varying)
 RETURNS TABLE(tipo_indirizzo character varying, indirizzo_completo text, geoloc geometry, indirizzo_id bigint, soggetto_ruolo_id bigint, tipo_indirizzo_id integer, indirizzo_dettaglio_id bigint, indirizzo_libero text, is_normalizzato boolean, stato_id integer, stato_descrizione character varying, stato_iso2 character, regione_id integer, regione_descrizione character varying, provincia_id integer, provincia_sigla character varying, provincia_descrizione character varying, comune_id integer, comune_descrizione character varying, codice_postale_id integer, cap_codice character, locality character varying, administrative_area character varying, sublocality character varying, postal_box character varying)
 LANGUAGE plpgsql
 STABLE ROWS 10
AS $function$
/*
    Funzione: script.fn_get_indirizzo(p_soggetto_ruolo_id, p_tipo_codice)

    Nuova logica:
    - Prova il tipo richiesto (p_tipo_codice).
    - Se non trova indirizzi:
        * legge da config.tipi_ruolo_tipi_indirizzo il fallback_tipo_indirizzo_id
          per (tipo_ruolo del soggetto_ruolo, tipo_indirizzo corrente),
        * risale la catena di fallback finché:
            - trova almeno un indirizzo per un tipo, oppure
            - la catena termina (fallback NULL), oppure
            - rileva un loop nella catena (ciclo A→B→A).

    Per ogni tipo provato, i dati vengono recuperati da:
        script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
  Output:
  - Stesso schema di fn_get_indirizzi_by_ruolo:
    tipo_indirizzo, indirizzo_completo, geoloc,
    id tecnici, flag is_normalizzato,
    stato/regione/provincia/comune/CAP,
    campi "raw" internazionali.
*/

DECLARE
    v_tipo_ruolo_id      bigint;
    v_current_codice     text := p_tipo_codice;
    v_current_tipo_id    bigint;
    v_fallback_tipo_id   bigint;
    v_rows_found         integer;
    v_visited_tipo_ids   bigint[] := '{}'::bigint[];
BEGIN
    -- Ricavo il tipo_ruolo legato al soggetto_ruolo
    SELECT sr.tipo_ruolo_id
    INTO v_tipo_ruolo_id
    FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.id = p_soggetto_ruolo_id;

    IF v_tipo_ruolo_id IS NULL THEN
        -- soggetto_ruolo non valido: nessun indirizzo
        RETURN;
    END IF;

    LOOP
        -- 1) Provo il tipo corrente (v_current_codice)
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

        GET DIAGNOSTICS v_rows_found = ROW_COUNT;

        -- Se ho trovato almeno un indirizzo, ho finito
        IF v_rows_found > 0 THEN
            RETURN;
        END IF;

        -- 2) Nessun indirizzo per questo tipo: cerco fallback in matrice

        -- Ricavo id del tipo_indirizzo corrente
        SELECT ti.id
        INTO v_current_tipo_id
        FROM config.tipi_indirizzi ti
        WHERE ti.codice_interno = v_current_codice;

        IF v_current_tipo_id IS NULL THEN
            -- Tipo non riconosciuto: non posso proseguire
            RETURN;
        END IF;

        -- Protezione da loop nella catena di fallback
        IF v_current_tipo_id = ANY (v_visited_tipo_ids) THEN
            -- Rilevato ciclo A->B->A: esco senza risultati
            RETURN;
        END IF;

        v_visited_tipo_ids := array_append(v_visited_tipo_ids, v_current_tipo_id);

        -- Cerco il prossimo fallback per (tipo_ruolo, tipo_indirizzo corrente)
        SELECT m.fallback_tipo_indirizzo_id
        INTO v_fallback_tipo_id
        FROM config.tipi_ruolo_tipi_indirizzo m
        WHERE m.tipo_ruolo_id     = v_tipo_ruolo_id
          AND m.tipo_indirizzo_id = v_current_tipo_id
          AND m.attivo            = TRUE
          AND (m.valido_dal IS NULL OR m.valido_dal <= current_date)
          AND (m.valido_al  IS NULL OR m.valido_al  >= current_date)
        LIMIT 1;

        -- Nessun fallback configurato: esco senza risultati
        IF v_fallback_tipo_id IS NULL THEN
            RETURN;
        END IF;

        -- Traduco il fallback id in codice_interno per il prossimo ciclo
        SELECT ti.codice_interno
        INTO v_current_codice
        FROM config.tipi_indirizzi ti
        WHERE ti.id = v_fallback_tipo_id;

        IF v_current_codice IS NULL THEN
            -- Configurazione incoerente (id senza codice_interno): esco
            RETURN;
        END IF;

        -- Loop: riprovo con il nuovo tipo (v_current_codice)
    END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
