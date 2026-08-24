{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_sync_is_abortito_snapshot.md" %}
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
-- Scopo: sincronizza gli snapshot derivati dallo stato del contratto:
--   is_abortito_snapshot  <- config.stati_doc_contratti.is_abortito
--   is_draft_snapshot     <- config.stati_doc_contratti.is_bozza
-- Deve restare BEFORE: la colonna GENERATED partecipa_overlap_snapshot
-- (= NOT abortito AND NOT draft) e' calcolata dal NEW finale dei BEFORE.
DECLARE
    v_is_abortito config.stati_doc_contratti.is_abortito%TYPE;
    v_is_bozza    config.stati_doc_contratti.is_bozza%TYPE;
BEGIN
    SELECT is_abortito, is_bozza
      INTO v_is_abortito, v_is_bozza
      FROM config.stati_doc_contratti
     WHERE id = NEW.stato_doc_contratto_id;

    NEW.is_abortito_snapshot := COALESCE(v_is_abortito, false);
    NEW.is_draft_snapshot    := COALESCE(v_is_bozza, false);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_sync_is_abortito_snapshot()
IS 'Trigger BEFORE INSERT/UPDATE OF stato_doc_contratto_id (z90): sincronizza is_abortito_snapshot (da is_abortito) e is_draft_snapshot (da is_bozza) di config.stati_doc_contratti. Entrambi alimentano la colonna GENERATED partecipa_overlap_snapshot. rev 2026-06-02.';
```

---
{% include-markdown "signature-core.md" %}
