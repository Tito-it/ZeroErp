{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_esito_classe.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_esito_classe`

```sql
CREATE FUNCTION trgfn_flussi_guard_esito_classe()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_esito_classe()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: al completamento di un flusso la CLASSE dell'esito deve
--        corrispondere alla modalita_esito del template:
--          DOMINIO     => esito di ramo (is_verdetto = false);
--          non-DOMINIO => verdetto      (is_verdetto = true).
--        Difesa in profondita' autoritativa: vale per qualunque
--        percorso di scrittura (BE di dominio, generico, SQL).
-- Regole:
--   1. Scoped alla TRANSIZIONE verso COMPLETATO: le righe gia'
--      completate (legacy PRA-0000243) restano toccabili.
--   2. Esito NULL a COMPLETATO -> competenza del guard 477.
--   3. Flusso senza template -> classe verdetto (come il BE, che
--      tratta il template assente come MANUALE).
DECLARE
  v_modalita        pratiche.template_flussi.modalita_esito%TYPE;
  v_template_codice pratiche.template_flussi.codice%TYPE;
  v_is_verdetto     config.esiti_flussi_pratiche.is_verdetto%TYPE;
BEGIN
  -- (1) Solo la transizione di completamento. L'evento e' UPDATE OF
  -- stato_id: si esclude lo "stato riscritto identico" (no transizione).
  IF TG_OP = 'UPDATE' AND OLD.stato_id = NEW.stato_id THEN
    RETURN NEW;
  END IF;

  -- (2) Senza esito non c'e' classe da validare (guard 477 presidia).
  IF NEW.esito IS NULL THEN
    RETURN NEW;
  END IF;

  IF NOT EXISTS (
    SELECT 1
      FROM config.stati_flussi_pratiche sfp
     WHERE sfp.id = NEW.stato_id
       AND sfp.codice_interno = 'COMPLETATO'
  ) THEN
    RETURN NEW;
  END IF;

  -- (3) Classe attesa dal template.
  SELECT tf.modalita_esito, tf.codice
    INTO v_modalita, v_template_codice
    FROM pratiche.template_flussi tf
   WHERE tf.id = NEW.template_flusso_id;
  IF NOT FOUND THEN
    v_modalita        := 'MANUALE';
    v_template_codice := NULL;
  END IF;

  -- Classe dell'esito (esistenza gia' garantita da fk_flussi_esito;
  -- guard difensivo comunque).
  SELECT e.is_verdetto
    INTO v_is_verdetto
    FROM config.esiti_flussi_pratiche e
   WHERE e.codice_interno = NEW.esito;
  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  IF v_modalita = 'DOMINIO' AND v_is_verdetto THEN
    -- Il caso PRA-0000243: verdetto generico su step a esito
    -- calcolato dal dominio -> ramo mai attivato, in silenzio.
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_flussi_guard_esito_classe',
      'E_FLUSSI_ESITO_NON_AMMESSO',
      jsonb_build_object(
        'campo', 'esito',
        'flusso_id',          NEW.id,
        'pratica_id',         NEW.pratica_id,
        'template_flusso_id', NEW.template_flusso_id,
        'template_codice',    v_template_codice,
        'modalita_esito',     v_modalita,
        'esito',              NEW.esito
      ),
      NEW.tx_id,
      NEW.esito,
      COALESCE(v_template_codice, NEW.id::text),
      'ramo (calcolato dal dominio)'
    );
  ELSIF v_modalita <> 'DOMINIO' AND NOT v_is_verdetto THEN
    -- Simmetrico: esito di ramo scritto su uno step normale
    -- (prima fermato solo dal guard BE lato operatore).
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_flussi_guard_esito_classe',
      'E_FLUSSI_ESITO_NON_AMMESSO',
      jsonb_build_object(
        'campo', 'esito',
        'flusso_id',          NEW.id,
        'pratica_id',         NEW.pratica_id,
        'template_flusso_id', NEW.template_flusso_id,
        'template_codice',    v_template_codice,
        'modalita_esito',     v_modalita,
        'esito',              NEW.esito
      ),
      NEW.tx_id,
      NEW.esito,
      COALESCE(v_template_codice, NEW.id::text),
      'verdetto'
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_esito_classe()
IS 'BEFORE INSERT OR UPDATE OF stato_id su pratiche.flussi: alla transizione verso COMPLETATO la classe dell''esito deve corrispondere alla modalita_esito del template (DOMINIO => ramo is_verdetto=false, altrimenti verdetto is_verdetto=true) — FLUSSI_ESITO_NON_AMMESSO (504). Scoped alla transizione: righe gia'' COMPLETATE non ri-validate (legacy PRA-0000243).';
```

</div>

---
{% include-markdown "signature-core.md" %}
