{% include-markdown "it/dbzero/catalogo/manual/fn_uom_fonti_conversione.md" %}
# ⚙️ Funzione `fn_uom_fonti_conversione`

```sql
CREATE FUNCTION fn_uom_fonti_conversione(p_articolo_id uuid, p_uom_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_uom_fonti_conversione(p_articolo_id uuid, p_uom_id bigint)
 RETURNS TABLE(priorita integer, fonte_id bigint, fattore numeric, validita daterange)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT 0,
     NULL::bigint AS int8,
     (1)::numeric AS "numeric",
     daterange(NULL::date, NULL::date) AS daterange
    FROM catalogo.articoli a
   WHERE ((a.id = fn_uom_fonti_conversione.p_articolo_id) AND (a.uom_id = fn_uom_fonti_conversione.p_uom_id))
 UNION ALL
  SELECT 1,
     o.id,
     (o.factor_to_base)::numeric AS factor_to_base,
     o.validita
    FROM catalogo.articoli_uom_operativa o
   WHERE ((o.articolo_id = fn_uom_fonti_conversione.p_articolo_id) AND (o.uom_id = fn_uom_fonti_conversione.p_uom_id) AND (o.attivo IS TRUE))
 UNION ALL
  SELECT 2,
     c.id,
         CASE
             WHEN (c.uom_from_id = fn_uom_fonti_conversione.p_uom_id) THEN (c.fattore)::numeric
             ELSE ((1)::numeric / c.fattore)
         END AS "case",
     c.validita
    FROM (catalogo.articoli a
      JOIN catalogo.unita_misura_conversioni c ON ((((c.uom_from_id = fn_uom_fonti_conversione.p_uom_id) AND (c.uom_to_id = a.uom_id)) OR ((c.uom_from_id = a.uom_id) AND (c.uom_to_id = fn_uom_fonti_conversione.p_uom_id)))))
   WHERE ((a.id = fn_uom_fonti_conversione.p_articolo_id) AND (c.attivo IS TRUE));
END

COMMENT ON FUNCTION catalogo.fn_uom_fonti_conversione(p_articolo_id uuid, p_uom_id bigint)
IS 'Le fonti da cui l''unita'' p_uom_id si converte nell''unita'' base dell''articolo p_articolo_id, ciascuna col suo fattore (quante unita'' base vale una unita'' p_uom_id) e il suo periodo: priorita 0, l''unita'' base stessa (fattore 1, sempre); 1, la mappatura dell''articolo (catalogo.articoli_uom_operativa, attiva; fonte_id e'' la riga); 2, la conversione generale fra le due unita'' (catalogo.unita_misura_conversioni, attiva), nel verso in cui e'' scritta o nell''inverso (1/fattore; fonte_id e'' la conversione). Sede unica del predicato «da dove si converte»: la leggono catalogo.fn_get_uom_factor (alla data, la fonte di priorita'' piu'' bassa), catalogo.fn_uom_operativa_alla_data (la mappatura alla data) e catalogo.fn_uom_primo_giorno_non_convertibile (su un periodo). Le mappature di un''unita'' non si sovrappongono (uq_articoli_uom_operativa_no_overlap), ne'' le conversioni di una coppia (ex_unita_misura_conversioni_coppia_no_overlap). fattore e'' numeric senza scala: l''inversa di una conversione non sta in numeric(18,6). SECURITY INVOKER: le tabelle del catalogo non hanno RLS.';
```

</div>

---
{% include-markdown "signature-core.md" %}
