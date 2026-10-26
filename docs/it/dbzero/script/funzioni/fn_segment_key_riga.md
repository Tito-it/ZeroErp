# ⚙️ Funzione `fn_segment_key_riga`

```sql
CREATE FUNCTION fn_segment_key_riga(p_segment_key character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_segment_key_riga(p_segment_key character varying)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE
AS $function$
-- =========================================================
-- Scopo: la riga del documento da cui viene una riga di
--   commessa, letta dalla chiave (:R:<riga>); NULL se la chiave
--   non ne ha (consumi, righe a mano).
-- Nessun SET: si espande in linea.
-- Brief: brief-db-grammatica-unica-documenti §13.3 (2e).
-- =========================================================
SELECT substring(p_segment_key FROM ':R:([0-9]+)')::bigint;
$function$

COMMENT ON FUNCTION script.fn_segment_key_riga(p_segment_key character varying)
IS 'La riga del documento da cui viene una riga di commessa, letta dalla chiave (:R:<riga>); NULL se la chiave non ne ha. LANGUAGE sql IMMUTABLE senza SET: si espande in linea. Brief: brief-db-grammatica-unica-documenti §13.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
