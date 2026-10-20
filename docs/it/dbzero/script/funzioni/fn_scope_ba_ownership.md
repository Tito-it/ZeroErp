{% include-markdown "it/dbzero/script/manual/fn_scope_ba_ownership.md" %}
# ⚙️ Funzione `fn_scope_ba_ownership`

```sql
CREATE FUNCTION fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- =========================================================
    -- Scope policy BA_OWNERSHIP, versione ruolo-aware.
    -- Ritorna true se:
    --   1. l'identita (p_identita_id) e' utilizzabile oggi
    --      (script.fn_veste_utilizzabile, rev 2026-10-07)
    --   2. l'identita e' in veste cliente (CLIENTE_PORTALE o
    --      SHOP_CUSTOMER) — filtro interno alla fn
    --   3. il billing_account ha lo stesso soggetto_ruolo
    --      dell'identita
    -- Fail-closed: NULL o identita inesistente/inattiva -> false.
    -- STABLE, inlineable dal planner. Usata sia dal portale
    -- B2B (policy senza filtro canale) sia dallo shop (policy
    -- con filtro canale_origine='SHOP' aggiuntivo).
    -- =========================================================
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN anagrafiche.billing_account  ba
            ON ba.soggetto_ruolo_id = id.soggetto_ruolo_id
         WHERE id.id                = p_identita_id
           -- Rev 2026-10-07: utilizzabile oggi, non solo accesa.
           AND script.fn_veste_utilizzabile(id.id)
           AND id.ruolo_applicativo IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')
           AND ba.id                = p_billing_account_id
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
IS 'Scope policy BA_OWNERSHIP ruolo-aware (post 20-04-2026): true se l''identita e'' in veste cliente (CLIENTE_PORTALE o SHOP_CUSTOMER) attiva e condivide il soggetto_ruolo col BA. Il filtro canale_origine e'' demandato alle policy RLS (portale B2B senza filtro, shop con canale=SHOP). STABLE, inlineable, fail-closed. Rev 2026-10-07 (brief-db-veste-utilizzabile): «attiva» e'' diventata «utilizzabile oggi» (script.fn_veste_utilizzabile): una veste scaduta non vede piu'' i suoi dati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
