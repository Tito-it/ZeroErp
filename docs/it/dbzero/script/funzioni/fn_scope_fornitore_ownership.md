{% include-markdown "it/dbzero/script/manual/fn_scope_fornitore_ownership.md" %}
# ⚙️ Funzione `fn_scope_fornitore_ownership`

```sql
CREATE FUNCTION fn_scope_fornitore_ownership(p_identita_id bigint, p_fornitore_sr_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_fornitore_ownership(p_identita_id bigint, p_fornitore_sr_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Match diretto: il target soggetto_ruolo e' quello dell'identita,
    -- e l'identita stessa e' in veste FORNITORE_PORTALE. Evita
    -- false positive su altre identita (es. cliente con stesso sr).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
         WHERE id.id                = p_identita_id
           AND id.soggetto_ruolo_id = p_fornitore_sr_id
           AND id.ruolo_applicativo = 'FORNITORE_PORTALE'
           AND id.attivo            = true
    );
$function$

COMMENT ON FUNCTION script.fn_scope_fornitore_ownership(p_identita_id bigint, p_fornitore_sr_id bigint)
IS 'Scope policy FORNITORE_OWNERSHIP: ritorna true se il soggetto_ruolo del fornitore target coincide con il soggetto_ruolo dell''identita e l''identita e'' in veste FORNITORE_PORTALE attiva. STABLE, inlineable.';
```

---
{% include-markdown "signature-core.md" %}
