{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_ordine.md" %}
# 🔍 View `vw_stato_sorgente_ordine`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio roll-out): descrittore normalizzato dello stato vivo di ogni ordine di VENDITA — stato nativo (alias fedeli) + fase/esito/terminale da config.stati_doc_ordini (mappa centrata sul ciclo di vendita). Chiave (sorgente_tipo_id, sorgente_uid) con sorgente_uid=(id)::text (key_selector=id); al piu' una riga per chiave. Read-time. Consumata dal motore solo via script.vw_stato_sorgente.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
    sdor.terminale
   FROM ((vendite.ordini o
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_ordini sdor ON ((sdor.id = o.stato_doc_ordine_id)));
```


---
{% include-markdown "signature-core.md" %}
