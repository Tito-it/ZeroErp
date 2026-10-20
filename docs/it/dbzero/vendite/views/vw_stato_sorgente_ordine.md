{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_ordine.md" %}
# 🔍 View `vw_stato_sorgente_ordine`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio roll-out): descrittore normalizzato dello stato vivo di ogni ordine di VENDITA — stato nativo (alias fedeli) + fase/esito/terminale da config.stati_doc_ordini (mappa centrata sul ciclo di vendita). Chiave (sorgente_tipo_id, sorgente_uid) con sorgente_uid=(id)::text (key_selector=id); al piu' una riga per chiave. Read-time. Consumata dal motore solo via script.vw_stato_sorgente. ⭐ rev 2026-10-05 (20261005-23): espone in coda la chiave nel suo tipo — sorgente_chiave_id = id (bigint), sorgente_chiave_uuid NULL — accanto alla forma testuale sorgente_uid, che resta la chiave del lineage e delle join. Serve a chi cerca UN documento: sotto RLS il confronto sul testo non arriva all'indice (int8out non e' leakproof), quello sul bigint si'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_ordine
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (o.id)::text AS sorgente_uid,
    sdor.codice_interno AS stato_codice_interno,
    sdor.codice AS stato_codice,
    sdor.descrizione AS stato_descrizione,
    sdor.fase,
    sdor.esito,
    sdor.terminale,
    NULL::uuid AS sorgente_chiave_uuid,
    o.id AS sorgente_chiave_id
   FROM ((vendite.ordini o
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_ordini sdor ON ((sdor.id = o.stato_doc_ordine_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
