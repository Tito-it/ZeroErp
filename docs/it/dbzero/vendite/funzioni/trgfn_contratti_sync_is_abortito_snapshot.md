# ⚙️ Funzione `trgfn_contratti_sync_is_abortito_snapshot`

```sql
CREATE FUNCTION trgfn_contratti_sync_is_abortito_snapshot()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_sync_is_abortito_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: sincronizza is_abortito_snapshot da config.stati_doc_contratti.
-- Prerequisito obbligatorio per la colonna GENERATED validita_attiva:
-- PG calcola le STORED generated dal NEW finale dei BEFORE trigger,
-- quindi il valore corretto di is_abortito_snapshot deve essere
-- disponibile in NEW prima che avvenga il calcolo.
DECLARE
    v_is_abortito config.stati_doc_contratti.is_abortito%TYPE;
BEGIN
    SELECT is_abortito
      INTO v_is_abortito
      FROM config.stati_doc_contratti
     WHERE id = NEW.stato_doc_contratto_id;

    NEW.is_abortito_snapshot := COALESCE(v_is_abortito, false);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_sync_is_abortito_snapshot()
IS 'Trigger BEFORE INSERT/UPDATE OF stato_doc_contratto_id: imposta is_abortito_snapshot da config.stati_doc_contratti. Prerequisito per la colonna GENERATED validita_attiva. rev 2026-05-21.';
```

---
{% include-markdown "signature-core.md" %}
