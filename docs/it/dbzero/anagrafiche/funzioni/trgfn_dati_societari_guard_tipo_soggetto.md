{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_dati_societari_guard_tipo_soggetto.md" %}
# ⚙️ Funzione `trgfn_dati_societari_guard_tipo_soggetto`

```sql
CREATE FUNCTION trgfn_dati_societari_guard_tipo_soggetto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: la riga di dati societari nasce solo su un soggetto la cui
--   natura li ammette (config.tipi_soggetto_dettaglio.dati_societari_policy):
--   NONE -> rifiuto; OPTIONAL, REQUIRED -> ammessi (l'obbligo lo giudica
--   al COMMIT trgfn_soggetti_guard_dati_societari_required).
-- Aggancio: BEFORE INSERT, fase a05: parla prima della forma e del canale.
--   Il soggetto della riga non si cambia (lucchetto
--   E_DATI_SOCIETARI_SOGGETTO_IMMUTABILE); la natura che cambia la giudica
--   anagrafiche.fn_check_cambio_natura_soggetto.
-- =========================================================
DECLARE
    v_cod_int_tipo config.tipi_soggetto_dettaglio.codice_interno%TYPE;
    v_natura       config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_policy       config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
BEGIN
    SELECT tsd.codice_interno,
           COALESCE(tsd.descrizione, tsd.codice_interno),
           tsd.dati_societari_policy
      INTO v_cod_int_tipo, v_natura, v_policy
      FROM anagrafiche.soggetti s
      LEFT JOIN config.tipi_soggetto_dettaglio tsd
             ON tsd.id = s.tipo_soggetto_dettaglio_id
     WHERE s.id = NEW.soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto',
            'E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO',
            jsonb_build_object('soggetto_id', NEW.soggetto_id),
            NEW.tx_id,
            NEW.soggetto_id::text,
            NULL);
    END IF;

    -- Soggetto senza natura, o natura senza policy. Gli argomenti restano
    -- quelli della frase condivisa con trgfn_soggetti_guard_dati_societari_required.
    IF v_policy IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto',
            'E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO',
            jsonb_build_object('soggetto_id',    NEW.soggetto_id,
                               'codice_interno', v_cod_int_tipo),
            NEW.tx_id,
            NEW.soggetto_id::text,
            COALESCE(v_cod_int_tipo, '<NULL>'));
    END IF;

    IF v_policy = 'NONE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto',
            'E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO',
            jsonb_build_object('soggetto_id',           NEW.soggetto_id,
                               'codice_interno',        v_cod_int_tipo,
                               'dati_societari_policy', v_policy),
            NEW.tx_id,
            v_natura);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()
IS 'Guard di anagrafiche.dati_societari (trg_dati_societari_a05_guard_tipo_soggetto_ins, BEFORE INSERT, fase a05: parla prima della forma giuridica e del canale FE): la riga nasce solo su un soggetto esistente (E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO) la cui natura ha una policy dei dati societari (E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO) diversa da NONE (E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO, con la natura nella frase). Solo all''INSERT: il soggetto della riga non si cambia (lucchetto E_DATI_SOCIETARI_SOGGETTO_IMMUTABILE), e la natura che cambia la giudica anagrafiche.fn_check_cambio_natura_soggetto. La variabile della policy segue la colonna (%TYPE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
