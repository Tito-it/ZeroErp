{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_cliente_del_builder.md" %}
# ⚙️ Funzione `fn_pgtap_cliente_del_builder`

```sql
CREATE FUNCTION fn_pgtap_cliente_del_builder(p_etichetta text, p_billing_account_id bigint, p_chiamante text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_cliente_del_builder(p_etichetta text, p_billing_account_id bigint, p_chiamante text)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, auth_user_id integer, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: il cliente su cui un builder pgTAP scrive. Col billing
--   account di un'altra fixture: l'azienda di chi agisce e quel
--   BA, verificato. Senza: il mondo (un cliente nuovo).
DECLARE
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
BEGIN
    IF p_billing_account_id IS NULL THEN
        RETURN QUERY
        SELECT m.emittente_fiscale_id, m.emittente_soggetto_ruolo_id,
               m.auth_user_id, m.billing_account_id, m.istanza_utility_id,
               m.cliente_soggetto_ruolo_id, m.utility_id
          FROM dbops.fn_pgtap_crea_mondo_cliente(p_etichetta) m;
        RETURN;
    END IF;

    -- L'azienda di chi agisce, senza costruire un cliente.
    SELECT a.emittente_fiscale_id, a.emittente_soggetto_ruolo_id, a.auth_user_id
      INTO v_ef_id, v_ef_sr_id, v_user_id
      FROM dbops.fn_pgtap_azienda_di_chi_agisce(p_chiamante) a;

    -- ⚠️ Il BA chiesto si VERIFICA prima di usarlo: uno di
    --   un'altra azienda solleva qui, nominando il builder.
    RETURN QUERY
    SELECT v_ef_id, v_ef_sr_id, v_user_id,
           c.billing_account_id, c.istanza_utility_id,
           c.cliente_soggetto_ruolo_id, c.utility_id
      FROM dbops.fn_pgtap_cliente_ba_del_mondo(
               p_billing_account_id, v_ef_sr_id, p_chiamante) c;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_cliente_del_builder(p_etichetta text, p_billing_account_id bigint, p_chiamante text)
IS 'Fixture pgTAP, building block dei builder di commessa, contratto, bolla senza ordine, fattura, lotto e ordine: il cliente su cui il builder scrive. Senza billing account: il mondo (dbops.fn_pgtap_crea_mondo_cliente: azienda, operatore, contesto e un cliente nuovo). Col billing account di un''altra fixture: l''azienda di chi agisce (dbops.fn_pgtap_azienda_di_chi_agisce, serve un contesto aperto) e quel BA verificato (dbops.fn_pgtap_cliente_ba_del_mondo: uno di un''altra azienda solleva, nominando p_chiamante), senza costruire un cliente in piu''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
