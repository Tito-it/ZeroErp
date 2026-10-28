{% include-markdown "it/dbzero/pratiche/manual/trgfn_template_flussi_guard_modalita_esito.md" %}
# ⚙️ Funzione `trgfn_template_flussi_guard_modalita_esito`

```sql
CREATE FUNCTION trgfn_template_flussi_guard_modalita_esito()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_template_flussi_guard_modalita_esito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: invarianti di coerenza della configurazione esito del
--        template-step. I CHECK di dominio vivono come constraint;
--        qui solo coerenza, con errore parlante (config-time).
--        DOMINIO = esito calcolato da un BB di dominio: niente
--        default (Inv3); gli automatismi che scrivono un default
--        devono scrivere un verdetto (Inv4).
BEGIN
  -- Invariante 1: un automatismo deve sapere quale esito scrivere.
  -- (Riformulata per DOMINIO: vale solo per AUTOMATICO/CONTESTUALE.)
  IF NEW.modalita_esito IN ('AUTOMATICO', 'CONTESTUALE')
     AND NEW.esito_default IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_template_flussi_guard_modalita_esito',
      'E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO',
      jsonb_build_object(
        'campo', 'esito_default',
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
      'E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA',
      jsonb_build_object(
        'campo', 'direzione',
        'template_flusso_id', NEW.id,
        'codice',             NEW.codice,
        'direzione',          NEW.direzione
      ),
      NEW.tx_id,
      COALESCE(NEW.codice, ''),
      NEW.direzione
    );
  END IF;

  -- Invariante 3: DOMINIO non ammette esito_default (l'esito e'
  -- calcolato a runtime dal building block di dominio).
  IF NEW.modalita_esito = 'DOMINIO' AND NEW.esito_default IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_template_flussi_guard_modalita_esito',
      'E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO',
      jsonb_build_object(
        'campo', 'esito_default',
        'template_flusso_id', NEW.id,
        'codice',             NEW.codice,
        'esito_default',      NEW.esito_default
      ),
      NEW.tx_id,
      COALESCE(NEW.codice, ''),
      NEW.esito_default
    );
  END IF;

  -- Invariante 4: il default di un automatismo deve essere un
  -- VERDETTO (is_verdetto=true): gli esiti di ramo sono calcolati
  -- dal dominio, mai applicabili come default.
  IF NEW.modalita_esito IN ('AUTOMATICO', 'CONTESTUALE')
     AND NEW.esito_default IS NOT NULL
     AND EXISTS (
       SELECT 1
         FROM config.esiti_flussi_pratiche e
        WHERE e.codice_interno = NEW.esito_default
          AND NOT e.is_verdetto
     ) THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_template_flussi_guard_modalita_esito',
      'E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO',
      jsonb_build_object(
        'campo', 'esito_default',
        'template_flusso_id', NEW.id,
        'codice',             NEW.codice,
        'modalita_esito',     NEW.modalita_esito,
        'esito_default',      NEW.esito_default
      ),
      NEW.tx_id,
      NEW.esito_default,
      COALESCE(NEW.codice, '')
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_template_flussi_guard_modalita_esito()
IS 'BEFORE INSERT OR UPDATE OF modalita_esito/esito_default/direzione su pratiche.template_flussi: enforce Inv1 (esito_default obbligatorio per AUTOMATICO/CONTESTUALE, E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO id 842), Inv2 (AUTOMATICO solo INTERNA, E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA id 843), Inv3 (DOMINIO vieta esito_default, E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO id 844), Inv4 (esito_default di automatismo deve essere verdetto is_verdetto=true, E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO id 845) con errori parlanti. Codici rinominati il 2026-08-05 (20260805-19): i vecchi nomi senza prefisso restano a catalogo ritirati con obsoleto_dal.';
```

</div>

---
{% include-markdown "signature-core.md" %}
