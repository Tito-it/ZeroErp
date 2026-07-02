{% include-markdown "it/dbzero/script/manual/vw_pratica_doc_sorgente.md" %}
# 🔍 View `vw_pratica_doc_sorgente`

```sql
CREATE OR REPLACE VIEW script.vw_pratica_doc_sorgente AS
SELECT DISTINCT ON (ps.pratica_id) ps.pratica_id,
    ps.sorgente_tipo_id,
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
     LEFT JOIN script.vw_stato_sorgente ss ON (((ss.sorgente_tipo_id = ps.sorgente_tipo_id) AND (ss.sorgente_uid = ps.sorgente_uid))))
  ORDER BY ps.pratica_id, COALESCE(ss.risolto, false) DESC, (NOT COALESCE(ss.terminale, false)) DESC, ((ps.ruolo_link)::text = 'ROOT'::text) DESC, ps.id DESC;
```


---
{% include-markdown "signature-core.md" %}
