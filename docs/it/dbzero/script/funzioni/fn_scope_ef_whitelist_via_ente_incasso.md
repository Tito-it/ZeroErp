{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_ente_incasso.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_ente_incasso`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_ente_incasso(p_auth_user_id integer, p_ente_incasso_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_ente_incasso(p_auth_user_id integer, p_ente_incasso_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Risolve il canale -> il CONTO su cui atterra il suo denaro ->
    -- il soggetto -> l'emittente, e delega alla canonica. E' D5:
    -- quando il denaro arriva non ha ancora una fattura, e il suo
    -- padrone lo dice il conto.
    -- ⚠️ La catena vive TUTTA in fn_resolve_emittente_fiscale_id,
    --   che e' SECURITY DEFINER e la stessa usata dal guard di
    --   scrittura: due copie della catena sono il modo in cui un
    --   perimetro comincia a rispondere in modo diverso a seconda
    --   di chi chiede.
    -- Canale senza conto risolvibile -> emittente NULL -> la
    -- canonica risponde false (fail-closed).
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('ente_incasso', p_ente_incasso_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_ente_incasso(p_auth_user_id integer, p_ente_incasso_id bigint)
IS 'Scope dell''operatore su un CANALE di incasso: risolve canale -> conto -> soggetto -> emittente e delega alla canonica. ⭐ E'' D5 in una riga: quando il denaro arriva in banca non ha ancora una fattura, e il suo padrone lo dice il conto. La catena vive tutta in script.fn_resolve_emittente_fiscale_id, che e'' SECURITY DEFINER e la stessa che usa il guard di SCRITTURA — cosi'' lettura e scrittura non possono divergere. Fail-closed su catena interrotta.';
```

---
{% include-markdown "signature-core.md" %}
