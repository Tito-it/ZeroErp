{% include-markdown "it/dbzero/pratiche/manual/trgfn_tfap_guard_compatibilita.md" %}
# ⚙️ Funzione `trgfn_tfap_guard_compatibilita`

```sql
CREATE FUNCTION trgfn_tfap_guard_compatibilita()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_tfap_guard_compatibilita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: config-time, un binding di avanzamento su proiezione e'
--   ammesso solo su step non-DOMINIO (D-B3) e non deve coesistere con
--   un handler_eventi COMPLETATO sullo stesso step (D-B10).
DECLARE
  v_modalita pratiche.template_flussi.modalita_esito%TYPE;
  v_codice   pratiche.template_flussi.codice%TYPE;
BEGIN
  SELECT tf.modalita_esito, tf.codice
    INTO v_modalita, v_codice
    FROM pratiche.template_flussi tf
   WHERE tf.id = NEW.template_flusso_id;

  -- Step DOMINIO: la proiezione produce verdetti -> non ammesso.
  IF v_modalita = 'DOMINIO' THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche','pratiche.trgfn_tfap_guard_compatibilita',
      'E_TEMPLATE_FLUSSO_PROIEZIONE_STEP_DOMINIO',
      jsonb_build_object('template_flusso_id', NEW.template_flusso_id,
                         'template_codice', v_codice,
                         'modalita_esito', v_modalita),
      dbops.fn_get_or_create_session_tx_id(),
      COALESCE(v_codice, NEW.template_flusso_id::text));
  END IF;

  -- Mutua esclusione con handler_eventi COMPLETATO ATTIVO: il
  -- conflitto e' fra binding entrambi attivi (un handler disattivato
  -- non dispatcha -> il cutover puo' disattivarlo, non serve DELETE).
  IF NEW.attivo AND EXISTS (
    SELECT 1 FROM pratiche.template_flussi_handler_eventi e
     WHERE e.template_flusso_id = NEW.template_flusso_id
       AND e.evento = 'COMPLETATO'
       AND e.attivo
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche','pratiche.trgfn_tfap_guard_compatibilita',
      'E_TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER',
      jsonb_build_object('template_flusso_id', NEW.template_flusso_id,
                         'template_codice', v_codice,
                         'lato', 'binding_proiezione'),
      dbops.fn_get_or_create_session_tx_id(),
      COALESCE(v_codice, NEW.template_flusso_id::text));
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_tfap_guard_compatibilita()
IS 'BEFORE INSERT OR UPDATE su pratiche.template_flussi_avanzamento_proiezione (GUIDA D4/G2): il binding di avanzamento su proiezione e'' ammesso solo su step non-DOMINIO (D-B3, TEMPLATE_FLUSSO_PROIEZIONE_STEP_DOMINIO 517) e non puo'' coesistere con un handler_eventi COMPLETATO sullo stesso step (D-B10, TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER 518).';
```

</div>

---
{% include-markdown "signature-core.md" %}
