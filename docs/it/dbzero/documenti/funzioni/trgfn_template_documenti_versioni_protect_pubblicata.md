{% include-markdown "it/dbzero/documenti/manual/trgfn_template_documenti_versioni_protect_pubblicata.md" %}
# ⚙️ Funzione `trgfn_template_documenti_versioni_protect_pubblicata`

```sql
CREATE FUNCTION trgfn_template_documenti_versioni_protect_pubblicata()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca l'UPDATE su una versione template quando e' in stato PUBBLICATA.
--   Una versione PUBBLICATA è immutabile: HTML, CSS, render engine,
--   validita', template_documento_id, versione non si modificano.
--   Per ogni cambio si crea una nuova BOZZA.
--
-- Errore:
--   E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE
BEGIN
  IF OLD.stato = 'PUBBLICATA' THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_template_documenti_versioni_protect_pubblicata',
      'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
      jsonb_build_object(
        'template_documento_id', OLD.template_documento_id,
        'versione', OLD.versione,
        'stato', OLD.stato
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata()
IS 'Guard A1: blocca UPDATE su versioni template PUBBLICATA. Una versione pubblicata e'' immutabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
