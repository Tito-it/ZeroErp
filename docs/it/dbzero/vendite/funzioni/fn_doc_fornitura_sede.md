# ⚙️ Funzione `fn_doc_fornitura_sede`

```sql
CREATE FUNCTION fn_doc_fornitura_sede(p_documento text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_doc_fornitura_sede(p_documento text)
 RETURNS TABLE(schema_tabella name, testata name, colonna_etichetta name, tabella name, colonna_fk name, etichetta text)
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore senza colonna
--   di vocabolario (lo stesso di script.fn_get_stato_testata_documento);
--   etichetta e' la parola che l'operatore legge, senza colonna.
--   Schema, tabelle e colonne sono nomi del catalogo: ancorati li'.
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dove stanno la testata e la scheda di fornitura di un
    --   documento. Zero righe = selettore ignoto (o documento
    --   senza scheda di fornitura): decide il chiamante.
    -- ⭐ IMMUTABLE: e' una mappa scritta qui, non legge tabelle.
    -- =========================================================
    RETURN QUERY
    SELECT v.s::name, v.te::name, v.et::name, v.t::name, v.fk::name, v.lbl
      FROM (VALUES
          ('CONTRATTO', 'vendite', 'contratti',           'numero', 'contratti_utilities',           'contratto_id', 'Contratto'),
          ('OFFERTA',   'vendite', 'offerte_commerciali', 'codice', 'offerte_commerciali_utilities', 'offerta_id',   'Offerta')
      ) AS v(doc, s, te, et, t, fk, lbl)
     WHERE v.doc = p_documento;
END;
$function$

COMMENT ON FUNCTION vendite.fn_doc_fornitura_sede(p_documento text)
IS 'Dove sta la scheda di fornitura (1:1) di un documento: lo schema, la testata e la sua colonna leggibile (numero o codice), la tabella della scheda e la sua colonna verso la testata, e la parola che l''operatore legge (Contratto, Offerta). Selettore: CONTRATTO, OFFERTA (il vocabolario di script.fn_get_stato_testata_documento); il preventivo non ha scheda di fornitura. Zero righe = selettore ignoto, decide il chiamante. Schema e nomi separati, non regclass: finiscono in un format(%I), e il testo di un regclass dipende dal search_path. La usano vendite.fn_doc_fornitura_da_anagrafica, il guard vendite.trgfn_doc_fornitura_guard_coppia e il trigger vendite.trgfn_doc_fornitura_segue_cliente. Gemella di script.fn_doc_indirizzi_sede. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§8.4).';
```

---
{% include-markdown "signature-core.md" %}
