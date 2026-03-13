{% include-markdown "it/dbzero/script/manual/fn_get_indirizzo_by_soggetto.md" %}
# ⚙️ Funzione `fn_get_indirizzo_by_soggetto`

```sql
CREATE FUNCTION fn_get_indirizzo_by_soggetto(p_soggetto_id uuid, p_tipo_codice character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo_by_soggetto(p_soggetto_id uuid, p_tipo_codice character varying)
 RETURNS SETOF anagrafiche.vw_indirizzi_resolved_soggetto
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_tipo_soggetto_dettaglio_id anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
  v_current_codice config.tipi_indirizzi.codice_interno%TYPE := p_tipo_codice;
  v_current_tipo_id config.tipi_indirizzi.id%TYPE;
  v_fallback_tipo_id config.tipi_soggetto_dettaglio_tipi_indirizzo.fallback_tipo_indirizzo_id%TYPE;
  v_rows_found integer;
  v_visited_tipo_ids config.tipi_indirizzi.id%TYPE[] := '{}'::integer[];
BEGIN
  -- Recupera tipo_soggetto_dettaglio per risolvere la matrice fallback
  SELECT s.tipo_soggetto_dettaglio_id
  INTO v_tipo_soggetto_dettaglio_id
  FROM anagrafiche.soggetti s
  WHERE s.id = p_soggetto_id;

  IF v_tipo_soggetto_dettaglio_id IS NULL THEN
    RETURN;
  END IF;

  -- Loop con fallback: cerca indirizzo per tipo richiesto,
  -- se non trovato segue la catena fallback su
  -- config.tipi_soggetto_dettaglio_tipi_indirizzo
  LOOP
    RETURN QUERY
    SELECT *
    FROM anagrafiche.vw_indirizzi_resolved_soggetto r
    WHERE r.soggetto_id = p_soggetto_id
      AND r.tipo_indirizzo_codice = v_current_codice;

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
      RETURN;
    END IF;

    -- Protezione anti-loop circolare
    IF v_current_tipo_id = ANY (v_visited_tipo_ids) THEN
      RETURN;
    END IF;

    v_visited_tipo_ids := array_append(v_visited_tipo_ids, v_current_tipo_id);

    -- Cerca fallback nella matrice tipo_soggetto_dettaglio/tipo_indirizzo
    SELECT m.fallback_tipo_indirizzo_id
    INTO v_fallback_tipo_id
    FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
    WHERE m.tipo_soggetto_dettaglio_id = v_tipo_soggetto_dettaglio_id
      AND m.tipo_indirizzo_id = v_current_tipo_id
      AND m.attivo = TRUE
      AND (m.valido_dal IS NULL OR m.valido_dal <= current_date)
      AND (m.valido_al IS NULL OR m.valido_al >= current_date)
    LIMIT 1;

    IF v_fallback_tipo_id IS NULL THEN
      RETURN;
    END IF;

    -- Passa al codice del tipo fallback per il prossimo ciclo
    SELECT ti.codice_interno
    INTO v_current_codice
    FROM config.tipi_indirizzi ti
    WHERE ti.id = v_fallback_tipo_id;

    IF v_current_codice IS NULL THEN
      RETURN;
    END IF;
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
