# ⚙️ Funzione `fn_doc_indirizzi_sede`

```sql
CREATE FUNCTION fn_doc_indirizzi_sede(p_documento character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_indirizzi_sede(p_documento character varying)
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
          ('DDT_VENDITA', 'vendite', 'ddt_indirizzi',                 'ddt_id',        'DDT'),
          ('ORDINE_VENDITA', 'vendite', 'ordini_indirizzi',              'ordine_id',     'ORDINI'),
          ('PREVENTIVO', 'vendite', 'preventivi_indirizzi',          'preventivo_id', 'PREVENTIVI'),
          ('OFFERTA_COMMERCIALE', 'vendite', 'offerte_commerciali_indirizzi', 'offerta_id',    'OFFERTE'),
          ('CONTRATTO',  'vendite', 'contratti_indirizzi',           'contratto_id',  'CONTRATTI'),
          ('FATTURA',    'vendite', 'fatture_indirizzi',             'fattura_id',    'FATTURE')
      ) AS v(doc, s, t, fk, amb)
     WHERE v.doc = p_documento;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_indirizzi_sede(p_documento character varying)
IS 'Dove stanno gli indirizzi di un documento: schema e tabella dei suoi *_indirizzi, la colonna verso la testata, l''ambito di config.tipi_indirizzi_allowed. Selettore: DDT, ORDINE, PREVENTIVO, OFFERTA, CONTRATTO (il vocabolario di script.fn_get_stato_testata_documento) e FATTURA. Zero righe = selettore ignoto, decide il chiamante. Schema e nome separati, non regclass: il testo di un regclass dipende dal search_path, e qui finisce in un format(%I). La usano il guard degli indirizzi del cliente, il riempimento dello slot di default e il motivo d''emissione. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§7.2 c). ⭐ rev 2026-10-19 (20261019-43, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato). L''ambito (quinta colonna) resta al plurale fino al 2d (G-6).';
```

---
{% include-markdown "signature-core.md" %}
