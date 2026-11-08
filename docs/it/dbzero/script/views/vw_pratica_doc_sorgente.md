{% include-markdown "it/dbzero/script/manual/vw_pratica_doc_sorgente.md" %}
# 🔍 View `vw_pratica_doc_sorgente`

> 📝 **Descrizione**
>
> Una riga per pratica col descrittore del documento PIU' VIVO fra i suoi link (ROOT e COLLEGATO) in pratiche.pratiche_sorgenti. Regola d'ancora, NULL-safe: prima il risolto, poi il vivo (non terminale), poi il ROOT, poi il link piu' recente (ps.id). Cosi' un ordine COLLEGATO vivo accende la pratica preventivo -&gt; ordine senza far regredire preventivo -&gt; commessa (la commessa non risolta perde sul risolto). Link non risolto: risolto=false e stato_* NULL (non la sentinella UNKNOWN di pratiche.fn_stato_sorgente). La chiave del documento nelle colonne del modello: sorgente_id o sorgente_uid, una sola, secondo il key_selector del tipo. Il documento si cerca in script.vw_stato_sorgente sulle sue colonne native, un ramo per chiave (sorgente_chiave_uuid = sorgente_uid, sorgente_chiave_id = sorgente_id), in una LATERAL: dentro la sottoquery la chiave del link e' un parametro esterno, e sotto RLS arriva all'indice di ogni ramo della union (int8eq e uuid_eq sono leakproof). Un OR sulle due chiavi in un ramo solo non scende nella union e legge tutte le tabelle-documento. Sede unica della regola; la legge il backend. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_pratica_doc_sorgente
WITH (security_invoker=on) AS
SELECT DISTINCT ON (ps.pratica_id) ps.pratica_id,
    ps.sorgente_tipo_id,
    ps.sorgente_id,
    ps.sorgente_uid,
    ps.ruolo_link,
    so.descrizione AS sorgente_descrizione,
    COALESCE(ss.risolto, false) AS risolto,
    ss.stato_codice_interno,
    ss.stato_codice,
    ss.stato_descrizione,
    ss.fase,
    ss.esito,
    ss.terminale
   FROM ((pratiche.pratiche_sorgenti ps
     JOIN config.sorgenti so ON ((so.id = ps.sorgente_tipo_id)))
     LEFT JOIN LATERAL ( SELECT v.risolto,
            v.stato_codice_interno,
            v.stato_codice,
            v.stato_descrizione,
            v.fase,
            v.esito,
            v.terminale
           FROM script.vw_stato_sorgente v
          WHERE ((v.sorgente_tipo_id = ps.sorgente_tipo_id) AND (v.sorgente_chiave_uuid = ps.sorgente_uid))
        UNION ALL
         SELECT v.risolto,
            v.stato_codice_interno,
            v.stato_codice,
            v.stato_descrizione,
            v.fase,
            v.esito,
            v.terminale
           FROM script.vw_stato_sorgente v
          WHERE ((v.sorgente_tipo_id = ps.sorgente_tipo_id) AND (v.sorgente_chiave_id = ps.sorgente_id))) ss ON (true))
  ORDER BY ps.pratica_id, COALESCE(ss.risolto, false) DESC, (NOT COALESCE(ss.terminale, false)) DESC, ((ps.ruolo_link)::text = 'ROOT'::text) DESC, ps.id DESC;
```

</div>


---
{% include-markdown "signature-core.md" %}
