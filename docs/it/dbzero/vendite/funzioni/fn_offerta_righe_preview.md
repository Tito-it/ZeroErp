{% include-markdown "it/dbzero/vendite/manual/fn_offerta_righe_preview.md" %}
# ⚙️ Funzione `fn_offerta_righe_preview`

```sql
CREATE FUNCTION fn_offerta_righe_preview(p_offerta_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_righe_preview(p_offerta_id bigint)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, articolo_descrizione character varying, is_composito boolean, uom_id bigint, uom_codice character varying, prezzo_listino numeric, tipo_variazione character varying, valore_variazione numeric, override_riga_id bigint, override_prezzo numeric, tipo_eccezione vendite.tipo_eccezione_contratto, origine character varying, prezzo_finale numeric, componenti jsonb, quantita numeric, qta_operativa numeric, tipo_erogazione character varying, fonte_quantita_attesa character varying, riga_key text, azioni text[], escludi_blocco_codice text, ordine smallint, uom_operativa_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: le righe del drawer dell'offerta, coi verbi che il DB
--   ammette, come quelle del contratto (stesse colonne, stessi verbi).
--   Corpo comune: vendite.fn_documento_righe_preview.
-- Nasce il 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R4).
BEGIN
    RETURN QUERY
    SELECT *
      FROM vendite.fn_documento_righe_preview('OFFERTA_COMMERCIALE', p_offerta_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_righe_preview(p_offerta_id bigint)
IS 'Le righe di un''offerta come le vede il drawer: righe della versione operativa del listino con l''overlay OVERRIDE/ESCLUSIONE, piu'' le AGGIUNTA standalone e bundle; riga_key, azioni (DA_LISTINO -> SOVRASCRIVI_PREZZO, ESCLUDI; OVERRIDE -> MODIFICA, RIPRISTINA_LISTINO; ESCLUSIONE -> RIPRISTINA_ARTICOLO; AGGIUNTA -> MODIFICA, RIMUOVI) ed escludi_blocco_codice. Stesse 24 colonne di vendite.fn_contratto_righe_preview: involucro di vendite.fn_documento_righe_preview(''OFFERTA'', id). Il drawer rende i verbi del DB e non li deduce. Non e'' vendite.fn_offerta_righe_espanse (righe ordine-ready, esclusioni tolte). Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R4). ⭐ rev 2026-10-19 (20261019-26, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE.';
```

---
{% include-markdown "signature-core.md" %}
