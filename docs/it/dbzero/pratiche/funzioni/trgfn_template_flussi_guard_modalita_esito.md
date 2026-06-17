# ⚙️ Funzione `trgfn_template_flussi_guard_modalita_esito`

```sql
CREATE FUNCTION trgfn_template_flussi_guard_modalita_esito()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_template_flussi_guard_modalita_esito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: invarianti di coerenza della configurazione esito del
--        template-step. I CHECK di dominio vivono come constraint;
--        qui solo coerenza, con errore parlante (config-time).
BEGIN
  -- Invariante 1: un automatismo deve sapere quale esito scrivere.
  IF NEW.modalita_esito <> 'MANUALE' AND NEW.esito_default IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_template_flussi_guard_modalita_esito',
      'TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO',
      jsonb_build_object(
        'template_flusso_id', NEW.id,
        'codice',             NEW.codice,
        'modalita_esito',     NEW.modalita_esito
      ),
      NEW.tx_id,
      NEW.modalita_esito,
      COALESCE(NEW.codice, '')
    );
  END IF;

  -- Invariante 2: solo gli step a direzione INTERNA possono
  -- auto-risolversi senza intervento umano (AUTOMATICO).
  IF NEW.modalita_esito = 'AUTOMATICO' AND NEW.direzione <> 'INTERNA' THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_template_flussi_guard_modalita_esito',
      'TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA',
      jsonb_build_object(
        'template_flusso_id', NEW.id,
        'codice',             NEW.codice,
        'direzione',          NEW.direzione
      ),
      NEW.tx_id,
      COALESCE(NEW.codice, ''),
      NEW.direzione
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_template_flussi_guard_modalita_esito()
IS 'BEFORE INSERT OR UPDATE OF modalita_esito/esito_default/direzione su pratiche.template_flussi: enforce Inv1 (esito_default obbligatorio se non MANUALE, 494) e Inv2 (AUTOMATICO solo INTERNA, 495) con errori parlanti.';
```

---
{% include-markdown "signature-core.md" %}
