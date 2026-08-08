{% include-markdown "it/dbzero/script/manual/vw_pratica_doc_sorgente.md" %}
# 🔍 View `vw_pratica_doc_sorgente`

> 📝 **Descrizione**
>
> D3b (brief-db-proiezione-stato-dominio roll-out §5b): una riga per pratica col descrittore del documento PIU' VIVO tra i suoi link (ROOT+COLLEGATO). Regola d'ancora NULL-safe: risolto-first, poi vivo(non-terminale)-first, poi ROOT come tiebreak, poi link piu' recente (ps.id). Accende l'ordine COLLEGATO vivo su una pratica preventivo-&gt;ordine SENZA regredire preventivo-&gt;commessa (la commessa non risolta perde per risolto-first). Fallback come il BE odierno: link non risolto -&gt; risolto=false e stato_* NULL (non la sentinella UNKNOWN dello scalare fn_stato_sorgente). Promuove a DB la regola oggi inline in pratiche_repository._doc_sorgente_lateral; sede unica, riusabile da D4 (GUIDA).

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
