# ⚙️ Funzione `fn_ddt_trigger_ordine_testata`

```sql
CREATE FUNCTION fn_ddt_trigger_ordine_testata(p_sorgente_tipo_id bigint, p_sorgente_uid uuid, p_sorgente_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_trigger_ordine_testata(p_sorgente_tipo_id bigint, p_sorgente_uid uuid, p_sorgente_id bigint DEFAULT NULL::bigint)
 RETURNS character varying
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT o.fatturazione_trigger
    FROM (config.sorgenti so
      JOIN vendite.ordini o ON (((o.id = fn_ddt_trigger_ordine_testata.p_sorgente_id) OR (o.uid = fn_ddt_trigger_ordine_testata.p_sorgente_uid))))
   WHERE ((so.id = fn_ddt_trigger_ordine_testata.p_sorgente_tipo_id) AND ((so.codice_interno)::text = 'ORDINE_VENDITA'::text));
END

COMMENT ON FUNCTION vendite.fn_ddt_trigger_ordine_testata(p_sorgente_tipo_id bigint, p_sorgente_uid uuid, p_sorgente_id bigint)
IS 'Il fatturazione_trigger dell''ordine sorgente di TESTATA di una bolla: tipo ORDINE_VENDITA e l''ordine cercato con la regola (o.id = p_sorgente_id OR o.uid = p_sorgente_uid). NULL se la bolla non viene da un ordine, se la sorgente manca o se l''ordine non e'' visibile (SECURITY INVOKER: la RLS di chi chiede). Serve alla riga-onere senza legame di fulfillment, scritta a mano sulla bolla, il cui trigger non si legge dal legame. La leggono vendite.fn_ddt_push_diagnosi e script.fn_check_ddt_emittibile. p_sorgente_id e'' in coda, DEFAULT NULL. BEGIN ATOMIC.';
```

</div>

---
{% include-markdown "signature-core.md" %}
