{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_guard_chiusura_flussi.md" %}
# ⚙️ Funzione `trgfn_pratiche_guard_chiusura_flussi`

```sql
CREATE FUNCTION trgfn_pratiche_guard_chiusura_flussi()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_chiusura_flussi()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice_a  config.stati_pratiche.codice_interno%TYPE;
    v_bloccanti text;
    v_aperti    text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Blocca la transizione a CHIUSA se la pratica ha ancora lavoro:
  --   (a) flussi obbligatori non completati e ancora percorribili
  --       (fn_check_chiusura_pratica; ramo morto di un bivio non blocca), OPPURE
  --   (b) flussi ISTANZIATI in stato non terminale (fn_pratica_flussi_aperti, D1).
  --   Stesso predicato dell'auto-chiusura (fn_check_pratica_chiudibile).
  --   ANNULLATA non passa di qui (stato diverso da CHIUSA).
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

  -- (a) Template bloccanti: obbligatori, non completati, percorribili.
  SELECT string_agg(c.codice, ', ' ORDER BY c.codice)
    INTO v_bloccanti
    FROM pratiche.fn_check_chiusura_pratica(NEW.id) c
   WHERE c.bloccante;

  IF v_bloccanti IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
          'pratiche',
          'pratiche.trgfn_pratiche_guard_chiusura_flussi',
          'E_PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI',
          jsonb_build_object(
              'pratica_id', NEW.id,
              'flussi_bloccanti', v_bloccanti
          ),
          NULL::uuid,
          v_bloccanti
      );
  END IF;

  -- (b) D1: flussi istanziati ancora aperti (lavoro avviato pendente).
  SELECT string_agg(
           COALESCE(a.codice, 'flusso#' || a.flusso_id) || ' (' || a.stato_codice_interno || ')',
           ', ' ORDER BY COALESCE(a.codice, 'flusso#' || a.flusso_id)
         )
    INTO v_aperti
    FROM pratiche.fn_pratica_flussi_aperti(NEW.id) a;

  IF v_aperti IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
          'pratiche',
          'pratiche.trgfn_pratiche_guard_chiusura_flussi',
          'E_PRATICHE_CHIUSURA_FLUSSI_APERTI',
          jsonb_build_object(
              'pratica_id', NEW.id,
              'flussi_aperti', v_aperti
          ),
          NULL::uuid,
          v_aperti
      );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_guard_chiusura_flussi()
IS 'BEFORE UPDATE OF stato_id: blocca la transizione a CHIUSA se restano (a) flussi obbligatori non completati ancora percorribili (fn_check_chiusura_pratica, err 485) o (b) flussi istanziati non terminali (fn_pratica_flussi_aperti, err 501, D1). Ramo morto di un bivio non blocca. Stesso predicato dell''auto-chiusura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
