{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_contratto.md" %}
# 🔍 View `vw_stato_sorgente_contratto`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio roll-out): descrittore normalizzato dello stato vivo di ogni contratto — stato nativo (alias fedeli) + fase/esito/terminale da config.stati_doc_contratti. Chiave (sorgente_tipo_id, sorgente_uid) con sorgente_uid=(id)::text (key_selector=id); al piu' una riga per chiave. Read-time. Consumata dal motore solo via script.vw_stato_sorgente. ⭐ rev 2026-10-05 (20261005-23): espone in coda la chiave nel suo tipo — sorgente_chiave_id = id (bigint), sorgente_chiave_uuid NULL — accanto alla forma testuale sorgente_uid, che resta la chiave del lineage e delle join. Serve a chi cerca UN documento: sotto RLS il confronto sul testo non arriva all'indice (int8out non e' leakproof), quello sul bigint si'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_contratto
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (c.id)::text AS sorgente_uid,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.descrizione AS stato_descrizione,
    sdc.fase,
    sdc.esito,
    sdc.terminale,
    NULL::uuid AS sorgente_chiave_uuid,
    c.id AS sorgente_chiave_id
   FROM ((vendite.contratti c
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_contratti sdc ON ((sdc.id = c.stato_doc_contratto_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
