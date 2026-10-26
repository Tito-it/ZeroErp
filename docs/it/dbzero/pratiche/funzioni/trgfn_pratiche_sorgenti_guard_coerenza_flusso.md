{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_sorgenti_guard_coerenza_flusso.md" %}
# ⚙️ Funzione `trgfn_pratiche_sorgenti_guard_coerenza_flusso`

```sql
CREATE FUNCTION trgfn_pratiche_sorgenti_guard_coerenza_flusso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: garantire che il flusso d'origine del link (flusso_id)
--   appartenga alla stessa pratica del link. flusso_id ancora il
--   ROOT documento->flusso (brief-db-aggancio-documento-flusso):
--   deve essere un flusso DI quella pratica.
-- Regole:
--   1. Scatta solo se flusso_id e' valorizzato (COLLEGATO -> NULL,
--      non vincolati).
--   2. Se il flusso non esiste, RETURN NEW: la FK
--      fk_pratiche_sorgenti_flusso solleva l'errore corretto.
--   3. Se la pratica del flusso differisce da NEW.pratica_id ->
--      errore parlante.
DECLARE
    v_flusso_pratica_id pratiche.flussi.pratica_id%TYPE;
BEGIN
    -- (1) Solo link agganciati a un flusso.
    IF NEW.flusso_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT f.pratica_id INTO v_flusso_pratica_id
      FROM pratiche.flussi f
     WHERE f.id = NEW.flusso_id;

    -- (2) Flusso inesistente: lascia decidere la FK.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    -- (3) Coerenza pratica del flusso = pratica del link.
    IF v_flusso_pratica_id IS DISTINCT FROM NEW.pratica_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso',
            'E_PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE',
            jsonb_build_object(
                'pratica_id', NEW.pratica_id,
                'flusso_id', NEW.flusso_id,
                'flusso_pratica_id', v_flusso_pratica_id,
                'ruolo_link', NEW.ruolo_link
            ),
            NEW.tx_id,
            NEW.flusso_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso()
IS 'BEFORE INSERT/UPDATE OF flusso_id,pratica_id su pratiche_sorgenti: se flusso_id e'' valorizzato, il flusso deve appartenere alla stessa pratica del link. Flusso inesistente -> lascia sollevare la FK (brief-db-aggancio-documento-flusso).';
```

</div>

---
{% include-markdown "signature-core.md" %}
