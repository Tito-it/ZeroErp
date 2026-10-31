# ⚙️ Funzione `fn_listino_periodicita_articolo`

```sql
CREATE FUNCTION fn_listino_periodicita_articolo(p_listino_versione_id bigint, p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listino_periodicita_articolo(p_listino_versione_id bigint, p_articolo_id uuid)
 RETURNS character varying
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT COALESCE(( SELECT k.periodicita
            FROM vendite.listini_kit k
           WHERE ((k.listino_versione_id = fn_listino_periodicita_articolo.p_listino_versione_id) AND (k.articolo_padre_id = fn_listino_periodicita_articolo.p_articolo_id))), ( SELECT lr.periodicita
            FROM vendite.listini_righe lr
           WHERE ((lr.listino_versione_id = fn_listino_periodicita_articolo.p_listino_versione_id) AND (lr.articolo_id = fn_listino_periodicita_articolo.p_articolo_id) AND (lr.attivo IS TRUE) AND (lr.periodicita IS NOT NULL))
           ORDER BY lr.id
          LIMIT 1)) AS "coalesce";
END

COMMENT ON FUNCTION vendite.fn_listino_periodicita_articolo(p_listino_versione_id bigint, p_articolo_id uuid)
IS 'La periodicita'' con cui un articolo si addebita su una versione di listino: per un kit quella di vendite.listini_kit, per gli altri quella della riga di listino attiva (fra due righe sullo stesso articolo la prima con la periodicita''). NULL = nessuna periodicita'' su quel listino. Sede unica (regola del 2): la leggono il default della riga a canone (script.trgfn_righe_default_periodicita_da_listino), il lister dei canoni (vendite.fn_contratti_addebiti_maturati) e l''anteprima delle righe (vendite.fn_documento_righe_preview). SECURITY INVOKER. Nasce il 2026-10-31 (20261031-32), brief-db-contratto-righe-periodiche-in-commessa §7.7 (L12, D-2-bis).';
```

</div>

---
{% include-markdown "signature-core.md" %}
