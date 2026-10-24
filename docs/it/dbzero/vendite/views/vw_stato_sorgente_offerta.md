{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_offerta.md" %}
# 🔍 View `vw_stato_sorgente_offerta`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio roll-out): descrittore normalizzato dello stato vivo di ogni offerta commerciale — stato nativo (alias fedeli) + fase/esito/terminale dichiarati su config.stati_doc_offerte. Chiave (sorgente_tipo_id, sorgente_uid) coerente con pratiche_sorgenti (key_selector=uid); al piu' una riga per chiave. Read-time (nessun mirror). Consumata dal motore solo via script.vw_stato_sorgente. ⭐ rev 2026-10-05 (20261005-23): espone in coda la chiave nel suo tipo — sorgente_chiave_uuid = uid (uuid), sorgente_chiave_id NULL — accanto alla forma testuale sorgente_uid, che resta la chiave del lineage e delle join. Serve a chi cerca UN documento: sotto RLS il confronto sul testo non arriva all'indice (uuid_out non e' leakproof), quello sull'uuid si'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_offerta
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (oc.uid)::text AS sorgente_uid,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.descrizione AS stato_descrizione,
    sdo.fase,
    sdo.esito,
    sdo.terminale,
    oc.uid AS sorgente_chiave_uuid,
    NULL::bigint AS sorgente_chiave_id
   FROM ((vendite.offerte_commerciali oc
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = oc.stato_doc_offerta_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
