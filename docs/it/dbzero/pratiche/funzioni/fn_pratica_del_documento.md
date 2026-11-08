{% include-markdown "it/dbzero/pratiche/manual/fn_pratica_del_documento.md" %}
# ⚙️ Funzione `fn_pratica_del_documento`

```sql
CREATE FUNCTION fn_pratica_del_documento(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_pratica_del_documento(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS TABLE(n_pratiche bigint, pratica_id bigint, pratica_numero text)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT count(DISTINCT ps.pratica_id) AS count,
     min(p.id) AS min,
     (array_agg(p.codice ORDER BY p.id))[1] AS array_agg
    FROM (pratiche.pratiche_sorgenti ps
      JOIN pratiche.pratiche p ON ((p.id = ps.pratica_id)))
   WHERE ((ps.sorgente_tipo_id = fn_pratica_del_documento.p_sorgente_tipo_id) AND ((ps.sorgente_id = fn_pratica_del_documento.p_sorgente_id) OR (ps.sorgente_uid = fn_pratica_del_documento.p_sorgente_uid)));
END

COMMENT ON FUNCTION pratiche.fn_pratica_del_documento(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'La pratica di un documento: quante pratiche distinte lo hanno fra le sorgenti (pratiche.pratiche_sorgenti), la prima per id e il suo codice. Una riga sempre (0 e NULL senza pratiche). Il documento si passa con le colonne del modello (tipo, sorgente_id, sorgente_uid) e si cerca con la regola d''incontro (sorgente_id = p_sorgente_id OR sorgente_uid = p_sorgente_uid): chi ha il documento passa il suo id e il suo uid, chi ha la chiave del modello passa quella e NULL nell''altra. Sede unica: la leggono le viste di lista (colonne pratica_id, pratica_numero, n_pratiche, filtrabili e ordinabili) e vendite.fn_documento_lineage_sintesi. BEGIN ATOMIC, STABLE, INVOKER, incorporabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
