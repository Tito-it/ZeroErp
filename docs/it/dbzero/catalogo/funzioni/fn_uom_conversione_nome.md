{% include-markdown "it/dbzero/catalogo/manual/fn_uom_conversione_nome.md" %}
# ⚙️ Funzione `fn_uom_conversione_nome`

```sql
CREATE FUNCTION fn_uom_conversione_nome(p_articolo_id uuid, p_uom_from_id bigint, p_uom_to_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_uom_conversione_nome(p_articolo_id uuid, p_uom_from_id bigint, p_uom_to_id bigint)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (p_articolo_id IS NOT NULL) THEN ( SELECT format('%s → %s (%s)'::text, u.codice, ub.codice, a.codice) AS format
                FROM ((catalogo.articoli a
                  JOIN catalogo.unita_misura ub ON ((ub.id = a.uom_id)))
                  JOIN catalogo.unita_misura u ON ((u.id = fn_uom_conversione_nome.p_uom_from_id)))
               WHERE (a.id = fn_uom_conversione_nome.p_articolo_id))
             ELSE ( SELECT format('%s → %s'::text, uf.codice, ut.codice) AS format
                FROM (catalogo.unita_misura uf
                  JOIN catalogo.unita_misura ut ON ((ut.id = fn_uom_conversione_nome.p_uom_to_id)))
               WHERE (uf.id = fn_uom_conversione_nome.p_uom_from_id))
         END AS format;
END

COMMENT ON FUNCTION catalogo.fn_uom_conversione_nome(p_articolo_id uuid, p_uom_from_id bigint, p_uom_to_id bigint)
IS 'Il nome di una conversione nei valori dei messaggi, nella forma delle unita'' e non in una lingua: per la mappatura di un articolo (p_articolo_id valorizzato) «unita'' → unita'' base (codice articolo)», con p_uom_from_id l''unita'' della mappatura; per la conversione generale (p_articolo_id NULL) «unita'' → unita''», da p_uom_from_id a p_uom_to_id. NULL se l''articolo o un''unita'' non c''e'' (la riga se ne va con lui). La leggono i guard catalogo.trgfn_uom_guard_storia e catalogo.trgfn_uom_guard_listini_attivi. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
