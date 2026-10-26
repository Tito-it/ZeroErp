{% include-markdown "it/dbzero/script/manual/vw_pratica_doc_sorgente.md" %}
# 🔍 View `vw_pratica_doc_sorgente`

> 📝 **Descrizione**
>
> D3b (brief-db-proiezione-stato-dominio roll-out §5b): una riga per pratica col descrittore del documento PIU' VIVO tra i suoi link (ROOT+COLLEGATO). Regola d'ancora NULL-safe: risolto-first, poi vivo(non-terminale)-first, poi ROOT come tiebreak, poi link piu' recente (ps.id). Accende l'ordine COLLEGATO vivo su una pratica preventivo-&gt;ordine SENZA regredire preventivo-&gt;commessa (la commessa non risolta perde per risolto-first). Fallback come il BE odierno: link non risolto -&gt; risolto=false e stato_* NULL (non la sentinella UNKNOWN dello scalare fn_stato_sorgente). Promuove a DB la regola oggi inline in pratiche_repository._doc_sorgente_lateral; sede unica, riusabile da D4 (GUIDA). ⭐ rev 2026-10-05 (20261005-24): il documento si cerca per CHIAVE NATIVA in una LATERAL (script.fn_sorgente_chiave_uuid / _id su sorgente_chiave_uuid / sorgente_chiave_id di script.vw_stato_sorgente), non piu' con un LEFT JOIN sulla forma testuale. Sotto RLS il confronto sul testo non arriva all'indice (uuid_out, int8out non leakproof) e la union delle sei tabelle-documento si rileggeva per intero per ogni collegamento (dbdev come applicazione, 2026-10-05: vista intera ~0,9 s -&gt; ~0,03 s, una pratica 22 -&gt; 6 ms; righe identiche). La LATERAL e' la forma, non uno stile: dentro la sottoquery la chiave del collegamento e' un parametro esterno e la conversione arriva all'Index Cond; allo stesso livello resterebbe un Join Filter. Stesse colonne, stesse righe, stessa regola d'ancora.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_pratica_doc_sorgente
WITH (security_invoker=on) AS
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
     LEFT JOIN LATERAL ( SELECT v.risolto,
            v.stato_codice_interno,
            v.stato_codice,
            v.stato_descrizione,
            v.fase,
            v.esito,
            v.terminale
           FROM script.vw_stato_sorgente v
          WHERE ((v.sorgente_tipo_id = ps.sorgente_tipo_id) AND (v.sorgente_chiave_uuid = script.fn_sorgente_chiave_uuid(ps.sorgente_uid)))
        UNION ALL
         SELECT v.risolto,
            v.stato_codice_interno,
            v.stato_codice,
            v.stato_descrizione,
            v.fase,
            v.esito,
            v.terminale
           FROM script.vw_stato_sorgente v
          WHERE ((v.sorgente_tipo_id = ps.sorgente_tipo_id) AND (v.sorgente_chiave_id = script.fn_sorgente_chiave_id(ps.sorgente_uid)))) ss ON (true))
  ORDER BY ps.pratica_id, COALESCE(ss.risolto, false) DESC, (NOT COALESCE(ss.terminale, false)) DESC, ((ps.ruolo_link)::text = 'ROOT'::text) DESC, ps.id DESC;
```

</div>


---
{% include-markdown "signature-core.md" %}
