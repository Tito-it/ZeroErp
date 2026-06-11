{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_guard_chiusura_flussi.md" %}
# ⚙️ Funzione `trgfn_pratiche_guard_chiusura_flussi`

```sql
CREATE FUNCTION trgfn_pratiche_guard_chiusura_flussi()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_chiusura_flussi()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice_a       config.stati_pratiche.codice_interno%TYPE;
    v_bloccanti      text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Blocca la transizione a CHIUSA se esistono flussi
  --   obbligatori non completati e ancora percorribili
  --   (fn_check_chiusura_pratica). Il ramo morto di un bivio
  --   non blocca; ANNULLATA non passa di qui (stato diverso).
  -- =========================================================

  -- Nessuna transizione: niente da validare.
  IF OLD.stato_id = NEW.stato_id THEN
      RETURN NEW;
  END IF;

  -- Solo verso CHIUSA.
  SELECT sp.codice_interno
    INTO v_codice_a
    FROM config.stati_pratiche sp
   WHERE sp.id = NEW.stato_id;

  IF v_codice_a IS DISTINCT FROM 'CHIUSA' THEN
      RETURN NEW;
  END IF;

  -- Template bloccanti: obbligatori, non completati, percorribili.
  SELECT string_agg(c.codice, ', ' ORDER BY c.codice)
    INTO v_bloccanti
    FROM pratiche.fn_check_chiusura_pratica(NEW.id) c
   WHERE c.bloccante;

  IF v_bloccanti IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
          'pratiche',
          'pratiche.trgfn_pratiche_guard_chiusura_flussi',
          'PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI',
          jsonb_build_object(
              'pratica_id', NEW.id,
              'flussi_bloccanti', v_bloccanti
          ),
          NULL::uuid,
          v_bloccanti
      );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_guard_chiusura_flussi()
IS 'BEFORE UPDATE OF stato_id: blocca la transizione a CHIUSA con flussi obbligatori non completati ancora percorribili (fn_check_chiusura_pratica). Il ramo morto di un bivio non blocca la chiusura.';
```

---
{% include-markdown "signature-core.md" %}
