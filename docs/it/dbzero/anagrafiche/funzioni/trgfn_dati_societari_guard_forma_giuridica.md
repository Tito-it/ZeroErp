{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_dati_societari_guard_forma_giuridica.md" %}
# ⚙️ Funzione `trgfn_dati_societari_guard_forma_giuridica`

```sql
CREATE FUNCTION trgfn_dati_societari_guard_forma_giuridica()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: la forma giuridica dei dati societari regge, nell'ordine:
--   1. paese del soggetto            -> E_FORMA_GIURIDICA_PAESE
--   2. ammessa dalla natura          -> E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO
--   3. REA secondo rea_policy        -> E_REA_OBBLIGATORIO / E_REA_NON_AMMESSO
--   4. capitale secondo capitale_sociale_policy
--                                    -> E_CAPITALE_SOCIALE_OBBLIGATORIO / _NON_AMMESSO
-- REQUIRED = presente, NONE = assente, OPTIONAL = libero. La coppia
--   provincia/numero REA la tiene chk_dati_societari_rea_coppia.
-- Tace con forma NULL (dal 20261011-03 la colonna e' NOT NULL), con
--   soggetto o forma inesistenti (FK) e, sulla sola matrice, col soggetto
--   senza natura (lo rifiuta trgfn_dati_societari_guard_tipo_soggetto).
-- Il cambio di natura del soggetto lo giudica il guard al COMMIT su
--   anagrafiche.soggetti (trgfn_soggetti_guard_forma_giuridica_natura).
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (C-1, B-6).
-- =========================================================
DECLARE
    v_sogg_stato_id  anagrafiche.soggetti.stato_id%TYPE;
    v_natura_id      anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_forma_stato_id config.forme_giuridiche.stato_id%TYPE;
    v_forma          config.forme_giuridiche.descrizione%TYPE;
    v_rea_policy     config.forme_giuridiche.rea_policy%TYPE;
    v_cap_policy     config.forme_giuridiche.capitale_sociale_policy%TYPE;
    v_natura         config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_paese          config.stati.descrizione%TYPE;
BEGIN
    IF NEW.forma_giuridica_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT s.stato_id, s.tipo_soggetto_dettaglio_id
      INTO v_sogg_stato_id, v_natura_id
      FROM anagrafiche.soggetti s
     WHERE s.id = NEW.soggetto_id;
    IF NOT FOUND THEN
        RETURN NEW;   -- la FK verso anagrafiche.soggetti parla dopo
    END IF;

    SELECT fg.stato_id, fg.descrizione, fg.rea_policy, fg.capitale_sociale_policy
      INTO v_forma_stato_id, v_forma, v_rea_policy, v_cap_policy
      FROM config.forme_giuridiche fg
     WHERE fg.id = NEW.forma_giuridica_id;
    IF NOT FOUND THEN
        RETURN NEW;   -- la FK verso config.forme_giuridiche parla dopo
    END IF;

    -- 1. Paese
    IF v_sogg_stato_id IS DISTINCT FROM v_forma_stato_id THEN
        SELECT st.descrizione INTO v_paese FROM config.stati st WHERE st.id = v_sogg_stato_id;
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica',
            'E_FORMA_GIURIDICA_PAESE',
            jsonb_build_object('campo',              'forma_giuridica_id',
                               'soggetto_id',        NEW.soggetto_id,
                               'forma_giuridica_id', NEW.forma_giuridica_id,
                               'soggetto_stato_id',  v_sogg_stato_id,
                               'forma_stato_id',     v_forma_stato_id),
            NEW.tx_id,
            COALESCE(v_forma, NEW.forma_giuridica_id::text),
            COALESCE(v_paese, v_sogg_stato_id::text));
    END IF;

    -- 2. Ammessa dalla natura (C-1)
    IF v_natura_id IS NOT NULL
       AND NOT anagrafiche.fn_forma_giuridica_ammessa(
                   NEW.forma_giuridica_id, v_natura_id,
                   script.fn_giorno_operativo(now())) THEN
        SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura
          FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = v_natura_id;
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica',
            'E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO',
            jsonb_build_object('campo',                      'forma_giuridica_id',
                               'soggetto_id',                NEW.soggetto_id,
                               'forma_giuridica_id',         NEW.forma_giuridica_id,
                               'tipo_soggetto_dettaglio_id', v_natura_id),
            NEW.tx_id,
            COALESCE(v_forma, NEW.forma_giuridica_id::text),
            v_natura);
    END IF;

    -- 3. REA (B-6). La coppia la tiene il CHECK: basta il numero.
    IF v_rea_policy = 'REQUIRED' AND NEW.iscrizione_rea IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica',
            'E_REA_OBBLIGATORIO',
            jsonb_build_object('campo',              'iscrizione_rea',
                               'soggetto_id',        NEW.soggetto_id,
                               'forma_giuridica_id', NEW.forma_giuridica_id),
            NEW.tx_id,
            COALESCE(v_forma, NEW.forma_giuridica_id::text));
    END IF;
    IF v_rea_policy = 'NONE' AND NEW.iscrizione_rea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica',
            'E_REA_NON_AMMESSO',
            jsonb_build_object('campo',              'iscrizione_rea',
                               'soggetto_id',        NEW.soggetto_id,
                               'forma_giuridica_id', NEW.forma_giuridica_id),
            NEW.tx_id,
            COALESCE(v_forma, NEW.forma_giuridica_id::text));
    END IF;

    -- 4. Capitale sociale (B-6)
    IF v_cap_policy = 'REQUIRED' AND NEW.capitale_sociale IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica',
            'E_CAPITALE_SOCIALE_OBBLIGATORIO',
            jsonb_build_object('campo',              'capitale_sociale',
                               'soggetto_id',        NEW.soggetto_id,
                               'forma_giuridica_id', NEW.forma_giuridica_id),
            NEW.tx_id,
            COALESCE(v_forma, NEW.forma_giuridica_id::text));
    END IF;
    IF v_cap_policy = 'NONE' AND NEW.capitale_sociale IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_dati_societari_guard_forma_giuridica',
            'E_CAPITALE_SOCIALE_NON_AMMESSO',
            jsonb_build_object('campo',              'capitale_sociale',
                               'soggetto_id',        NEW.soggetto_id,
                               'forma_giuridica_id', NEW.forma_giuridica_id),
            NEW.tx_id,
            COALESCE(v_forma, NEW.forma_giuridica_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica()
IS 'Guard BEFORE INSERT OR UPDATE OF forma_giuridica_id, soggetto_id, id_prov_iscri_rea, iscrizione_rea, capitale_sociale su anagrafiche.dati_societari. La forma regge, nell''ordine: paese del soggetto (E_FORMA_GIURIDICA_PAESE); ammessa dalla natura (anagrafiche.fn_forma_giuridica_ammessa, E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO, C-1); REA secondo rea_policy (E_REA_OBBLIGATORIO / E_REA_NON_AMMESSO) e capitale secondo capitale_sociale_policy (E_CAPITALE_SOCIALE_OBBLIGATORIO / _NON_AMMESSO), B-6: REQUIRED presente, NONE assente, OPTIONAL libero. Tace con forma NULL (la colonna e'' NOT NULL dal 20261011-03), con soggetto o forma inesistenti e, sulla matrice, col soggetto senza natura. Il cambio di natura del soggetto lo giudica il guard al COMMIT su anagrafiche.soggetti. Brief: brief-db-dati-fiscali-e-societari-del-soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
