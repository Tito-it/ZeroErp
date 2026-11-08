{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo.md" %}
# ⚙️ Funzione `fn_pgtap_cliente_ba_del_mondo`

```sql
CREATE FUNCTION fn_pgtap_cliente_ba_del_mondo(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint, p_chiamante text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_cliente_ba_del_mondo(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint, p_chiamante text)
 RETURNS TABLE(billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, utility_id integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il cliente di un builder pgTAP chiesto per billing
--   account — verificato dell'azienda di chi agisce — con le sue
--   chiavi. Building block di fn_pgtap_crea_fattura,
--   fn_pgtap_crea_contratto e fn_pgtap_crea_ordine.
DECLARE
    v_link_sr anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- ⚠️ Il BA chiesto si VERIFICA prima di usarlo: uno di
    --   un'altra azienda produrrebbe una testata che il guard
    --   emittente/BA rifiuta piu' avanti, con un messaggio che
    --   non nomina la fixture.
    SELECT efba.emittente_soggetto_ruolo_id INTO v_link_sr
      FROM anagrafiche.emittenti_fiscali_billing_account efba
     WHERE efba.billing_account_id = p_billing_account_id;

    IF v_link_sr IS DISTINCT FROM p_emittente_soggetto_ruolo_id THEN
        RAISE EXCEPTION
            '%: il billing account % e'' legato all''emittente sr = % e non a % (l''azienda di chi agisce): il documento si chiede su un BA costruito dallo stesso mondo',
            p_chiamante, p_billing_account_id, v_link_sr, p_emittente_soggetto_ruolo_id;
    END IF;

    RETURN QUERY
    SELECT ba.id, ba.istanza_utility_id, ba.soggetto_ruolo_id, ba.utility_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_cliente_ba_del_mondo(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint, p_chiamante text)
IS 'Fixture pgTAP, building block: verifica che un billing account sia legato all''azienda di chi agisce (anagrafiche.emittenti_fiscali_billing_account, non in RLS) e solleva prima di costruire, nominando la fixture chiamante (p_chiamante), se e'' di un''altra azienda o di nessuna; altrimenti torna BA, istanza, soggetto_ruolo e utility. Sede unica della verifica: la chiamano dbops.fn_pgtap_cliente_del_builder (per i builder di documento) e dbops.fn_pgtap_crea_mondo_cliente. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
