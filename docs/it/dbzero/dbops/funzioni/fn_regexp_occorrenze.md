{% include-markdown "it/dbzero/dbops/manual/fn_regexp_occorrenze.md" %}
# ⚙️ Funzione `fn_regexp_occorrenze`

```sql
CREATE FUNCTION fn_regexp_occorrenze(p_testo text, p_pattern text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_regexp_occorrenze(p_testo text, p_pattern text)
 RETURNS SETOF text[]
 LANGUAGE plpgsql
 IMMUTABLE PARALLEL SAFE ROWS 1
AS $function$
BEGIN
    -- Scopo: le occorrenze di p_pattern in p_testo, una riga per
    --   ognuna, i gruppi catturati nell'array: regexp_matches con
    --   'g'. Esiste per DICHIARARE la cardinalita' (ROWS 1):
    --   regexp_matches ne dichiara 10, e nelle viste del presidio
    --   dei codici quel 10, moltiplicato dalle ricorsioni, accende il
    --   JIT su ~300 ms di lavoro vero.
    RETURN QUERY SELECT pg_catalog.regexp_matches(p_testo, p_pattern, 'g');
END;
$function$

COMMENT ON FUNCTION dbops.fn_regexp_occorrenze(p_testo text, p_pattern text)
IS 'Le occorrenze di una regex in un testo, una riga per ognuna coi gruppi catturati nell''array: lo stesso risultato di regexp_matches(testo, pattern, ''g''). Esiste per DICHIARARE la cardinalita'' vera (ROWS 1): regexp_matches ne dichiara 10, e in dbops.vw_funzioni_check_codici quel 10, moltiplicato da due ricorsioni, portava la stima sopra jit_above_cost appena le statistiche di pg_proc contavano piu'' corpi (rosso di test-vw-funzioni-check-codici-sotto-jit-v1 su zeroerp_ci, 2026-10-12). plpgsql perche'' una LANGUAGE sql verrebbe inlineata e il ROWS ignorato. Precedente: 20261008-21 (ROWS 1 dichiarato). Non STRICT: con un argomento NULL non da'' righe, come regexp_matches. Da usare dove la stima moltiplica un piano, non al posto di ogni regexp_matches.';
```

</div>

---
{% include-markdown "signature-core.md" %}
