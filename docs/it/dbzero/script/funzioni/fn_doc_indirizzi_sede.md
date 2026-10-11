# ⚙️ Funzione `fn_doc_indirizzi_sede`

```sql
CREATE FUNCTION fn_doc_indirizzi_sede(p_documento text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_indirizzi_sede(p_documento text)
 RETURNS TABLE(schema_tabella name, tabella name, colonna_fk name, ambito text)
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- ⚠️ Tipo nudo DICHIARATO: p_documento e' un selettore senza colonna
--   di vocabolario (lo stesso di script.fn_get_stato_testata_documento).
--   Schema, tabella e colonna sono nomi del catalogo: ancorati li'.
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dove stanno gli indirizzi di un documento. Zero righe =
    --   selettore ignoto: decide il chiamante.
    -- ⭐ IMMUTABLE: e' una mappa scritta qui, non legge tabelle.
    -- =========================================================
    RETURN QUERY
    SELECT v.s::name, v.t::name, v.fk::name, v.amb
      FROM (VALUES
          ('DDT',        'vendite', 'ddt_indirizzi',                 'ddt_id',        'DDT'),
          ('ORDINE',     'vendite', 'ordini_indirizzi',              'ordine_id',     'ORDINI'),
          ('PREVENTIVO', 'vendite', 'preventivi_indirizzi',          'preventivo_id', 'PREVENTIVI'),
          ('OFFERTA',    'vendite', 'offerte_commerciali_indirizzi', 'offerta_id',    'OFFERTE'),
          ('CONTRATTO',  'vendite', 'contratti_indirizzi',           'contratto_id',  'CONTRATTI'),
          ('FATTURA',    'vendite', 'fatture_indirizzi',             'fattura_id',    'FATTURE')
      ) AS v(doc, s, t, fk, amb)
     WHERE v.doc = p_documento;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_indirizzi_sede(p_documento text)
IS 'Dove stanno gli indirizzi di un documento: schema e tabella dei suoi *_indirizzi, la colonna verso la testata, l''ambito di config.tipi_indirizzi_allowed. Selettore: DDT, ORDINE, PREVENTIVO, OFFERTA, CONTRATTO (il vocabolario di script.fn_get_stato_testata_documento) e FATTURA. Zero righe = selettore ignoto, decide il chiamante. Schema e nome separati, non regclass: il testo di un regclass dipende dal search_path, e qui finisce in un format(%I). La usano il guard degli indirizzi del cliente, il riempimento dello slot di default e il motivo d''emissione. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§7.2 c).';
```

---
{% include-markdown "signature-core.md" %}
