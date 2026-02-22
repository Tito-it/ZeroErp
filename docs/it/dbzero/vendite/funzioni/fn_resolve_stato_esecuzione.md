{% include-markdown "it/dbzero/vendite/manual/fn_resolve_stato_esecuzione.md" %}
# ⚙️ Funzione `fn_resolve_stato_esecuzione`

```sql
CREATE FUNCTION fn_resolve_stato_esecuzione(p_stato_source text, p_current_stato_esecuzione character varying, p_has_critical boolean, p_esclusa boolean, p_fatturato boolean, p_default_stato_esecuzione character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_stato_esecuzione(p_stato_source text DEFAULT NULL::text, p_current_stato_esecuzione character varying DEFAULT NULL::character varying, p_has_critical boolean DEFAULT false, p_esclusa boolean DEFAULT false, p_fatturato boolean DEFAULT false, p_default_stato_esecuzione character varying DEFAULT 'PENDING'::character varying)
 RETURNS character varying
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
  v_source text;
  v_default vendite.fatturazione_lotti_fatture.stato_esecuzione%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizzare e risolvere lo stato_esecuzione runtime
  --   evitando duplicazioni CASE nelle funzioni lotto/attivita.
  --
  -- Regole:
  --   - esclusa=true    -> mantiene stato corrente
  --   - critical=true   -> ERRORE
  --   - fatturato=true  -> COMPLETED
  --   - mapping source:
  --       IN_ESECUZIONE -> RUNNING
  --       COMPLETATO    -> COMPLETED
  --       ERRORE        -> ERRORE
  --       PENDING/RUNNING/COMPLETED pass-through
  --   - fallback su default (PENDING)
  -- =========================================================
  IF COALESCE(p_esclusa, false) THEN
    RETURN p_current_stato_esecuzione;
  END IF;

  IF COALESCE(p_has_critical, false) THEN
    RETURN 'ERRORE';
  END IF;

  IF COALESCE(p_fatturato, false) THEN
    RETURN 'COMPLETED';
  END IF;

  v_source := upper(btrim(COALESCE(p_stato_source, '')));
  v_default := upper(btrim(COALESCE(p_default_stato_esecuzione, 'PENDING')));

  IF v_default NOT IN ('PENDING','RUNNING','COMPLETED','ERRORE') THEN
    v_default := 'PENDING';
  END IF;

  IF v_source = '' THEN
    RETURN v_default;
  END IF;

  IF v_source = 'IN_ESECUZIONE' THEN
    RETURN 'RUNNING';
  ELSIF v_source = 'COMPLETATO' THEN
    RETURN 'COMPLETED';
  ELSIF v_source IN ('PENDING','RUNNING','COMPLETED','ERRORE') THEN
    RETURN v_source;
  END IF;

  RETURN v_default;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_stato_esecuzione(p_stato_source text, p_current_stato_esecuzione character varying, p_has_critical boolean, p_esclusa boolean, p_fatturato boolean, p_default_stato_esecuzione character varying)
IS 'Helper condiviso: risolve stato_esecuzione con priorita esclusa/critical/fatturato e mapping stato_lotto.';
```

---
{% include-markdown "signature-core.md" %}
