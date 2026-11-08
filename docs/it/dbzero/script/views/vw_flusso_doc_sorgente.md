# 🔍 View `vw_flusso_doc_sorgente`

> 📝 **Descrizione**
>
> Una riga per flusso di pratica col descrittore del suo documento, fra i link di pratiche.pratiche_sorgenti con quel flusso_id. Regola d'ancora, NULL-safe: prima il ROOT (il documento del passo: un flusso ne ha uno solo, uq_pratiche_sorgenti_flusso_root), poi lo spareggio della pratica: il risolto, il vivo (non terminale), il link piu' recente (ps.id). Gemella di script.vw_pratica_doc_sorgente, che e' la sede per pratica: stesse colonne, piu' flusso_id. Link non risolto: risolto=false e stato_* NULL. La chiave del documento nelle colonne del modello (sorgente_id o sorgente_uid, una sola); il documento si cerca in script.vw_stato_sorgente un ramo per chiave, in una LATERAL, perche' sotto RLS arrivi all'indice di ogni ramo della union. Sede unica della regola per flusso; la legge il backend (percorso della pratica, coda di lavoro). security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_flusso_doc_sorgente
WITH (security_invoker=on) AS
SELECT DISTINCT ON (ps.flusso_id) ps.flusso_id,
    ps.pratica_id,
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
  WHERE (ps.flusso_id IS NOT NULL)
  ORDER BY ps.flusso_id, ((ps.ruolo_link)::text = 'ROOT'::text) DESC, COALESCE(ss.risolto, false) DESC, (NOT COALESCE(ss.terminale, false)) DESC, ps.id DESC;
```

</div>


---
{% include-markdown "signature-core.md" %}
