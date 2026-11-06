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
IS '⭐ rev 2026-11-06 (20261106-24, brief-db-sorgente-documento-e-riga §7.2 lotto 0 giro 0.3): l''ordine di testata si cerca nelle due grammatiche della sorgente: (o.id = p_sorgente_id OR o.uid = p_sorgente_uid). Oggi la bolla porta l''uid dell''ordine; dal lotto T l''id (S-5). Il parametro nuovo e'' in coda, DEFAULT NULL: chi passa solo (tipo, uid) ha il comportamento di prima. La firma (tipo, uid) si ritira (20261106-27). Building block: il fatturazione_trigger dell''ordine sorgente di TESTATA di una bolla (config.sorgenti ORDINE_VENDITA + vendite.ordini.uid = sorgente_uid). NULL se la bolla non viene da un ordine, se la sorgente manca o se l''ordine non e'' visibile (SECURITY INVOKER: la RLS di chi chiede). Serve alla riga-onere SENZA legame di fulfillment, scritta a mano sulla bolla: il suo trigger non si legge dal legame. Sede unica (regola del 2) della lettura che stava in linea in vendite.fn_ddt_push_diagnosi (20261103-39) e in script.fn_check_ddt_emittibile (20261103-41), sostituite da 20261103-44 e -45. BEGIN ATOMIC (linee-guida-sql §5c). brief-db-addebito-trasporto-ordine §9.5 P-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
