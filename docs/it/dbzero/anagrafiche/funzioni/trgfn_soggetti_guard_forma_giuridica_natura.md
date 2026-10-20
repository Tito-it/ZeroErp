# ⚙️ Funzione `trgfn_soggetti_guard_forma_giuridica_natura`

```sql
CREATE FUNCTION trgfn_soggetti_guard_forma_giuridica_natura()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: al COMMIT, la natura del soggetto ammette la forma giuridica
--   dei suoi dati societari (anagrafiche.fn_forma_giuridica_ammessa).
-- Aggancio: CONSTRAINT TRIGGER AFTER UPDATE OF tipo_soggetto_dettaglio_id,
--   DEFERRABLE INITIALLY DEFERRED: natura e forma si cambiano nella
--   stessa transazione (prima la natura, poi la forma), e si giudica lo
--   stato finale. Si rileggono le tabelle, non NEW.
-- Tace senza dati societari, con forma o natura NULL.
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (C-1).
-- =========================================================
DECLARE
    v_natura_id anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_forma_id  anagrafiche.dati_societari.forma_giuridica_id%TYPE;
    v_natura    config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_forma     config.forme_giuridiche.descrizione%TYPE;
BEGIN
    SELECT s.tipo_soggetto_dettaglio_id INTO v_natura_id
      FROM anagrafiche.soggetti s WHERE s.id = NEW.id;
    SELECT ds.forma_giuridica_id INTO v_forma_id
      FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = NEW.id;

    IF v_natura_id IS NULL OR v_forma_id IS NULL THEN
        RETURN NULL;
    END IF;

    IF anagrafiche.fn_forma_giuridica_ammessa(v_forma_id, v_natura_id,
                                              script.fn_giorno_operativo(now())) THEN
        RETURN NULL;
    END IF;

    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura
      FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = v_natura_id;
    SELECT fg.descrizione INTO v_forma
      FROM config.forme_giuridiche fg WHERE fg.id = v_forma_id;

    PERFORM script.fn_log_and_raise_error(
        'database', 'anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura',
        'E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA',
        jsonb_build_object('campo',                      'forma_giuridica_id',
                           'soggetto_id',                NEW.id,
                           'tipo_soggetto_dettaglio_id', v_natura_id,
                           'forma_giuridica_id',         v_forma_id),
        NEW.tx_id,
        v_natura,
        COALESCE(v_forma, v_forma_id::text));

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura()
IS 'Guard al COMMIT (constraint trigger AFTER UPDATE OF tipo_soggetto_dettaglio_id, DEFERRABLE INITIALLY DEFERRED) su anagrafiche.soggetti: la natura del soggetto deve ammettere la forma giuridica dei suoi dati societari (anagrafiche.fn_forma_giuridica_ammessa), altrimenti E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA, campo forma_giuridica_id. Differito perche'' natura e forma si cambiano insieme: nella stessa transazione prima la natura, poi la forma (il guard immediato della forma la confronta con la natura nuova). Rilegge le tabelle, non NEW. Tace senza dati societari o con forma o natura NULL. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (C-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
