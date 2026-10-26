{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_esito_completato.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_esito_completato`

```sql
CREATE FUNCTION trgfn_flussi_guard_esito_completato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_esito_completato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una fase (flusso) non puo' chiudersi senza verdetto.
-- Se il nuovo stato e' COMPLETATO l'esito e' obbligatorio.
-- BEFORE INSERT OR UPDATE OF stato_id su pratiche.flussi.
BEGIN
  IF NEW.esito IS NULL
     AND EXISTS (
       SELECT 1
         FROM config.stati_flussi_pratiche sfp
        WHERE sfp.id = NEW.stato_id
          AND sfp.codice_interno = 'COMPLETATO'
     )
  THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_flussi_guard_esito_completato',
      'E_FLUSSI_ESITO_OBBLIGATORIO',
      jsonb_build_object(
        'flusso_id', NEW.id,
        'pratica_id', NEW.pratica_id,
        'template_flusso_id', NEW.template_flusso_id
      ),
      NEW.tx_id,
      NEW.id::text
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_esito_completato()
IS 'BEFORE INSERT OR UPDATE OF stato_id su flussi: COMPLETATO richiede esito NOT NULL (nessuna fase si chiude senza verdetto).';
```

</div>

---
{% include-markdown "signature-core.md" %}
