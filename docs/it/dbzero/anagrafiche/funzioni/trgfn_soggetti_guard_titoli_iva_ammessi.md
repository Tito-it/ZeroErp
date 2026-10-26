# ⚙️ Funzione `trgfn_soggetti_guard_titoli_iva_ammessi`

```sql
CREATE FUNCTION trgfn_soggetti_guard_titoli_iva_ammessi()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_titoli_iva_ammessi()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: chi cambia natura non lascia titoli IVA vigenti che la natura
--   nuova non ammette. L'altro lato di
--   trgfn_soggetti_titoli_iva_guard_tipo_soggetto.
-- Aggancio: BEFORE UPDATE OF tipo_soggetto_dettaglio_id; il confronto
--   OLD/NEW sta qui, perche' UPDATE OF scatta anche a valore uguale.
-- ⛔ I titoli si leggono da anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto,
--   SECURITY DEFINER: la RLS per emittente nasconderebbe quelli degli
--   altri emittenti. Esce solo l'id del tipo.
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).
-- =========================================================
DECLARE
    v_tipo_id config.tipi_titolo_iva.id%TYPE;
    v_titolo  config.tipi_titolo_iva.descrizione%TYPE;
    v_natura  config.tipi_soggetto_dettaglio.descrizione%TYPE;
BEGIN
    IF NEW.tipo_soggetto_dettaglio_id IS NOT DISTINCT FROM OLD.tipo_soggetto_dettaglio_id THEN
        RETURN NEW;
    END IF;

    v_tipo_id := anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto(
                     NEW.id, NEW.tipo_soggetto_dettaglio_id);

    IF v_tipo_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_titoli_iva_ammessi',
            'E_DATO_FISCALE_SENZA_TIPO_SOGGETTO',
            jsonb_build_object('campo',              'tipo_soggetto_dettaglio_id',
                               'soggetto_id',        NEW.id,
                               'tipo_titolo_iva_id', v_tipo_id),
            NEW.tx_id,
            -- frase chiusa: il VARIADIC si passa vuoto ma ESPLICITO
            VARIADIC ARRAY[]::text[]);
    END IF;

    SELECT tt.descrizione INTO v_titolo
      FROM config.tipi_titolo_iva tt WHERE tt.id = v_tipo_id;
    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura
      FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = NEW.tipo_soggetto_dettaglio_id;

    PERFORM script.fn_log_and_raise_error(
        'database', 'anagrafiche.trgfn_soggetti_guard_titoli_iva_ammessi',
        'E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI',
        jsonb_build_object('campo',                      'tipo_soggetto_dettaglio_id',
                           'soggetto_id',                NEW.id,
                           'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                           'tipo_titolo_iva_id',         v_tipo_id),
        NEW.tx_id,
        v_natura,
        COALESCE(v_titolo, v_tipo_id::text));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_titoli_iva_ammessi()
IS 'Guard BEFORE UPDATE OF tipo_soggetto_dettaglio_id su anagrafiche.soggetti: chi cambia natura non lascia titoli IVA VIGENTI che la natura nuova non ammette (E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI, CONFLITTO_STATO, campo tipo_soggetto_dettaglio_id); natura tolta con titoli vigenti: E_DATO_FISCALE_SENZA_TIPO_SOGGETTO. I titoli si leggono da anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto, SECURITY DEFINER, perche'' la RLS per emittente nasconderebbe quelli degli altri emittenti. Si esce chiudendo il titolo (valido_al). L''altro lato e'' trgfn_soggetti_titoli_iva_guard_tipo_soggetto. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
