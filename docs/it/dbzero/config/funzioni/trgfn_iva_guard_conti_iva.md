{% include-markdown "it/dbzero/config/manual/trgfn_iva_guard_conti_iva.md" %}
# ⚙️ Funzione `trgfn_iva_guard_conti_iva`

```sql
CREATE FUNCTION trgfn_iva_guard_conti_iva()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_iva_guard_conti_iva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_acq CHAR(1);
  v_tipo_ven CHAR(1);
BEGIN
  -- 
  -- Constraint trigger per validare i conti IVA in config.iva
  --    conto_iva_acquisti deve riferirsi a un conto di tipo A
  --    conto_iva_vendita deve riferirsi a un conto di tipo V
  -- Usa messaggi centralizzati in config.messaggi_errore
  -- Schema: config
  -- 

  -- Validazione conto acquisti
  IF NEW.conto_iva_acquisti_id IS NOT NULL THEN
    SELECT tipo_conto INTO v_tipo_acq
      FROM config.conti_contabili
     WHERE id = NEW.conto_iva_acquisti_id;
    IF v_tipo_acq IS DISTINCT FROM 'A' THEN

        PERFORM script.fn_log_and_raise_error(
          'database',
          TG_NAME,
          'E_IVA_CONTO_ACQ_ERR',
          jsonb_build_object('campo','conto_iva_acquisti_id','id',NEW.conto_iva_acquisti_id),
          NULL::uuid,
          NEW.conto_iva_acquisti_id::text
        );
    END IF;
  END IF;

  -- Validazione conto vendita
  IF NEW.conto_iva_vendita_id IS NOT NULL THEN
    SELECT tipo_conto INTO v_tipo_ven
      FROM config.conti_contabili
     WHERE id = NEW.conto_iva_vendita_id;
    IF v_tipo_ven IS DISTINCT FROM 'V' THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_IVA_CONTO_VEN_ERR',
        jsonb_build_object('campo','conto_iva_vendita_id','id',NEW.conto_iva_vendita_id),
        NULL::uuid,
        NEW.conto_iva_vendita_id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_iva_guard_conti_iva()
IS 'Controlla i vincoli sui conti IVA in fase di inserimento/aggiornamento.La funzione verifica che i conti IVA di acquisto e vendita siano rispettivamente
     di tipo A (acquisti) e V (vendite).';
```

</div>

---
{% include-markdown "signature-core.md" %}
