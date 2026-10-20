# ⚙️ Funzione `trgfn_soggetti_guard_sesso_policy`

```sql
CREATE FUNCTION trgfn_soggetti_guard_sesso_policy()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_sesso_policy()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: il sesso di un soggetto rispetta la policy della sua natura.
--   config.tipi_soggetto_dettaglio.sesso_policy:
--     REQUIRED  -> obbligatorio (M, F o X): NULL rifiutato;
--     OPTIONAL  -> facoltativo: tutto ammesso;
--     NONE      -> non si indica: un valore rifiutato.
--   Il VALORE (M, F, X o NULL) lo presidia il CHECK chk_soggetti_sesso;
--   qui si decide solo QUANDO serve, cioe' la parte che sta in un'altra
--   tabella e che un CHECK non puo' leggere.
-- Aggancio: BEFORE INSERT OR UPDATE OF sesso, tipo_soggetto_dettaglio_id.
--   Il ramo sulla natura copre il cambio di natura: una PG che diventa PR
--   deve portare il sesso, un PR che diventa PG deve lasciarlo.
--   Nessun altro trigger BEFORE di soggetti scrive queste due colonne
--   (linee-guida-trigger, «UPDATE OF»).
-- ⚠️ Limite dichiarato, come trgfn_soggetti_guard_cf_piva_obbligatori:
--   senza natura (tipo_soggetto_dettaglio_id NULL) non c'e' policy da
--   leggere, e il guard tace. Un id inesistente lo rifiuta la FK, dopo.
-- Brief: brief-db-sesso-senza-default (§3 D2-D4, §4.1 punto 3).
-- =========================================================
DECLARE
    v_policy      config.tipi_soggetto_dettaglio.sesso_policy%TYPE;
    v_descrizione config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_codice      config.tipi_soggetto_dettaglio.codice_interno%TYPE;
BEGIN
    IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT tsd.sesso_policy, tsd.descrizione, tsd.codice_interno
      INTO v_policy, v_descrizione, v_codice
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = NEW.tipo_soggetto_dettaglio_id;

    IF NOT FOUND THEN
        RETURN NEW;   -- la FK fk_soggetti_tipo_soggetto_dettaglio parla dopo
    END IF;

    IF v_policy = 'REQUIRED' AND NEW.sesso IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_sesso_policy',
            'E_SESSO_OBBLIGATORIO',
            jsonb_build_object('campo',                      'sesso',
                               'soggetto_id',                NEW.id,
                               'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                               'codice_interno',             v_codice),
            NEW.tx_id,
            COALESCE(v_descrizione, v_codice));
    END IF;

    IF v_policy = 'NONE' AND NEW.sesso IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_sesso_policy',
            'E_SESSO_NON_AMMESSO',
            jsonb_build_object('campo',                      'sesso',
                               'soggetto_id',                NEW.id,
                               'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                               'codice_interno',             v_codice),
            NEW.tx_id,
            COALESCE(v_descrizione, v_codice));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_sesso_policy()
IS 'Guard BEFORE INSERT OR UPDATE OF sesso, tipo_soggetto_dettaglio_id su anagrafiche.soggetti: il sesso rispetta config.tipi_soggetto_dettaglio.sesso_policy della natura (REQUIRED: NULL rifiutato con E_SESSO_OBBLIGATORIO; NONE: un valore rifiutato con E_SESSO_NON_AMMESSO; OPTIONAL: tutto ammesso). Il valore (M, F, X o NULL) lo presidia il CHECK chk_soggetti_sesso. Senza natura tace, come il guard su CF e P.IVA. Campo «sesso» nel contesto, per il form. Brief: brief-db-sesso-senza-default.';
```

</div>

---
{% include-markdown "signature-core.md" %}
