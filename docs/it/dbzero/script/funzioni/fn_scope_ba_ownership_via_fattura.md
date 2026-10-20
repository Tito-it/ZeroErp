{% include-markdown "it/dbzero/script/manual/fn_scope_ba_ownership_via_fattura.md" %}
# ⚙️ Funzione `fn_scope_ba_ownership_via_fattura`

```sql
CREATE FUNCTION fn_scope_ba_ownership_via_fattura(p_identita_id bigint, p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ba_ownership_via_fattura(p_identita_id bigint, p_fattura_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Join fattura -> billing_account -> identita: il cliente
    -- dell'identita e quello del BA della fattura devono
    -- coincidere. Fattura inesistente -> false (fail-closed).
    SELECT EXISTS (
        SELECT 1
          FROM vendite.fatture              f
          JOIN anagrafiche.billing_account  ba
            ON ba.id = f.billing_account_id
          JOIN anagrafiche.identita_digitali id
            ON id.soggetto_ruolo_id = ba.soggetto_ruolo_id
         WHERE f.id      = p_fattura_id
           AND id.id     = p_identita_id
           -- Rev 2026-10-07: utilizzabile oggi, non solo accesa.
           AND script.fn_veste_utilizzabile(id.id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ba_ownership_via_fattura(p_identita_id bigint, p_fattura_id bigint)
IS 'Scope policy BA_OWNERSHIP via fattura: ritorna true se il billing_account della fattura target appartiene al soggetto_ruolo dell''identita (via BA.soggetto_ruolo_id). Wrapper per tabelle figlie senza billing_account_id diretto (es. vendite.fatture_scadenze). STABLE, inlineable. Rev 2026-10-07 (brief-db-veste-utilizzabile): l''identita'' deve essere utilizzabile oggi (script.fn_veste_utilizzabile), non solo accesa.';
```

</div>

---
{% include-markdown "signature-core.md" %}
