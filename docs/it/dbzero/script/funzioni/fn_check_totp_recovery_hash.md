{% include-markdown "it/dbzero/script/manual/fn_check_totp_recovery_hash.md" %}
# ⚙️ Funzione `fn_check_totp_recovery_hash`

```sql
CREATE FUNCTION fn_check_totp_recovery_hash(p_hash jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_totp_recovery_hash(p_hash jsonb)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: dire se un mazzo NUOVO di codici di recupero ha la
    --   forma giusta. NULL -> false.
    -- ⚠️ CASE e non AND: l'AND non garantisce l'ordine, e
    --    jsonb_array_length / jsonb_array_elements su uno scalare
    --    sollevano invece di rispondere false.
    SELECT CASE
        WHEN jsonb_typeof(p_hash) IS DISTINCT FROM 'array' THEN false
        WHEN jsonb_array_length(p_hash) = 0 THEN false
        WHEN EXISTS (
                 SELECT 1
                   FROM jsonb_array_elements(p_hash) e(v)
                  WHERE jsonb_typeof(e.v) <> 'string'
                     OR btrim(e.v #>> '{}') = '') THEN false
        ELSE (SELECT count(DISTINCT e.v) FROM jsonb_array_elements(p_hash) e(v))
             = jsonb_array_length(p_hash)
    END;
$function$

COMMENT ON FUNCTION script.fn_check_totp_recovery_hash(p_hash jsonb)
IS 'Un mazzo NUOVO di codici di recupero del secondo fattore ha la forma giusta? true se e'' un array jsonb con almeno un elemento, tutti stringhe non vuote (gli hash calcolati dal backend: il formato e'' suo), senza doppioni (il consumo toglie l''hash con l''operatore jsonb -, che li toglierebbe tutti). Un mazzo vuoto e'' uno stato legittimo della riga (codici finiti), non un mazzo nuovo: e'' un check dei verbi, non un CHECK della tabella. La chiedono script.fn_totp_registra_device e script.fn_totp_rigenera_recovery. NULL -> false. Non solleva (fn_check_*). IMMUTABLE. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
