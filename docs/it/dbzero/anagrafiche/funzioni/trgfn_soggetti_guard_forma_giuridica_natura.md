{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_forma_giuridica_natura.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_forma_giuridica_natura`

```sql
CREATE FUNCTION trgfn_soggetti_guard_forma_giuridica_natura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: al COMMIT, la forma giuridica dei dati societari regge il
--   soggetto com'e' diventato, nell'ordine del guard immediato dei
--   dati societari:
--   1. paese della forma = stato del soggetto -> E_FORMA_GIURIDICA_PAESE
--   2. ammessa dalla natura (anagrafiche.fn_forma_giuridica_ammessa)
--                          -> E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA
-- Aggancio: CONSTRAINT TRIGGER AFTER UPDATE OF tipo_soggetto_dettaglio_id,
--   stato_id, DEFERRABLE INITIALLY DEFERRED: natura (o stato) e forma
--   si cambiano nella stessa transazione, e si giudica lo stato
--   finale. Si rileggono le tabelle, non NEW.
-- Tace senza dati societari o con forma NULL; il punto 2 tace con
--   natura NULL.
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (C-1); il
--   paese dal 2026-11-24 (S41-5, brief-db-revisione-anagrafiche §20).
-- =========================================================
DECLARE
    v_natura_id      anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_sogg_stato_id  anagrafiche.soggetti.stato_id%TYPE;
    v_forma_id       anagrafiche.dati_societari.forma_giuridica_id%TYPE;
    v_forma_stato_id config.forme_giuridiche.stato_id%TYPE;
    v_natura         config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_forma          config.forme_giuridiche.descrizione%TYPE;
    v_paese          config.stati.descrizione%TYPE;
BEGIN
    SELECT s.tipo_soggetto_dettaglio_id, s.stato_id INTO v_natura_id, v_sogg_stato_id
      FROM anagrafiche.soggetti s WHERE s.id = NEW.id;
    SELECT ds.forma_giuridica_id INTO v_forma_id
      FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = NEW.id;

    IF v_forma_id IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT fg.stato_id, fg.descrizione INTO v_forma_stato_id, v_forma
      FROM config.forme_giuridiche fg WHERE fg.id = v_forma_id;

    -- 1. Paese (S41-5)
    IF v_sogg_stato_id IS DISTINCT FROM v_forma_stato_id THEN
        SELECT st.descrizione INTO v_paese FROM config.stati st WHERE st.id = v_sogg_stato_id;
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura',
            'E_FORMA_GIURIDICA_PAESE',
            jsonb_build_object('campo',              'forma_giuridica_id',
                               'soggetto_id',        NEW.id,
                               'forma_giuridica_id', v_forma_id,
                               'soggetto_stato_id',  v_sogg_stato_id,
                               'forma_stato_id',     v_forma_stato_id),
            NEW.tx_id,
            COALESCE(v_forma, v_forma_id::text),
            COALESCE(v_paese, v_sogg_stato_id::text));
    END IF;

    -- 2. Ammessa dalla natura (C-1)
    IF v_natura_id IS NULL
       OR anagrafiche.fn_forma_giuridica_ammessa(v_forma_id, v_natura_id,
                                                 script.fn_giorno_operativo(now())) THEN
        RETURN NULL;
    END IF;

    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura
      FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = v_natura_id;

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
IS 'Guard al COMMIT (constraint trigger AFTER UPDATE OF tipo_soggetto_dettaglio_id, stato_id, DEFERRABLE INITIALLY DEFERRED) su anagrafiche.soggetti: la forma giuridica dei dati societari regge il soggetto com''e'' diventato, nell''ordine del guard immediato trgfn_dati_societari_guard_forma_giuridica. 1. il paese della forma e'' lo stato del soggetto, altrimenti E_FORMA_GIURIDICA_PAESE (dal 2026-11-24: un cambio di stato non rileggeva la forma, S41-5 di brief-db-revisione-anagrafiche §20; lo stato lo cambia solo il SUPER_ADMIN, D-T5-3 a); 2. la natura ammette la forma (anagrafiche.fn_forma_giuridica_ammessa), altrimenti E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA. Campo forma_giuridica_id. Differito perche'' natura o stato e forma si cambiano insieme. Rilegge le tabelle, non NEW. Tace senza dati societari o con forma NULL; il punto 2 tace con natura NULL. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (C-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
