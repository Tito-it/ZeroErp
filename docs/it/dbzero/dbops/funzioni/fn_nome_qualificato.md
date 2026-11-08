{% include-markdown "it/dbzero/dbops/manual/fn_nome_qualificato.md" %}
# ⚙️ Funzione `fn_nome_qualificato`

```sql
CREATE FUNCTION fn_nome_qualificato(p_relazione regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_nome_qualificato(p_relazione regclass)
 RETURNS text
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT format('%I.%I'::text, n.nspname, c.relname) AS format
    FROM (pg_class c
      JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
   WHERE (c.oid = (fn_nome_qualificato.p_relazione)::oid);
END

COMMENT ON FUNCTION dbops.fn_nome_qualificato(p_relazione regclass)
IS 'Il nome di una tabella (o di un indice, di una vista) con il suo schema, sempre: «schema.nome», con le virgolette dove servono. A differenza di regclass::text non dipende dal search_path di chi chiama, che toglie lo schema quando e'' nel percorso. Serve dove il nome si scrive (una chiave di un riepilogo, un messaggio) o si rimette in un SQL dinamico, che altrimenti si risolverebbe col search_path di chi chiama: una tabella temporanea con lo stesso nome prenderebbe il posto di quella vera. NULL per un oid che non e'' una relazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
