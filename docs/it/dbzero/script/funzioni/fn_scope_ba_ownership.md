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
    -- Scopo: l'identita' (veste di cliente, CLIENTE_PORTALE o SHOP_CUSTOMER,
    --   utilizzabile oggi) e' il cliente del billing account? Fail-closed:
    --   identita' o BA NULL o inesistenti -> false.
    -- Il filtro canale_origine resta alle policy (portale senza, shop con SHOP).
    -- ⭐ Rev 2026-10-21 (20261021-31, giro 2 di brief-db-perimetro-una-volta-
    --   famiglie-residue): la regola BA_OWNERSHIP e' scritta UNA volta, nei
    --   building block delle policy: il perimetro dell'identita'
    --   (script.fn_get_identita_sr_perimetro: veste di cliente, utilizzabile
    --   oggi), il cliente della riga (script.fn_resolve_controparte_sr_id,
    --   DEFINER: niente policy del padre rieseguita) e il confronto
    --   (script.fn_scope_sr_perimetro). Questa resta per la domanda su UNA
    --   riga (catalogo config.scope_policy, adattatori che la chiamano); le
    --   policy del portale non passano piu' di qui (20261021-32).
    SELECT script.fn_scope_sr_perimetro(
        script.fn_get_identita_sr_perimetro(
            p_identita_id,
            ARRAY['CLIENTE_PORTALE', 'SHOP_CUSTOMER']::config.ruolo_applicativo[]),
        script.fn_resolve_controparte_sr_id('billing_account', p_billing_account_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ba_ownership(p_identita_id bigint, p_billing_account_id bigint)
IS 'Scope policy BA_OWNERSHIP ruolo-aware (post 20-04-2026): true se l''identita e'' in veste cliente (CLIENTE_PORTALE o SHOP_CUSTOMER) attiva e condivide il soggetto_ruolo col BA. Il filtro canale_origine e'' demandato alle policy RLS (portale B2B senza filtro, shop con canale=SHOP). STABLE, inlineable, fail-closed. Rev 2026-10-07 (brief-db-veste-utilizzabile): «attiva» e'' diventata «utilizzabile oggi» (script.fn_veste_utilizzabile): una veste scaduta non vede piu'' i suoi dati. Rev 2026-10-21 (20261021-31, giro 2 di brief-db-perimetro-una-volta-famiglie-residue): la regola e'' scritta una volta nei building block delle policy (script.fn_get_identita_sr_perimetro, script.fn_resolve_controparte_sr_id, script.fn_scope_sr_perimetro) e questa li compone per la domanda su una riga; le policy del portale non passano piu'' di qui. Pretende la veste di cliente (CLIENTE_PORTALE o SHOP_CUSTOMER).';
```

</div>

---
{% include-markdown "signature-core.md" %}
