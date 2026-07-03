{% include-markdown "it/dbzero/pratiche/manual/trgfn_template_flussi_figli_guard_immutabile.md" %}
# ⚙️ Funzione `trgfn_template_flussi_figli_guard_immutabile`

```sql
CREATE FUNCTION trgfn_template_flussi_figli_guard_immutabile()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: immutabilita' strutturale «Leggera» dei figli di
--        configurazione del template su fork PUBBLICATO. Generica:
--        la colonna FK verso template_flussi arriva in TG_ARGV[0].
DECLARE
  v_rec   jsonb;
  v_tf_id pratiche.template_flussi.id%TYPE;
  v_def   pratiche.workflow_definizioni.id%TYPE;
  v_tx    uuid;
BEGIN
  IF TG_OP = 'DELETE' THEN
    v_rec := to_jsonb(OLD);
  ELSE
    v_rec := to_jsonb(NEW);
  END IF;

  v_tf_id := (v_rec ->> TG_ARGV[0])::integer;
  -- FK non risolvibile (riga incoerente): non e' compito di questo
  -- guard; decidono le FK / gli altri guard.
  IF v_tf_id IS NULL THEN
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
  END IF;

  SELECT tf.definizione_id
    INTO v_def
    FROM pratiche.template_flussi tf
   WHERE tf.id = v_tf_id;

  IF pratiche.fn_check_definizione_congelata(v_def) THEN
    v_tx := NULLIF(v_rec ->> 'tx_id', '')::uuid;
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_template_flussi_figli_guard_immutabile',
      'TEMPLATE_DEFINIZIONE_CONGELATA',
      jsonb_build_object(
        'operazione',        TG_OP,
        'tabella',           TG_TABLE_NAME,
        'template_flusso_id', v_tf_id,
        'definizione_id',     v_def
      ),
      v_tx,
      v_def::text
    );
  END IF;

  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile()
IS 'Guard generico BEFORE INS/UPD/DEL sui figli di configurazione di template_flussi (canali, handler_eventi, competenze, prerequisiti, formule_tempo, regole_generazione): su edizione forkata pubblicata (fn_check_definizione_congelata) ogni scrittura e'' vietata -> TEMPLATE_DEFINIZIONE_CONGELATA (514). La colonna FK verso template_flussi arriva in TG_ARGV[0]. Immutabilita'' strutturale «Leggera» Fase 2b.';
```

---
{% include-markdown "signature-core.md" %}
