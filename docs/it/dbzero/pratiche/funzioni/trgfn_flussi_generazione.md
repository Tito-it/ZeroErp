{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_generazione.md" %}
# ⚙️ Funzione `trgfn_flussi_generazione`

```sql
CREATE FUNCTION trgfn_flussi_generazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_generazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_codice_interno config.stati_flussi_pratiche.codice_interno%TYPE;
  v_regola         RECORD;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Generazione automatica cross-pratica.
  --   Quando un flusso TRANSITA a COMPLETATO, cerca regole di
  --   generazione con auto = true e template_flusso_origine
  --   corrispondente, e invoca fn_genera_pratica_da_flusso
  --   per ciascuna regola matching.
  --
  -- Regole:
  --   - Scatta solo alla transizione di stato (idempotenza:
  --     un UPDATE che non cambia stato_id non genera nulla;
  --     il dedup in fn_genera_pratica_da_flusso copre anche
  --     il doppio evento residuo)
  --   - Solo se nuovo stato COMPLETATO e flusso template-based
  --   - Filtra per esito_richiesto (NULL = qualsiasi esito)
  --   - Ignora regole non attive o con auto = false
  -- =========================================================

  -- Idempotenza: genera solo alla TRANSIZIONE di stato.
  IF OLD.stato_id IS NOT DISTINCT FROM NEW.stato_id THEN
    RETURN NEW;
  END IF;

  -- Verifica se il nuovo stato e' COMPLETATO
  SELECT sfp.codice_interno
    INTO v_codice_interno
    FROM config.stati_flussi_pratiche sfp
   WHERE sfp.id = NEW.stato_id;

  IF v_codice_interno <> 'COMPLETATO' THEN
    RETURN NEW;
  END IF;

  -- Solo flussi template-based
  IF NEW.template_flusso_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Cerca regole matching
  FOR v_regola IN
    SELECT rg.id
      FROM pratiche.regole_generazione rg
     WHERE rg.template_flusso_origine_id = NEW.template_flusso_id
       AND rg.auto = true
       AND rg.attivo = true
       AND (
         rg.esito_richiesto IS NULL
         OR rg.esito_richiesto = NEW.esito
       )
  LOOP
    -- Genera la pratica target (dedup interno alla fn)
    PERFORM pratiche.fn_genera_pratica_da_flusso(
      NEW.id,
      v_regola.id
    );
  END LOOP;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_generazione()
IS 'AFTER UPDATE OF stato_id su flussi: genera pratiche cross-pratica solo alla transizione a COMPLETATO (idempotente; dedup in fn_genera_pratica_da_flusso).';
```

</div>

---
{% include-markdown "signature-core.md" %}
