{% include-markdown "it/dbzero/pratiche/manual/fn_pratica_del_documento.md" %}
# ⚙️ Funzione `fn_pratica_del_documento`

```sql
CREATE FUNCTION fn_pratica_del_documento(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_pratica_del_documento(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS TABLE(n_pratiche bigint, pratica_id bigint, pratica_numero text)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT count(DISTINCT ps.pratica_id) AS count,
     min(p.id) AS min,
     (array_agg(p.codice ORDER BY p.id))[1] AS array_agg
    FROM (pratiche.pratiche_sorgenti ps
      JOIN pratiche.pratiche p ON ((p.id = ps.pratica_id)))
   WHERE ((ps.sorgente_tipo_id = fn_pratica_del_documento.p_sorgente_tipo_id) AND (ps.sorgente_uid = fn_pratica_del_documento.p_sorgente_uid));
END

COMMENT ON FUNCTION pratiche.fn_pratica_del_documento(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'La pratica di un documento, per la chiave polimorfa del documento (tipo, uid resa a text secondo key_selector): quante pratiche distinte lo hanno fra le sorgenti, la prima per id e il suo codice. Una riga sempre (0 e NULL senza pratiche). Sede unica: la leggono le viste di lista (colonne pratica_id, pratica_numero, n_pratiche, filtrabili e ordinabili) e vendite.fn_documento_lineage_sintesi. BEGIN ATOMIC, STABLE, INVOKER, incorporabile. Brief: brief-db-lineage-seminata-per-chiave, giro B.';
```

</div>

---
{% include-markdown "signature-core.md" %}
