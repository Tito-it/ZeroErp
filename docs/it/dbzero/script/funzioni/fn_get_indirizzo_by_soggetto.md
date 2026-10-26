{% include-markdown "it/dbzero/script/manual/fn_get_indirizzo_by_soggetto.md" %}
# ⚙️ Funzione `fn_get_indirizzo_by_soggetto`

```sql
CREATE FUNCTION fn_get_indirizzo_by_soggetto(p_soggetto_id uuid, p_tipo_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
  /*
    Restituisce l'indirizzo di un soggetto per tipo_codice richiesto.
    Se non trova indirizzi per quel tipo, segue la catena di fallback
    configurata in config.tipi_soggetto_dettaglio_tipi_indirizzo
    fino a trovare un match o esaurire i fallback.

    Regole:
      - Recupera tipo_soggetto_dettaglio_id dal soggetto
      - Loop: cerca indirizzo per tipo corrente
      - Se trovato: ritorna. Se non trovato: segue fallback
      - Protezione anti-loop circolare via v_visited_tipo_ids
  */

  -- Recupera il tipo soggetto dettaglio per determinare la catena fallback
  SELECT s.tipo_soggetto_dettaglio_id INTO v_tipo_soggetto_dettaglio_id
  FROM anagrafiche.soggetti s WHERE s.id = p_soggetto_id;
  IF v_tipo_soggetto_dettaglio_id IS NULL THEN RETURN; END IF;

  LOOP
    -- Il tipo si confronta per ID (rev 20260923-49): la vista espone in
    -- tipo_indirizzo_codice il CODICE (display, mutabile), il parametro e' il
    -- CODICE_INTERNO. Confrontati come testo non si incontravano mai.
    SELECT ti.id INTO v_current_tipo_id
    FROM config.tipi_indirizzi ti WHERE ti.codice_interno = v_current_codice;
    IF v_current_tipo_id IS NULL THEN RETURN; END IF;

    -- Cerca indirizzi per il tipo corrente
    RETURN QUERY
    SELECT * FROM anagrafiche.vw_indirizzi_resolved_soggetto r
    WHERE r.soggetto_id = p_soggetto_id AND r.tipo_indirizzo_id = v_current_tipo_id;

    GET DIAGNOSTICS v_rows_found = ROW_COUNT;
    IF v_rows_found > 0 THEN RETURN; END IF;

    -- Nessun indirizzo trovato: cerca fallback
    -- Protezione anti-loop circolare
    IF v_current_tipo_id = ANY (v_visited_tipo_ids) THEN RETURN; END IF;
    v_visited_tipo_ids := array_append(v_visited_tipo_ids, v_current_tipo_id);

    -- Legge il fallback dalla matrice tipo_soggetto_dettaglio / tipo_indirizzo
    SELECT m.fallback_tipo_indirizzo_id INTO v_fallback_tipo_id
    FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
    WHERE m.tipo_soggetto_dettaglio_id = v_tipo_soggetto_dettaglio_id
      AND m.tipo_indirizzo_id = v_current_tipo_id
      AND m.attivo = TRUE
      AND (m.valido_dal IS NULL OR m.valido_dal <= (SELECT script.fn_data_operativa()))
      AND (m.valido_al IS NULL OR m.valido_al >= (SELECT script.fn_data_operativa()))
    LIMIT 1;
    IF v_fallback_tipo_id IS NULL THEN RETURN; END IF;

    -- Risolve il codice del tipo fallback per il prossimo ciclo
    SELECT ti.codice_interno INTO v_current_codice
    FROM config.tipi_indirizzi ti WHERE ti.id = v_fallback_tipo_id;
    IF v_current_codice IS NULL THEN RETURN; END IF;
  END LOOP;
END;
$function$

COMMENT ON FUNCTION script.fn_get_indirizzo_by_soggetto(p_soggetto_id uuid, p_tipo_codice character varying)
IS 'Restituisce l''indirizzo di un soggetto per tipo richiesto, con fallback configurato in tipi_soggetto_dettaglio_tipi_indirizzo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
