{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_preventivo.md" %}
# 🔍 View `vw_stato_sorgente_preventivo`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio): descrittore normalizzato dello stato vivo di ogni preventivo — stato nativo (alias fedeli) + fase/esito/terminale dichiarati su config.stati_doc_preventivi. Chiave (sorgente_tipo_id, sorgente_uid) coerente con pratiche.pratiche_sorgenti (key_selector=uid); al piu' una riga per chiave. Read-time (nessun mirror); fotografa lo stato MEMORIZZATO: la transizione EMESSO-&gt;SCADUTO e' asincrona (job notturno). Consumata dal motore solo via script.vw_stato_sorgente. ⭐ rev 2026-10-05 (20261005-23): espone in coda la chiave nel suo tipo — sorgente_chiave_uuid = uid (uuid), sorgente_chiave_id NULL — accanto alla forma testuale sorgente_uid, che resta la chiave del lineage e delle join. Serve a chi cerca UN documento: sotto RLS il confronto sul testo non arriva all'indice (uuid_out non e' leakproof), quello sull'uuid si'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_preventivo
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (p.uid)::text AS sorgente_uid,
    sdp.codice_interno AS stato_codice_interno,
    sdp.codice AS stato_codice,
    sdp.descrizione AS stato_descrizione,
    sdp.fase,
    sdp.esito,
    sdp.terminale,
    p.uid AS sorgente_chiave_uuid,
    NULL::bigint AS sorgente_chiave_id
   FROM ((vendite.preventivi p
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
