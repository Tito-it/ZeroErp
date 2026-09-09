# ⚙️ Funzione `fn_scope_ef_whitelist_via_attivita_fatturabile`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id integer, p_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id integer, p_attivita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: perimetro emittente di un'attivita' fatturabile,
    --   risalendo alla COMMESSA.
    -- ⛔ `commessa_id` e non `billing_account_id`: la prima e'
    --   NOT NULL, la seconda no, e una policy costruita su una
    --   chiave nullable ha un buco esatto dove il NULL passa.
    --   Brief §6.1.
    SELECT script.fn_scope_ef_whitelist_via_commessa(
        p_auth_user_id,
        (SELECT af.commessa_id
           FROM vendite.attivita_fatturabili af
          WHERE af.id = p_attivita_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id integer, p_attivita_id bigint)
IS 'Perimetro emittente di una vendite.attivita_fatturabili, risalendo a `commessa_id` (NOT NULL) e delegando a script.fn_scope_ef_whitelist_via_commessa. ⛔ Non si usa `billing_account_id`, che e'' nullable: una policy su una chiave nullable ha un buco esatto dove il NULL passa (brief §6.1). ⚠️ Serve a proteggere le NOTE di attivita'' fatturabile: la tabella attivita_fatturabili resta il debito dichiarato del §6.1. Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
