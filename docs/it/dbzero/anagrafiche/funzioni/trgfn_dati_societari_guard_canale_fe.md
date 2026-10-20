# ⚙️ Funzione `trgfn_dati_societari_guard_canale_fe`

```sql
CREATE FUNCTION trgfn_dati_societari_guard_canale_fe()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_dati_societari_guard_canale_fe()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_contesto  jsonb;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Il canale della fattura elettronica (destinatario_fe) ha
  --   il suo recapito, e il codice SDI ha la sua forma. Montato
  --   BEFORE INSERT OR UPDATE OF destinatario_fe,
  --   pec_fatturazione, codice_sdi.
  -- =========================================================
  IF TG_OP = 'UPDATE'
     AND NEW.destinatario_fe  IS NOT DISTINCT FROM OLD.destinatario_fe
     AND NEW.pec_fatturazione IS NOT DISTINCT FROM OLD.pec_fatturazione
     AND NEW.codice_sdi       IS NOT DISTINCT FROM OLD.codice_sdi THEN
    RETURN NEW;
  END IF;

  v_contesto := jsonb_build_object('dati_societari_id', NEW.id,
                                   'soggetto_id',       NEW.soggetto_id,
                                   'canale',            NEW.destinatario_fe);

  -- 1. La forma del codice, quando c'e' (con qualunque canale)
  IF NEW.codice_sdi IS NOT NULL
     AND NEW.codice_sdi !~ '^[A-Z0-9]{6,7}$' THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche', 'trgfn_dati_societari_guard_canale_fe',
      'E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO',
      v_contesto || jsonb_build_object('campo', 'codice_sdi'),
      NULL::uuid,
      NEW.codice_sdi);
  END IF;

  -- 2. Il canale C pretende il codice
  IF NEW.destinatario_fe = 'C' AND NEW.codice_sdi IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche', 'trgfn_dati_societari_guard_canale_fe',
      'E_DATI_SOCIETARI_CODICE_SDI_MANCANTE',
      v_contesto || jsonb_build_object('campo', 'codice_sdi'),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]);  -- nessun segnaposto nella frase
  END IF;

  -- 3. Il canale P pretende la PEC
  IF NEW.destinatario_fe = 'P'
     AND coalesce(btrim(NEW.pec_fatturazione), '') = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche', 'trgfn_dati_societari_guard_canale_fe',
      'E_DATI_SOCIETARI_PEC_FATTURAZIONE_MANCANTE',
      v_contesto || jsonb_build_object('campo', 'pec_fatturazione'),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]);  -- nessun segnaposto nella frase
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_dati_societari_guard_canale_fe()
IS 'Guard BEFORE INSERT OR UPDATE OF destinatario_fe, pec_fatturazione, codice_sdi su anagrafiche.dati_societari: codice SDI di 6-7 caratteri maiuscoli o cifre; canale C con il codice, canale P con la PEC. Un codice per campo; i CHECK del 20261010-37 fanno da rete. Brief: brief-db-character-n-spazi-di-riempimento D-6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
