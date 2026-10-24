{% include-markdown "it/dbzero/vendite/manual/fn_contratto_righe_preview.md" %}
# ⚙️ Funzione `fn_contratto_righe_preview`

```sql
CREATE FUNCTION fn_contratto_righe_preview(p_contratto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_righe_preview(p_contratto_id bigint)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, articolo_descrizione character varying, is_composito boolean, uom_id bigint, uom_codice character varying, prezzo_listino numeric, tipo_variazione character varying, valore_variazione numeric, override_riga_id bigint, override_prezzo numeric, tipo_eccezione vendite.tipo_eccezione_contratto, origine character varying, prezzo_finale numeric, componenti jsonb, quantita numeric, qta_operativa numeric, tipo_erogazione character varying, fonte_quantita_attesa character varying, riga_key text, azioni text[], escludi_blocco_codice text, ordine smallint, uom_operativa_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: le righe del drawer ContrattoRigheDrawer e la sorgente della
--   lista vendite.contratto_righe (output invariato).
-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R4): il
--   corpo vive in vendite.fn_documento_righe_preview, comune con
--   l'offerta (regola del 2); qui resta l'ingresso per il contratto.
--   Storia del corpo: 20260516-04 … 20261004-14.
BEGIN
    RETURN QUERY
    SELECT *
      FROM vendite.fn_documento_righe_preview('CONTRATTO', p_contratto_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_contratto_righe_preview(p_contratto_id bigint)
IS 'Le righe OPERATIVE di un contratto (listino + overlay OVERRIDE/ESCLUSIONE + AGGIUNTA standalone e bundle), con riga_key, azioni ed escludi_blocco_codice: SORGENTE della lista configurabile vendite.contratto_righe (D-8.4 del brief liste-righe-documento). 24 colonne. ⭐ Dal 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R4) e'' un involucro di vendite.fn_documento_righe_preview(''CONTRATTO'', id), il corpo comune con l''offerta (regola del 2): la storia delle regole (verbi per origine, UdM della riga, esposizione dei componenti, esclusione senza MODIFICA) e il contratto delle colonne stanno nel COMMENT di quella funzione. Firma e colonne invariate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
