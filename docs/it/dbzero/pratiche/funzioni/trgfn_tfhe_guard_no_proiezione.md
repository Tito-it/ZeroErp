{% include-markdown "it/dbzero/pratiche/manual/trgfn_tfhe_guard_no_proiezione.md" %}
# ⚙️ Funzione `trgfn_tfhe_guard_no_proiezione`

```sql
CREATE FUNCTION trgfn_tfhe_guard_no_proiezione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_tfhe_guard_no_proiezione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: config-time, non si puo' aggiungere un handler_eventi
--   COMPLETATO a uno step che ha gia' un binding di avanzamento su
--   proiezione (mutua esclusione, D-B10, lato simmetrico).
DECLARE
  v_codice pratiche.template_flussi.codice%TYPE;
BEGIN
  IF NEW.evento = 'COMPLETATO' AND NEW.attivo AND EXISTS (
    SELECT 1 FROM pratiche.template_flussi_avanzamento_proiezione b
     WHERE b.template_flusso_id = NEW.template_flusso_id
       AND b.attivo
  ) THEN
    SELECT tf.codice INTO v_codice
      FROM pratiche.template_flussi tf
     WHERE tf.id = NEW.template_flusso_id;
    PERFORM script.fn_log_and_raise_error(
      'pratiche','pratiche.trgfn_tfhe_guard_no_proiezione',
      'E_TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER',
      jsonb_build_object('template_flusso_id', NEW.template_flusso_id,
                         'template_codice', v_codice,
                         'lato', 'handler_eventi'),
      dbops.fn_get_or_create_session_tx_id(),
      COALESCE(v_codice, NEW.template_flusso_id::text));
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_tfhe_guard_no_proiezione()
IS 'BEFORE INSERT OR UPDATE su pratiche.template_flussi_handler_eventi (GUIDA D4/G2, D-B10 lato simmetrico): vieta un handler_eventi COMPLETATO su uno step che ha gia'' un binding di avanzamento su proiezione (TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER 518).';
```

</div>

---
{% include-markdown "signature-core.md" %}
