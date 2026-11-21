{% include-markdown "it/dbzero/documenti/manual/trgfn_template_documenti_versioni_block_delete.md" %}
# ⚙️ Funzione `trgfn_template_documenti_versioni_block_delete`

```sql
CREATE FUNCTION trgfn_template_documenti_versioni_block_delete()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_documenti_versioni_block_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca la cancellazione fisica di versioni template
--   quando sono in stato protetto o gia' utilizzate.
--
-- Regole:
--   1. Non si cancellano versioni PUBBLICATA o OBSOLETA
--      (manteniamo la storia per audit dei documenti generati).
--   2. Non si cancellano versioni gia' usate da almeno un
--      documento generato (integrità referenziale storica).
--   3. Solo versioni BOZZA non usate possono essere cancellate.
--
-- Errore:
--   E_DOCUMENTI_VERSIONE_DELETE_BLOCKED
DECLARE
  v_count_documenti integer;
BEGIN
  IF OLD.stato IN ('PUBBLICATA', 'OBSOLETA') THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_template_documenti_versioni_block_delete',
      'E_DOCUMENTI_VERSIONE_DELETE_BLOCKED',
      jsonb_build_object(
        'template_documento_id', OLD.template_documento_id,
        'versione', OLD.versione,
        'stato', OLD.stato
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  SELECT COUNT(*)
    INTO v_count_documenti
    FROM documenti.documenti_generati
   WHERE template_versione_id = OLD.id;

  IF v_count_documenti > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_template_documenti_versioni_block_delete',
      'E_DOCUMENTI_VERSIONE_DELETE_BLOCKED',
      jsonb_build_object(
        'template_documento_id', OLD.template_documento_id,
        'versione', OLD.versione,
        'documento_generati_count', v_count_documenti
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN OLD;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_documenti_versioni_block_delete()
IS 'Si cancella solo una versione in BOZZA che nessuna stampa ha usato (E_DOCUMENTI_VERSIONE_DELETE_BLOCKED): PUBBLICATA e OBSOLETA restano per la ristampa e per l''audit, e una versione citata da una stampa resta per la ristampa fedele. Il secondo rifiuto ripete la FK RESTRICT della stampa per dare il codice parlante: conta le stampe che chi cancella vede, e quelle fuori dal suo perimetro le ferma la FK.';
```

</div>

---
{% include-markdown "signature-core.md" %}
