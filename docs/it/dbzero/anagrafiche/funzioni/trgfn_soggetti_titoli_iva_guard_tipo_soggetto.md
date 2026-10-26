# ⚙️ Funzione `trgfn_soggetti_titoli_iva_guard_tipo_soggetto`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_guard_tipo_soggetto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: un titolo IVA vigente e' ammesso dalla natura del titolare.
--   Vigente: anagrafiche.fn_titolo_iva_vigente (attivo e valido almeno
--   fino a oggi, D-5). Ammesso: anagrafiche.fn_titolo_iva_ammesso
--   (matrice config.tipi_titolo_iva_tipi_soggetto_dettaglio; nessuna
--   riga = non ammesso, D-1).
-- Aggancio: BEFORE INSERT OR UPDATE OF tipo_titolo_iva_id, soggetto_id,
--   attivo, valido_al — le colonne che possono rendere vigente un titolo
--   non ammesso. imponibile_utilizzato (movimenti) resta fuori.
-- Il cambio di natura del SOGGETTO lo giudica un altro guard, su
--   anagrafiche.soggetti (trgfn_soggetti_guard_titoli_iva_ammessi).
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).
-- =========================================================
DECLARE
    v_natura_id   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_natura      config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_titolo      config.tipi_titolo_iva.descrizione%TYPE;
BEGIN
    -- Un titolo chiuso o scaduto non cambia nessuna aliquota.
    IF NOT anagrafiche.fn_titolo_iva_vigente(NEW.attivo, NEW.valido_al,
                                             script.fn_giorno_operativo(now())) THEN
        RETURN NEW;
    END IF;

    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_natura_id
      FROM anagrafiche.soggetti s
     WHERE s.id = NEW.soggetto_id;

    IF NOT FOUND THEN
        RETURN NEW;   -- la FK verso anagrafiche.soggetti parla dopo
    END IF;

    IF v_natura_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto',
            'E_DATO_FISCALE_SENZA_TIPO_SOGGETTO',
            jsonb_build_object('campo',              'tipo_soggetto_dettaglio_id',
                               'soggetto_id',        NEW.soggetto_id,
                               'tipo_titolo_iva_id', NEW.tipo_titolo_iva_id),
            NEW.tx_id,
            -- frase chiusa: il VARIADIC si passa vuoto ma ESPLICITO
            VARIADIC ARRAY[]::text[]);
    END IF;

    IF anagrafiche.fn_titolo_iva_ammesso(NEW.tipo_titolo_iva_id, v_natura_id) THEN
        RETURN NEW;
    END IF;

    SELECT tt.descrizione INTO v_titolo
      FROM config.tipi_titolo_iva tt WHERE tt.id = NEW.tipo_titolo_iva_id;
    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura
      FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = v_natura_id;

    PERFORM script.fn_log_and_raise_error(
        'database', 'anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto',
        'E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO',
        jsonb_build_object('campo',                      'tipo_titolo_iva_id',
                           'soggetto_id',                NEW.soggetto_id,
                           'tipo_titolo_iva_id',         NEW.tipo_titolo_iva_id,
                           'tipo_soggetto_dettaglio_id', v_natura_id),
        NEW.tx_id,
        COALESCE(v_titolo, NEW.tipo_titolo_iva_id::text),
        v_natura);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto()
IS 'Guard BEFORE INSERT OR UPDATE OF tipo_titolo_iva_id, soggetto_id, attivo, valido_al su anagrafiche.soggetti_titoli_iva: un titolo VIGENTE (anagrafiche.fn_titolo_iva_vigente) deve essere ammesso dalla natura del soggetto (anagrafiche.fn_titolo_iva_ammesso, matrice config.tipi_titolo_iva_tipi_soggetto_dettaglio: nessuna riga = non ammesso). Tipo non ammesso: E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO, campo tipo_titolo_iva_id. Soggetto senza natura: E_DATO_FISCALE_SENZA_TIPO_SOGGETTO. Un titolo chiuso o scaduto non si giudica. imponibile_utilizzato fuori dall''aggancio: un movimento di plafond non inciampa in una regola di anagrafica. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
