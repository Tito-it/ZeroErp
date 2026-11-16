{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_check_coerenza.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_check_coerenza`

```sql
CREATE FUNCTION trgfn_documenti_generati_check_coerenza()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_check_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: alla nascita di una stampa, i suoi riferimenti stanno
--   insieme e il modello puo' stampare con quella versione.
--
-- Regole, nell'ordine:
--   1. la versione appartiene al modello indicato;
--   2. il modello va bene per il documento: stessa sorgente,
--      stesso tipo di output, e la stessa azienda oppure un
--      modello standard (fn_template_motivo_non_coerente);
--   3. il modello stampa oggi, e proprio con questa versione
--      (fn_template_motivo_non_stampabile).
--   Le regole 2 e 3 sono le stesse che la risoluzione applica
--   prima del render.
--
-- Errore: E_DOCUMENTI_GENERATO_COERENZA, col motivo nel contesto.
DECLARE
  v_tv_template_id documenti.template_documenti_versioni.template_documento_id%TYPE;
  -- tipo esplicito: il motivo dei BB, non una colonna
  v_motivo         text;
BEGIN
  SELECT v.template_documento_id
    INTO v_tv_template_id
    FROM documenti.template_documenti_versioni v
   WHERE v.id = NEW.template_versione_id;

  IF v_tv_template_id IS DISTINCT FROM NEW.template_documento_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'motivo', 'VERSIONE_DI_ALTRO_MODELLO',
        'template_versione_id', NEW.template_versione_id,
        'template_documento_id_atteso', v_tv_template_id,
        'template_documento_id_fornito', NEW.template_documento_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  v_motivo := documenti.fn_template_motivo_non_coerente(
      NEW.template_documento_id, NEW.sorgente_tipo_id,
      NEW.emittente_fiscale_id, NEW.tipo_documento_output_id);

  IF v_motivo IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'motivo', v_motivo,
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'tipo_documento_output_id', NEW.tipo_documento_output_id,
        'emittente_fiscale_id', NEW.emittente_fiscale_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  v_motivo := documenti.fn_template_motivo_non_stampabile(
      NEW.template_documento_id, NEW.template_versione_id);

  IF v_motivo IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'template_versione_id', NEW.template_versione_id,
        'motivo', v_motivo
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_check_coerenza()
IS 'Giudica, alla nascita di una stampa, che i suoi riferimenti stiano insieme e che il modello possa stampare: la versione appartiene al modello indicato (motivo VERSIONE_DI_ALTRO_MODELLO); il modello va bene per il documento, stessa sorgente, stesso tipo di output, stessa azienda oppure modello standard (motivi SORGENTE, TIPO, EMITTENTE, MODELLO_INESISTENTE: documenti.fn_template_motivo_non_coerente); il modello stampa oggi, e proprio con la versione della stampa (motivi MODELLO_SPENTO, NESSUNA_VERSIONE_VALIDA, VERSIONE_NON_IN_USO: documenti.fn_template_motivo_non_stampabile). Sono le regole che la risoluzione applica prima del render. Solleva E_DOCUMENTI_GENERATO_COERENZA, col motivo per nome nel contesto. Montata solo su INSERT: un cambio successivo del modello, o il suo spegnimento, non tocca le stampe gia'' fatte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
