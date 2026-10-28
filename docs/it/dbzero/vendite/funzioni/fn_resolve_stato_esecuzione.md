{% include-markdown "it/dbzero/vendite/manual/fn_resolve_stato_esecuzione.md" %}
# ⚙️ Funzione `fn_resolve_stato_esecuzione`

```sql
CREATE FUNCTION fn_resolve_stato_esecuzione(p_stato_source text, p_has_critical boolean, p_fatturato boolean, p_default_stato_esecuzione character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_stato_esecuzione(p_stato_source text DEFAULT NULL::text, p_has_critical boolean DEFAULT false, p_fatturato boolean DEFAULT false, p_default_stato_esecuzione character varying DEFAULT 'PENDING'::character varying)
 RETURNS character varying
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
  v_source  text;
  v_default vendite.fatturazione_lotti_fatture.stato_esecuzione%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizzare e risolvere lo stato_esecuzione runtime
  --   evitando duplicazioni CASE nelle funzioni lotto/attivita.
  --
  -- Regole:
  --   - critical=true   -> ERRORE
  --   - fatturato=true  -> COMPLETED
  --   - mapping source:
  --       IN_ESECUZIONE -> RUNNING
  --       COMPLETATO    -> COMPLETED
  --       ERRORE        -> ERRORE
  --       PENDING/RUNNING/COMPLETED pass-through
  --   - fallback su default (PENDING)
  --
  -- rev 2026-08-04 (D-M): via `p_esclusa`, che era il primo ramo
  --   e non e' mai stato preso — il flag e' dormiente da sempre.
  --   Via con lui `p_current_stato_esecuzione`, che serviva SOLO
  --   a quel ramo: un parametro che nessun chiamante puo' piu'
  --   influenzare e' una bugia nella firma.
  -- =========================================================
  IF COALESCE(p_has_critical, false) THEN
    RETURN 'ERRORE';
  END IF;

  IF COALESCE(p_fatturato, false) THEN
    RETURN 'COMPLETED';
  END IF;

  v_source  := upper(btrim(COALESCE(p_stato_source, '')));
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

COMMENT ON FUNCTION vendite.fn_resolve_stato_esecuzione(p_stato_source text, p_has_critical boolean, p_fatturato boolean, p_default_stato_esecuzione character varying)
IS 'Helper condiviso: risolve stato_esecuzione con priorita critical/fatturato e mapping stato_lotto. rev 2026-08-04 (D-M): firma da sei a quattro parametri. Via p_esclusa — il flag fatturazione_lotti_fatture.esclusa e'' dormiente da sempre (nessuno lo valorizza) e quel ramo non e'' mai stato preso — e via con lui p_current_stato_esecuzione, che era usato SOLO dentro quel ramo. ⚠️ La firma vecchia a sei parametri e'' stata DROPpata per intero e non sostituita: togliere un parametro crea un overload, e con i DEFAULT su tutti le chiamate esistenti sarebbero diventate ambigue.';
```

</div>

---
{% include-markdown "signature-core.md" %}
