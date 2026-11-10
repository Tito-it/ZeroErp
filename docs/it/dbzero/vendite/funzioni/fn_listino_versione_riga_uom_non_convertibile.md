{% include-markdown "it/dbzero/vendite/manual/fn_listino_versione_riga_uom_non_convertibile.md" %}
# ⚙️ Funzione `fn_listino_versione_riga_uom_non_convertibile`

```sql
CREATE FUNCTION fn_listino_versione_riga_uom_non_convertibile(p_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listino_versione_riga_uom_non_convertibile(p_versione_id bigint)
 RETURNS TABLE(riga_id bigint, articolo_id uuid, articolo_codice character varying, uom_codice character varying, primo_giorno date)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT x.id,
     x.articolo_id,
     x.articolo_codice,
     x.uom_codice,
     x.primo
    FROM ( SELECT lr.id,
             lr.articolo_id,
             a.codice AS articolo_codice,
             u.codice AS uom_codice,
             catalogo.fn_uom_primo_giorno_non_convertibile(lr.articolo_id, lr.uom_id, lv.validita) AS primo
            FROM (((vendite.listini_righe lr
              JOIN vendite.listini_versioni lv ON ((lv.id = lr.listino_versione_id)))
              JOIN catalogo.articoli a ON ((a.id = lr.articolo_id)))
              JOIN catalogo.unita_misura u ON ((u.id = lr.uom_id)))
           WHERE ((lr.listino_versione_id = fn_listino_versione_riga_uom_non_convertibile.p_versione_id) AND (lr.attivo IS TRUE))) x
   WHERE (x.primo IS NOT NULL)
   ORDER BY x.primo, x.articolo_codice, x.id
  LIMIT 1;
END

COMMENT ON FUNCTION vendite.fn_listino_versione_riga_uom_non_convertibile(p_versione_id bigint)
IS 'La prima riga attiva della versione di listino p_versione_id con un''unita'' che, in un giorno del periodo della versione (validita), non si converte per l''articolo (catalogo.fn_uom_primo_giorno_non_convertibile): la riga, l''articolo e i codici di articolo e unita'', il primo giorno scoperto. Al piu'' una riga: la prima per giorno, poi per codice articolo. Nessuna se ogni riga si converte per tutto il periodo, o se la versione non c''e'' o e'' fuori perimetro. La leggono il guard del periodo vendite.trgfn_listini_versioni_guard_uom_periodo e l''attivazione script.fn_check_versione_listino_attivabile. SECURITY INVOKER: la versione e le sue righe sono dell''azienda di chi le guarda.';
```

</div>

---
{% include-markdown "signature-core.md" %}
